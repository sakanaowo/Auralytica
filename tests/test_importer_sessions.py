"""Unit tests for Takeout import session management and safe switching."""

import json
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from auralytica import importer, storage
from auralytica.web import create_app

ORIGIN = 'http://127.0.0.1:8765'


def make_event(video='vid11111111', title='Nhạc hay', **fields):
    return dict(
        title=f'Watched {title}',
        titleUrl=f'https://www.youtube.com/watch?v={video}',
        time='2026-09-09T07:00:00+07:00',
        subtitles=[{'name': 'Artist - Topic'}],
        **fields,
    )


class ImporterSessionsTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.db_path = self.root / 'state.sqlite3'
        self.db = storage.open_database(self.db_path)
        self.addCleanup(self.db.close)

        self.folder_1 = self.root / 'Takeout1'
        self.folder_2 = self.root / 'Takeout2'
        self.hist_1 = self.folder_1 / 'history' / 'watch-history.json'
        self.hist_2 = self.folder_2 / 'history' / 'watch-history.json'
        self.hist_1.parent.mkdir(parents=True, exist_ok=True)
        self.hist_2.parent.mkdir(parents=True, exist_ok=True)

    def test_get_import_sessions_empty_and_populated(self):
        # Empty
        res = importer.get_import_sessions(self.db)
        self.assertEqual(res['items'], [])
        self.assertIsNone(res['active_import'])
        self.assertFalse(res['batch_locked'])

        # First import
        self.hist_1.write_text(json.dumps([make_event('vid11111111', 'Song 1')]))
        res_1 = importer.import_folder(self.db, self.folder_1)
        id_1 = res_1['import_id']

        # Second import
        self.hist_2.write_text(json.dumps([make_event('vid22222222', 'Song 2'), make_event('vid33333333', 'Song 3')]))
        res_2 = importer.import_folder(self.db, self.folder_2)
        id_2 = res_2['import_id']

        sessions = importer.get_import_sessions(self.db)
        self.assertEqual(len(sessions['items']), 2)
        self.assertEqual(sessions['active_import'], id_2)

        # Most recent session first
        item_0 = sessions['items'][0]
        self.assertEqual(item_0['id'], id_2)
        self.assertTrue(item_0['is_active'])
        self.assertEqual(item_0['statistics']['unique_videos'], 2)

        item_1 = sessions['items'][1]
        self.assertEqual(item_1['id'], id_1)
        self.assertFalse(item_1['is_active'])
        self.assertEqual(item_1['statistics']['unique_videos'], 1)

    def test_activate_session_and_preserve_state(self):
        # Import Session 1
        self.hist_1.write_text(json.dumps([make_event('vid11111111', 'Song 1')]))
        id_1 = importer.import_folder(self.db, self.folder_1)['import_id']

        # Classify vid11111111 as music
        storage.set_video_group(self.db, 'vid11111111', 'music')

        # Import Session 2
        self.hist_2.write_text(json.dumps([make_event('vid22222222', 'Song 2')]))
        id_2 = importer.import_folder(self.db, self.folder_2)['import_id']
        self.assertEqual(storage.get_setting(self.db, 'active_import'), str(id_2))

        # Switch back to Session 1
        act_res = importer.activate_import_session(self.db, id_1)
        self.assertEqual(act_res['status'], 'activated')
        self.assertEqual(act_res['active_import'], id_1)
        self.assertEqual(storage.get_setting(self.db, 'active_import'), str(id_1))

        # Verify Session 1 user classification was preserved
        v1 = storage.get_video(self.db, 'vid11111111')
        self.assertEqual(v1['user_group'], 'music')

    def test_activate_blocked_when_download_batch_busy(self):
        self.hist_1.write_text(json.dumps([make_event('vid11111111', 'Song 1')]))
        id_1 = importer.import_folder(self.db, self.folder_1)['import_id']
        self.hist_2.write_text(json.dumps([make_event('vid22222222', 'Song 2')]))
        id_2 = importer.import_folder(self.db, self.folder_2)['import_id']

        # Insert a running download batch
        self.db.execute("INSERT INTO download_batches (id, output_dir, status) VALUES (1, '/tmp', 'running')")
        self.db.commit()

        # Activating should raise BatchBusyError
        with self.assertRaises(storage.BatchBusyError):
            importer.activate_import_session(self.db, id_1)

    def test_cannot_delete_active_session(self):
        self.hist_1.write_text(json.dumps([make_event('vid11111111', 'Song 1')]))
        id_1 = importer.import_folder(self.db, self.folder_1)['import_id']

        with self.assertRaises(ValueError) as ctx:
            importer.delete_import_session(self.db, id_1)
        self.assertIn("Không thể xóa phiên đang hoạt động", str(ctx.exception))

    def test_delete_inactive_session(self):
        self.hist_1.write_text(json.dumps([make_event('vid11111111', 'Song 1')]))
        id_1 = importer.import_folder(self.db, self.folder_1)['import_id']

        self.hist_2.write_text(json.dumps([make_event('vid22222222', 'Song 2')]))
        id_2 = importer.import_folder(self.db, self.folder_2)['import_id']

        # Delete inactive Session 1
        res = importer.delete_import_session(self.db, id_1)
        self.assertEqual(res['status'], 'deleted')
        self.assertEqual(res['deleted_id'], id_1)

        # Check DB
        self.assertIsNone(self.db.execute("SELECT id FROM imports WHERE id = ?", (id_1,)).fetchone())
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM watch_events WHERE import_id = ?", (id_1,)).fetchone()[0], 0)
        # Session 2 still exists
        self.assertIsNotNone(self.db.execute("SELECT id FROM imports WHERE id = ?", (id_2,)).fetchone())
        # vid11111111 metadata still exists in videos table
        self.assertIsNotNone(storage.get_video(self.db, 'vid11111111'))

    def test_http_api_endpoints(self):
        self.hist_1.write_text(json.dumps([make_event('vid11111111', 'Song 1')]))
        id_1 = importer.import_folder(self.db, self.folder_1)['import_id']
        self.hist_2.write_text(json.dumps([make_event('vid22222222', 'Song 2')]))
        id_2 = importer.import_folder(self.db, self.folder_2)['import_id']

        app = create_app(self.db_path)
        client = TestClient(app, base_url=ORIGIN)

        # 1. GET /api/imports
        res = client.get('/api/imports', headers={'Origin': ORIGIN})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data['items']), 2)
        self.assertEqual(data['active_import'], id_2)

        # 2. POST /api/imports/{id}/activate
        res = client.post(f'/api/imports/{id_1}/activate', headers={'Origin': ORIGIN})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['active_import'], id_1)

        # Verify workflow is now pointing to id_1
        wf = client.get('/api/workflow', headers={'Origin': ORIGIN}).json()
        self.assertEqual(wf['active_import'], id_1)

        # 3. DELETE /api/imports/{id_1} should fail (it is now active)
        del_fail = client.delete(f'/api/imports/{id_1}', headers={'Origin': ORIGIN})
        self.assertEqual(del_fail.status_code, 400)

        # 4. DELETE /api/imports/{id_2} succeeds (it is inactive)
        del_ok = client.delete(f'/api/imports/{id_2}', headers={'Origin': ORIGIN})
        self.assertEqual(del_ok.status_code, 200)
        self.assertEqual(del_ok.json()['status'], 'deleted')
