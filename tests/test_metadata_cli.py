import json
from pathlib import Path
import tempfile
import unittest

from auralytica import importer, storage
from auralytica import metadata, audit


class MetadataServiceTests(unittest.TestCase):
    def test_collect_status_and_export_cache_dependencies(self):
        class Fake:
            key = 'cli-fixture-v1'
            last_http_status = 200
            calls = []
            def fetch(self, vid):
                self.calls.append(vid)
                return {'videoDetails':{'videoId':vid,'musicVideoType':'MUSIC_VIDEO_TYPE_ATV'}}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root/'db.sqlite3'
            (root/'watch-history.json').write_text(json.dumps([{'titleUrl':'https://youtu.be/aaaaaaaaaaa'}]))
            db = storage.open_database(path)
            self.addCleanup(db.close)
            importer.import_folder(db, root)
            provider = Fake()
            first_id = metadata.create_run(db, provider_key=provider.key, video_ids=['aaaaaaaaaaa'])
            first = metadata.collect_run(db, first_id, provider, sleep=lambda _: None)
            second_id = metadata.create_run(db, provider_key=provider.key, video_ids=['aaaaaaaaaaa'])
            second = metadata.collect_run(db, second_id, provider, sleep=lambda _: None)
            self.assertEqual(metadata.get_run(db, second_id)['status'], 'completed')
            self.assertEqual(Fake.calls, ['aaaaaaaaaaa'])
            output = root/'audit.jsonl'
            exported = audit.export_events(db, output, run_id=second['run_id'])
            records = [json.loads(s) for s in output.read_text().splitlines()]
            self.assertGreater(exported['records'], 0)
            self.assertTrue(any(r.get('kind')=='metadata_observed' and r.get('dependency') for r in records))
            self.assertTrue(any(r.get('kind')=='metadata_cache_hit' for r in records))
            with self.assertRaises(FileExistsError):
                audit.export_events(db, output, run_id=first['run_id'])

    def test_ytmusic_adapter_retries_only_transient_errors_and_retains_status(self):
        import requests
        from types import SimpleNamespace
        self.assertTrue(hasattr(metadata, 'YTMusicProvider'), 'YouTube Music adapter is missing')
        response = requests.Response()
        response.status_code = 429
        error = requests.HTTPError('SECRET signed URL', response=response)
        def get_song(vid):
            raise error
        provider = metadata.YTMusicProvider(client=SimpleNamespace(get_song=get_song))
        with self.assertRaises(Exception) as caught:
            provider.fetch('aaaaaaaaaaa')
        self.assertTrue(caught.exception.retryable)
        self.assertEqual(provider.last_http_status, 429)
        self.assertNotIn('SECRET', str(caught.exception))
        response.status_code = 403
        with self.assertRaises(Exception) as caught:
            provider.fetch('aaaaaaaaaaa')
        self.assertFalse(caught.exception.retryable)
