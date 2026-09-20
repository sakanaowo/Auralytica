from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from auralytica import main, importer, storage
from auralytica import metadata, audit


class MetadataCliTests(unittest.TestCase):
    def test_cli_collect_status_and_export_cache_dependencies(self):
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
            def invoke(*args):
                output = io.StringIO()
                with patch.object(sys, 'argv', ['auralytica',*args,'--database',str(path)]), redirect_stdout(output), redirect_stderr(io.StringIO()):
                    main()
                return json.loads(output.getvalue())
            # The missing CLI must fail at parsing, before any network adapter is constructed.
            with patch.object(metadata, 'YTMusicProvider', return_value=Fake(), create=True):
                first = invoke('metadata','collect','--video-id','aaaaaaaaaaa')
                second = invoke('metadata','collect','--video-id','aaaaaaaaaaa')
                status = invoke('metadata','status',second['run_id'])
                self.assertEqual(status['status'], 'completed')
                self.assertEqual(Fake.calls, ['aaaaaaaaaaa'])
            output = root/'audit.jsonl'
            exported = invoke('audit','--run-id',second['run_id'],'--output',str(output))
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

