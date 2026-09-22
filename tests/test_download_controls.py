import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock

from fastapi.testclient import TestClient
from auralytica.web import create_app
from auralytica.storage import open_database
from auralytica.downloader import run_batch

ORIGIN = 'http://127.0.0.1:8765'

class DownloadControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.database = self.root/'state.sqlite3'
        self.output = self.root/'audio'
        self.app = create_app(self.database)
        self.app.state.launch_worker = Mock()
        self.client = TestClient(self.app, base_url=ORIGIN)
        self.addCleanup(self.client.close)
        rows = [{'titleUrl': f'https://youtu.be/{i:011d}', 'title': f'Watched Song {i}',
                 'subtitles': [{'name': 'Artist - Topic' if i < 2 else 'Podcast'}]} for i in range(3)]
        self.client.post('/api/imports', headers={'Origin': ORIGIN},
                         files={'files': ('watch-history.json', json.dumps(rows))})

    def post(self, path, data=None):
        return self.client.post(path, headers={'Origin': ORIGIN}, json=data)

    def start(self, output=None):
        output = output or self.output
        preview = self.client.get('/api/downloads/preview', params={'output_dir': str(output)}).json()
        return self.post('/api/downloads', {'output_dir': str(output), 'preview_token': preview['token']})

    def test_preview_snapshot_stop_edit_resume_and_paginated_status(self):
        preview = self.client.get('/api/downloads/preview', params={'output_dir': str(self.output)})
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.json()['needed'], 2)
        self.assertFalse(self.output.exists())
        response = self.start()
        self.assertEqual(response.status_code, 200, response.text)
        batch = response.json()['batch_id']
        self.assertEqual(response.json()['total'], 2)
        self.assertEqual(self.start().json()['batch_id'], batch)
        status = self.client.get(f'/api/downloads/{batch}?page_size=1').json()
        self.assertEqual(len(status['items']), 1)
        self.assertEqual(status['total'], 2)
        self.assertEqual(self.post(f'/api/downloads/{batch}/stop').json()['status'], 'paused')
        self.assertEqual(self.post('/api/videos/move', {'video_ids': ['00000000000'], 'to_group': 'rest'}).status_code, 200)
        self.assertEqual(self.post(f'/api/downloads/{batch}/resume').json()['total'], 2)
        self.assertEqual(self.client.get('/api/downloads').json()['batches'][0]['batch_id'], batch)

    def test_preview_token_applies_dedup_selection_to_new_batch(self):
        selection = self.post('/api/dedup/selections', {
            'video_ids': ['00000000001'], 'keep': False, 'expected_revision': 0,
        })
        self.assertEqual(selection.status_code, 200, selection.text)
        preview = self.client.get('/api/downloads/preview', params={'output_dir': str(self.output)})
        self.assertEqual(preview.status_code, 200, preview.text)
        data = preview.json()
        self.assertEqual(
            {key: data[key] for key in ('music', 'excluded', 'kept', 'skipped', 'queued', 'needed')},
            {'music': 2, 'excluded': 1, 'kept': 1, 'skipped': 0, 'queued': 1, 'needed': 1},
        )
        response = self.post('/api/downloads', {'output_dir': str(self.output), 'preview_token': data['token']})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual((response.json()['total'], response.json()['excluded']), (1, 1))
        with open_database(self.database) as db:
            self.assertEqual(
                [row[0] for row in db.execute('SELECT video_id FROM download_items WHERE batch_id=?',
                                               (response.json()['batch_id'],))],
                ['00000000000'],
            )

    def test_stale_preview_token_returns_conflict_without_creating_batch(self):
        preview = self.client.get('/api/downloads/preview', params={'output_dir': str(self.output)}).json()
        self.assertEqual(self.post('/api/dedup/selections', {
            'video_ids': ['00000000001'], 'keep': False, 'expected_revision': 0,
        }).status_code, 200)
        response = self.post('/api/downloads', {
            'output_dir': str(self.output), 'preview_token': preview['token'],
        })
        self.assertEqual(response.status_code, 409, response.text)
        self.assertIn('preview', response.json()['detail'])
        with open_database(self.database) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM download_batches').fetchone()[0], 0)

    def test_finished_files_disable_preview_and_new_batch_skips_all(self):
        response = self.start()
        self.assertEqual(response.status_code, 200, response.text)
        batch = response.json()['batch_id']
        def adapter(video_id, directory, progress, stopped, lock_fd):
            path = directory/'audio.webm'; path.write_bytes(b'audio fixture')
            return {'id': video_id, 'path': str(path), 'vcodec': 'none', 'acodec': 'opus'}
        with open_database(self.database) as db:
            run_batch(db, batch, adapter=adapter)
        self.assertEqual(self.client.get('/api/downloads/preview', params={'output_dir': str(self.output)}).json()['needed'], 0)
        result = self.start()
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual((result.json()['status'], result.json()['skipped']), ('completed', 2))

    def test_launch_failure_pauses_and_is_visible_and_inputs_are_guarded(self):
        self.app.state.launch_worker.side_effect = OSError('cannot start process')
        response = self.start()
        self.assertEqual(response.status_code, 200, response.text)
        status = self.client.get(f"/api/downloads/{response.json()['batch_id']}").json()
        self.assertEqual(status['status'], 'paused')
        self.assertIn('cannot start', status['error'])
        self.assertEqual(self.client.post('/api/downloads', json={'output_dir': str(self.output)}).status_code, 403)
        self.assertEqual(self.post('/api/downloads', {'output_dir': '', 'video_ids': []}).status_code, 422)
        self.assertEqual(self.client.get('/api/downloads/999').status_code, 400)
        self.assertEqual(self.client.get('/api/downloads/1?page=0').status_code, 422)

    def test_web_stop_and_resume_completed_snapshot_without_network(self):
        response = self.start()
        batch = response.json()['batch_id']
        stopped = self.post(f'/api/downloads/{batch}/stop')
        self.assertEqual(stopped.status_code, 200, stopped.text)
        self.assertEqual(stopped.json()['status'], 'paused')
        with open_database(self.database) as db:
            for i in range(2):
                path = self.output/f'{i}.webm'; path.write_bytes(b'fixture')
                db.execute("UPDATE download_items SET status='completed',file_path=?,file_size=7 WHERE batch_id=? AND video_id=?", (str(path), batch, f'{i:011d}'))
        resumed = self.post(f'/api/downloads/{batch}/resume')
        self.assertEqual(resumed.status_code, 200, resumed.text)
        self.assertEqual(resumed.json()['status'], 'completed')

    def test_detached_worker_reports_preflight_error_and_recovers_orphan(self):
        response = self.start()
        batch = response.json()['batch_id']
        self.output.rmdir(); self.output.write_text('not a directory')
        from auralytica.download_controls import launch_worker
        launch_worker(self.database, batch)
        for _ in range(100):
            status = self.client.get(f'/api/downloads/{batch}').json()
            if status['status'] == 'paused' and status['error']: break
            time.sleep(.02)
        self.assertEqual(status['status'], 'paused')
        self.assertTrue(status['error'])
        with open_database(self.database) as db:
            db.execute("UPDATE download_batches SET status='running' WHERE id=?", (batch,))
        self.assertEqual(self.post(f'/api/downloads/{batch}/stop').json()['status'], 'paused')

    def test_retry_failed_and_retry_single_item_and_status_filter(self):
        response = self.start()
        self.assertEqual(response.status_code, 200, response.text)
        batch = response.json()['batch_id']
        with open_database(self.database) as db:
            db.execute("UPDATE download_items SET status='failed',error_code='unavailable',error_message='Video không khả dụng' WHERE batch_id=? AND video_id='00000000000'", (batch,))
            db.execute("UPDATE download_items SET status='completed',file_path='/tmp/0.webm',file_size=10 WHERE batch_id=? AND video_id='00000000001'", (batch,))
            db.execute("UPDATE download_batches SET status='partial' WHERE id=?", (batch,))

        # Filter by failed status
        failed_res = self.client.get(f'/api/downloads/{batch}?status=failed')
        self.assertEqual(failed_res.status_code, 200)
        failed_data = failed_res.json()
        self.assertEqual(len(failed_data['items']), 1)
        self.assertEqual(failed_data['filtered_total'], 1)
        self.assertEqual(failed_data['items'][0]['video_id'], '00000000000')
        self.assertEqual(failed_data['items'][0]['error_code'], 'unavailable')

        # Filter by completed status
        completed_res = self.client.get(f'/api/downloads/{batch}?status=completed')
        self.assertEqual(completed_res.status_code, 200)
        self.assertEqual(completed_res.json()['filtered_total'], 1)

        # Retry single item
        self.app.state.launch_worker.reset_mock()
        retry_item_res = self.post(f'/api/downloads/{batch}/items/00000000000/retry')
        self.assertEqual(retry_item_res.status_code, 200)
        self.assertEqual(retry_item_res.json()['status'], 'queued')
        self.app.state.launch_worker.assert_called_once()
        with open_database(self.database) as db:
            item = db.execute("SELECT status,error_code FROM download_items WHERE batch_id=? AND video_id='00000000000'", (batch,)).fetchone()
            self.assertEqual(item['status'], 'queued')
            self.assertIsNone(item['error_code'])

        # Set back to failed and test retry-failed
        with open_database(self.database) as db:
            db.execute("UPDATE download_items SET status='failed',error_code='bot_blocked',error_message='Bot blocked' WHERE batch_id=? AND video_id='00000000000'", (batch,))
            db.execute("UPDATE download_batches SET status='partial' WHERE id=?", (batch,))

        self.app.state.launch_worker.reset_mock()
        retry_all_res = self.post(f'/api/downloads/{batch}/retry-failed')
        self.assertEqual(retry_all_res.status_code, 200)
        self.assertEqual(retry_all_res.json()['status'], 'queued')
        self.app.state.launch_worker.assert_called_once()
        with open_database(self.database) as db:
            item = db.execute("SELECT status,error_code FROM download_items WHERE batch_id=? AND video_id='00000000000'", (batch,)).fetchone()
            self.assertEqual(item['status'], 'queued')
            self.assertIsNone(item['error_code'])

    def test_start_download_with_format_and_clean_names_payload(self):
        token = self.client.get('/api/downloads/preview', params={'output_dir': str(self.output)}).json()['token']
        res = self.post('/api/downloads', {
            'output_dir': str(self.output),
            'preview_token': token,
            'format': 'm4a_alac',
            'clean_names': True,
            'embed_metadata': True,
        })
        self.assertEqual(res.status_code, 200, res.text)
        batch = res.json()
        self.assertEqual(batch['format'], 'm4a_alac')
        self.assertTrue(batch['clean_names'])
        self.assertTrue(batch['embed_metadata'])
        status = self.client.get(f"/api/downloads/{batch['batch_id']}").json()
        self.assertEqual(status['format'], 'm4a_alac')
        self.assertTrue(status['clean_names'])
        self.assertTrue(status['embed_metadata'])

