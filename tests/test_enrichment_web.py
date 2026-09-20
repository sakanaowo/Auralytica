import json
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from auralytica import storage, web


ORIGIN = 'http://127.0.0.1:8765'


class Provider:
    key = 'fixture:player-v1:en:VN'
    last_http_status = 200

    def fetch(self, video_id):
        return {
            'videoDetails': {
                'videoId': video_id,
                'musicVideoType': 'MUSIC_VIDEO_TYPE_OMV',
                'title': 'Fixture song',
                'author': 'Fixture artist',
            },
            'playabilityStatus': {'status': 'OK'},
        }


class EnrichmentWebTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name) / 'state.sqlite3'
        self.app = web.create_app(self.database)
        self.app.state.metadata_provider_factory = Provider
        self.app.state.launch_metadata = self.app.state.run_metadata_inline
        self.client = TestClient(self.app, base_url=ORIGIN)
        self.addCleanup(self.client.close)
        self.history = [
            {'titleUrl': 'https://youtu.be/aaaaaaaaaaa', 'title': 'Watched Song A',
             'subtitles': [{'name': 'Channel A'}], 'time': '2026-09-01T00:00:00Z'},
            {'titleUrl': 'https://youtu.be/bbbbbbbbbbb', 'title': 'Watched Song B',
             'subtitles': [{'name': 'Channel B'}], 'time': '2026-09-02T00:00:00Z'},
        ]
        self.upload(self.history)

    def upload(self, rows):
        response = self.client.post('/api/imports', headers={'Origin': ORIGIN}, files=[
            ('files', ('Takeout/history/watch-history.json', json.dumps(rows).encode(), 'application/json'))])
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def post(self, path, payload=None):
        return self.client.post(path, headers={'Origin': ORIGIN}, json=payload or {})

    def test_metadata_scope_run_log_preview_apply_and_reimport(self):
        scope = self.client.get('/api/metadata/scope', params={'group': 'rest', 'limit': 1})
        self.assertEqual(scope.status_code, 200, scope.text)
        self.assertEqual(scope.json()['selected'], 1)
        started = self.post('/api/metadata/runs', {'group': 'rest', 'limit': 1})
        self.assertEqual(started.status_code, 200, started.text)
        run_id = started.json()['run_id']
        status = self.client.get(f'/api/metadata/runs/{run_id}').json()
        self.assertEqual(status['status'], 'completed')
        self.assertEqual(status['counts'], {'done': 1})
        events = self.client.get(f'/api/metadata/runs/{run_id}/events').json()
        self.assertTrue(any(row['kind'] == 'metadata_observed' for row in events['items']))

        preview = self.post('/api/classification/previews').json()
        self.assertEqual(preview['changed'], 1)
        self.assertEqual(preview['items'][0]['reason'], 'ytmusic_strong')
        applied = self.post(f"/api/classification/previews/{preview['preview_id']}/apply")
        self.assertEqual(applied.status_code, 200, applied.text)
        self.assertEqual(applied.json()['changed'], 1)
        self.assertEqual(self.client.get('/api/videos?group=music').json()['filtered_count'], 1)

        # Video metadata remains valid; recurrence and membership come from the new import.
        self.upload([self.history[0]])
        item = self.client.get('/api/videos?group=music').json()['items'][0]
        self.assertEqual(item['id'], 'aaaaaaaaaaa')
        self.assertEqual(item['reason'], 'ytmusic_strong')

    def test_stale_preview_and_batch_lock_do_not_mutate_library(self):
        started = self.post('/api/metadata/runs', {'group': 'rest', 'limit': 1}).json()
        self.assertEqual(started['status'], 'completed')
        preview = self.post('/api/classification/previews').json()
        self.post('/api/videos/move', {'video_ids': ['aaaaaaaaaaa'], 'to_group': 'music'})
        stale = self.post(f"/api/classification/previews/{preview['preview_id']}/apply")
        self.assertEqual(stale.status_code, 409, stale.text)
        self.assertEqual(self.client.get(
            f"/api/classification/previews/{preview['preview_id']}").json()['status'], 'stale')
        self.assertEqual(self.client.get('/api/videos?group=music').json()['filtered_count'], 1)

        fresh = self.post('/api/classification/previews').json()

        with storage.open_database(self.database) as db:
            from auralytica.batches import create_batch
            create_batch(db, Path(self.temp.name) / 'audio')
        blocked = self.post('/api/metadata/runs', {'group': 'rest', 'limit': 1})
        self.assertEqual(blocked.status_code, 409, blocked.text)
        apply_blocked = self.post(f"/api/classification/previews/{fresh['preview_id']}/apply")
        self.assertEqual(apply_blocked.status_code, 409, apply_blocked.text)

    def test_stop_then_resume_uses_the_frozen_selection(self):
        with storage.open_database(self.database) as db:
            from auralytica import metadata
            run_id = metadata.create_run(db, provider_key=Provider.key,
                                         video_ids=['aaaaaaaaaaa', 'bbbbbbbbbbb'])
            metadata.request_stop(db, run_id)
            paused = metadata.collect_run(db, run_id, Provider(), sleep=lambda _: None)
            self.assertEqual(paused['status'], 'paused')
            self.assertEqual(paused['counts'], {'pending': 2})
            completed = metadata.collect_run(db, run_id, Provider(), sleep=lambda _: None)
            self.assertEqual(completed['status'], 'completed')
            self.assertEqual(completed['counts'], {'done': 2})

    def test_stale_metadata_is_visible_but_not_new_classification_evidence(self):
        self.post('/api/metadata/runs', {'group': 'rest', 'limit': 1})
        with storage.open_database(self.database) as db:
            db.execute('UPDATE metadata_cache SET fetched_at=0')
        scope = self.client.get('/api/metadata/scope', params={'group': 'rest', 'limit': 1}).json()
        self.assertEqual((scope['cached'], scope['stale']), (0, 1))
        preview = self.post('/api/classification/previews').json()
        self.assertEqual(preview['changed'], 0)
        self.assertEqual(preview['items'][0]['reason'], 'metadata_stale')

    def test_apply_audit_failure_rolls_back_metadata_and_groups(self):
        self.post('/api/metadata/runs', {'group': 'rest', 'limit': 1})
        preview = self.post('/api/classification/previews').json()
        with storage.open_database(self.database) as db:
            db.execute("CREATE TRIGGER fail_preview_audit BEFORE INSERT ON audit_events "
                       "WHEN NEW.kind='preview_applied' BEGIN SELECT RAISE(ABORT,'fixture'); END")
        response = self.post(f"/api/classification/previews/{preview['preview_id']}/apply")
        self.assertEqual(response.status_code, 503, response.text)
        self.assertEqual(self.client.get('/api/videos?group=music').json()['filtered_count'], 0)
        self.assertEqual(self.client.get(
            f"/api/classification/previews/{preview['preview_id']}").json()['status'], 'ready')

    def test_new_app_marks_interrupted_metadata_run_resumable(self):
        with storage.open_database(self.database) as db:
            from auralytica import metadata
            run_id = metadata.create_run(db, provider_key=Provider.key,
                                         video_ids=['aaaaaaaaaaa'])
            db.execute("UPDATE audit_runs SET status='running' WHERE id=?", (run_id,))
        recovered = web.create_app(self.database)
        recovered.state.metadata_provider_factory = Provider
        recovered.state.launch_metadata = recovered.state.run_metadata_inline
        with TestClient(recovered, base_url=ORIGIN) as client:
            status = client.get(f'/api/metadata/runs/{run_id}').json()
            self.assertEqual(status['status'], 'paused')
            resumed = client.post(f'/api/metadata/runs/{run_id}/resume', headers={'Origin': ORIGIN})
            self.assertEqual(resumed.status_code, 200, resumed.text)
            self.assertEqual(client.get(f'/api/metadata/runs/{run_id}').json()['status'], 'completed')


if __name__ == '__main__':
    unittest.main()
