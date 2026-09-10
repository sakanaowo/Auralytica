import json
from pathlib import Path
import tempfile
import unittest

from auralytica import importer, storage


def event(video='abcdefghijk', **fields):
    return dict(title='Watched Nhạc 音楽', titleUrl=f'https://www.youtube.com/watch?v={video}',
                time='2026-09-09T07:00:00+07:00', **fields)


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = self.root / 'Takeout'
        self.history = self.folder / 'history' / 'watch-history.json'
        self.history.parent.mkdir(parents=True)
        self.db = storage.open_database(self.root / 'state.sqlite3')
        self.addCleanup(self.db.close)

    def write(self, rows):
        self.history.write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')

    def test_counts_repeats_ads_invalid_rows_and_utc(self):
        self.write([event(), event(), event('lmnopqrstuv'),
                    event(details=[{'name':'From Google Ads'}]), {}, 12,
                    {'titleUrl':'https://evil.example/watch?v=abcdefghijk'},
                    {'titleUrl':'https://youtu.be/12345678901','time':'bad'}])
        result = importer.import_folder(self.db, self.folder)
        self.assertEqual(result['statistics']['video_events'], 4)
        self.assertEqual(result['statistics']['unique_videos'], 3)
        self.assertEqual(result['statistics']['ads'], 1)
        self.assertEqual(result['statistics']['invalid_rows'], 1)
        self.assertEqual(result['statistics']['non_video_rows'], 2)
        self.assertEqual(result['statistics']['invalid_times'], 1)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM watch_events').fetchone()[0], 6)
        self.assertEqual(self.db.execute('SELECT watched_at FROM watch_events WHERE source_row=0').fetchone()[0], '2026-09-09T00:00:00+00:00')
        self.assertEqual(storage.get_video(self.db,'abcdefghijk')['title'], 'Nhạc 音楽')

    def test_reimport_and_new_export_keep_review_without_accumulating_active_counts(self):
        self.write([event(), event()])
        first = importer.import_folder(self.db, self.folder)
        storage.set_video_group(self.db, 'abcdefghijk', 'music')
        again = importer.import_folder(self.db, self.folder)
        self.assertTrue(again['reused'])
        self.assertEqual(first['import_id'], again['import_id'])
        self.write([event()])
        new = importer.import_folder(self.db, self.folder)
        self.assertNotEqual(first['import_id'], new['import_id'])
        self.assertEqual(storage.get_setting(self.db,'active_import'), str(new['import_id']))
        self.assertEqual(storage.get_video(self.db,'abcdefghijk')['user_group'], 'music')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM watch_events WHERE import_id=?', (new['import_id'],)).fetchone()[0],1)

    def test_library_is_scoped_to_history_and_does_not_add_unwatched_videos(self):
        self.write([event()])
        library = self.folder/'music library songs.csv'
        library.write_text('Video ID\nabcdefghijk\nlmnopqrstuv\n',encoding='utf-8')
        result = importer.import_folder(self.db,self.folder)
        self.assertEqual(result['statistics']['library_matches'],1)
        self.assertIsNone(storage.get_video(self.db,'lmnopqrstuv'))
        self.assertTrue(json.loads(storage.get_video(self.db,'abcdefghijk')['metadata_json'])['music_library'])
        library.write_text('Video ID\nlmnopqrstuv\n',encoding='utf-8')
        updated = importer.import_folder(self.db,self.folder)
        self.assertEqual(updated['import_id'],result['import_id'])
        self.assertEqual(updated['statistics']['library_matches'],0)

    def test_bad_input_keeps_active_import(self):
        self.write([event()])
        first = importer.import_folder(self.db,self.folder)
        for content in ('{', '{}', '[1,2]'):
            self.history.write_text(content)
            with self.subTest(content=content), self.assertRaises(ValueError):
                importer.import_folder(self.db,self.folder)
            self.assertEqual(storage.get_setting(self.db,'active_import'),str(first['import_id']))

    def test_multiple_sources_require_explicit_selection(self):
        self.write([event()])
        other = self.folder/'other'/'watch-history.json'
        other.parent.mkdir()
        other.write_text('[]')
        with self.assertRaisesRegex(ValueError,'--history'):
            importer.import_folder(self.db,self.folder)
        result = importer.import_folder(self.db,self.folder,history='history/watch-history.json')
        self.assertEqual(result['statistics']['unique_videos'],1)

    def test_missing_html_and_outside_selection_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'watch-history.json'):
            importer.import_folder(self.db,self.folder)
        (self.folder/'watch-history.html').write_text('<html>')
        with self.assertRaisesRegex(ValueError,'HTML'):
            importer.import_folder(self.db,self.folder)
        outside=self.root/'watch-history.json'
        outside.write_text('[]')
        with self.assertRaises(ValueError):
            importer.import_folder(self.db,self.folder,history='../watch-history.json')
