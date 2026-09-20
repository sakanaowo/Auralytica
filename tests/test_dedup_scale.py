import json
from pathlib import Path
import tempfile
import time
import unittest

from auralytica import dedup, storage
from auralytica.importer import import_folder


class DedupScaleTests(unittest.TestCase):
    def test_groups_7500_music_videos_without_pairwise_comparison(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            history = root / 'Takeout' / 'history'
            history.mkdir(parents=True)
            rows = [{'titleUrl': f'https://youtu.be/{index:011d}',
                     'title': f'Watched Song {index // 2:04d}',
                     'subtitles': [{'name': 'Artist - Topic'}]} for index in range(7500)]
            (history / 'watch-history.json').write_text(json.dumps(rows))
            with storage.open_database(root / 'state.sqlite3') as db:
                import_folder(db, history.parent)
                started = time.perf_counter()
                run = dedup.create_run(db)
                elapsed = time.perf_counter() - started
                self.assertEqual(run['groups'], 3750)
                self.assertFalse(run['stale'])
                page = dedup.list_groups(db, run['run_id'])
                self.assertEqual(page['total'], 3750)
                self.assertEqual(len(page['items']), 20)
                print(json.dumps({'dedup_videos': 7500, 'groups': 3750,
                                  'elapsed_seconds': round(elapsed, 3),
                                  'fixture': 'synthetic exact-title pairs'}))


if __name__ == '__main__':
    unittest.main()
