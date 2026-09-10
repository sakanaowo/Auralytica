import json
from pathlib import Path
import subprocess
import sys
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

    def test_preview_snapshot_stop_edit_resume_and_paginated_status(self):
        preview = self.client.get('/api/downloads/preview', params={'output_dir': str(self.output)})
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.json()['needed'], 2)
        self.assertFalse(self.output.exists())
        response = self.post('/api/downloads', {'output_dir': str(self.output)})
        self.assertEqual(response.status_code, 200, response.text)
        batch = response.json()['batch_id']
        self.assertEqual(response.json()['total'], 2)
        self.assertEqual(self.post('/api/downloads', {'output_dir': str(self.output)}).json()['batch_id'], batch)
        status = self.client.get(f'/api/downloads/{batch}?page_size=1').json()
        self.assertEqual(len(status['items']), 1)
        self.assertEqual(status['total'], 2)
        self.assertEqual(self.post(f'/api/downloads/{batch}/stop').json()['status'], 'paused')
        self.assertEqual(self.post('/api/videos/move', {'video_ids': ['00000000000'], 'to_group': 'rest'}).status_code, 200)
        self.assertEqual(self.post(f'/api/downloads/{batch}/resume').json()['total'], 2)
        self.assertEqual(self.client.get('/api/downloads').json()['batches'][0]['batch_id'], batch)

    def test_finished_files_disable_preview_and_cli_status_stop_resume_share_database(self):
        response = self.post('/api/downloads', {'output_dir': str(self.output)})
        self.assertEqual(response.status_code, 200, response.text)
        batch = response.json()['batch_id']
        def adapter(video_id, directory, progress, stopped, lock_fd):
            path = directory/'audio.webm'; path.write_bytes(b'audio fixture')
            return {'id': video_id, 'path': str(path), 'vcodec': 'none', 'acodec': 'opus'}
        with open_database(self.database) as db:
            run_batch(db, batch, adapter=adapter)
        self.assertEqual(self.client.get('/api/downloads/preview', params={'output_dir': str(self.output)}).json()['needed'], 0)
        cli = str(Path(sys.executable).parent/'auralytica')
        result = subprocess.run([cli, 'status', '--database', str(self.database)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'completed')
        result = subprocess.run([cli, 'download', '--output', str(self.output), '--database', str(self.database)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['skipped'], 2)

    def test_launch_failure_pauses_and_is_visible_and_inputs_are_guarded(self):
        self.app.state.launch_worker.side_effect = OSError('cannot start process')
        response = self.post('/api/downloads', {'output_dir': str(self.output)})
        self.assertEqual(response.status_code, 200, response.text)
        status = self.client.get(f"/api/downloads/{response.json()['batch_id']}").json()
        self.assertEqual(status['status'], 'paused')
        self.assertIn('cannot start', status['error'])
        self.assertEqual(self.client.post('/api/downloads', json={'output_dir': str(self.output)}).status_code, 403)
        self.assertEqual(self.post('/api/downloads', {'output_dir': '', 'video_ids': []}).status_code, 422)
        self.assertEqual(self.client.get('/api/downloads/999').status_code, 400)
        self.assertEqual(self.client.get('/api/downloads/1?page=0').status_code, 422)

    def test_cli_stop_and_resume_completed_snapshot_without_network(self):
        response = self.post('/api/downloads', {'output_dir': str(self.output)})
        batch = response.json()['batch_id']
        cli = str(Path(sys.executable).parent/'auralytica')
        def call(*args):
            return subprocess.run([cli, *args, '--database', str(self.database)], capture_output=True, text=True, timeout=10)
        stopped = call('stop', str(batch))
        self.assertEqual(stopped.returncode, 0, stopped.stderr)
        self.assertEqual(json.loads(stopped.stdout)['status'], 'paused')
        with open_database(self.database) as db:
            for i in range(2):
                path = self.output/f'{i}.webm'; path.write_bytes(b'fixture')
                db.execute("UPDATE download_items SET status='completed',file_path=?,file_size=7 WHERE batch_id=? AND video_id=?", (str(path), batch, f'{i:011d}'))
        resumed = call('resume', str(batch))
        self.assertEqual(resumed.returncode, 0, resumed.stderr)
        self.assertEqual(json.loads(resumed.stdout)['status'], 'completed')

    def test_detached_worker_reports_preflight_error_and_recovers_orphan(self):
        response = self.post('/api/downloads', {'output_dir': str(self.output)})
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
