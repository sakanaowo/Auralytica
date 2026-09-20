import json
from pathlib import Path
import tempfile
import unittest

from auralytica import storage
from auralytica.importer import import_folder


class DedupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.takeout = self.root / 'Takeout' / 'history'
        self.takeout.mkdir(parents=True)
        self.rows = [
            self.row('aaaaaaaaaaa', 'Shoujo A (Official Video)', 'Artist'),
            self.row('bbbbbbbbbbb', '少女A', 'Artist'),
            self.row('ccccccccccc', 'Home', 'Singer One'),
            self.row('ddddddddddd', 'HOME [Official Audio]', 'Singer Two'),
            self.row('eeeeeeeeeee', 'Shoujo A - live', 'Artist'),
            self.row('fffffffffff', 'Shoujo A remix', 'DJ'),
        ]
        (self.takeout / 'watch-history.json').write_text(json.dumps(self.rows))
        self.database = self.root / 'state.sqlite3'
        self.db = storage.open_database(self.database)
        self.addCleanup(self.db.close)
        import_folder(self.db, self.takeout.parent)
        for video_id in [row['titleUrl'].rsplit('/', 1)[-1] for row in self.rows]:
            storage.set_video_group(self.db, video_id, 'music')

    @staticmethod
    def row(video_id, title, channel):
        return {'titleUrl': f'https://youtu.be/{video_id}', 'title': f'Watched {title}',
                'subtitles': [{'name': channel}]}

    def test_normalization_preserves_version_markers(self):
        from auralytica.dedup import normalize_title
        self.assertEqual(normalize_title('  ＳＨＯＵＪＯ—Ａ (Official Video)  ')['key'], 'shoujo a')
        self.assertEqual(normalize_title('Shoujo A - LIVE')['markers'], ['live'])
        self.assertEqual(normalize_title('Shoujo A remix')['markers'], ['remix'])
        self.assertEqual(normalize_title('Song (unknown words)')['key'], 'song unknown words')

    def test_alias_groups_multilingual_titles_without_excluding_versions(self):
        from auralytica import dedup
        alias = dedup.confirm_aliases(self.db, ['Shoujo A', '少女A'], source='user')
        repeated = dedup.confirm_aliases(self.db, ['Shoujo A', '少女A'], source='user')
        self.assertEqual(repeated['song_key'], alias['song_key'])
        self.assertTrue(repeated['reused'])
        run = dedup.create_run(self.db)
        page = dedup.list_groups(self.db, run['run_id'])
        group = next(group for group in page['items'] if {'aaaaaaaaaaa', 'bbbbbbbbbbb'} <=
                     {member['video_id'] for member in group['members']})
        self.assertEqual(group['evidence_type'], 'confirmed_alias')
        self.assertEqual({m['keep'] for m in group['members']}, {True})
        self.assertEqual({m['raw_title'] for m in group['members']} & {'Shoujo A (Official Video)', '少女A'},
                         {'Shoujo A (Official Video)', '少女A'})
        self.assertEqual(alias['source'], 'user')

    def test_common_title_artist_conflict_is_review_only_and_run_becomes_stale(self):
        from auralytica import dedup
        run = dedup.create_run(self.db)
        page = dedup.list_groups(self.db, run['run_id'])
        home = next(group for group in page['items'] if group['title_key'] == 'home')
        self.assertTrue(home['artist_conflict'])
        self.assertEqual(home['evidence_type'], 'normalized_title')
        self.assertTrue(all(member['keep'] for member in home['members']))
        storage.set_video_group(self.db, 'ccccccccccc', 'rest')
        self.assertTrue(dedup.get_run(self.db, run['run_id'])['stale'])

    def test_ambiguous_alias_does_not_choose_a_song_key_arbitrarily(self):
        from auralytica import dedup
        dedup.confirm_aliases(self.db, ['Shoujo A', '少女A'], source='fixture-one')
        dedup.confirm_aliases(self.db, ['Shoujo A', 'Girl A'], source='fixture-two')
        run = dedup.create_run(self.db)
        groups = dedup.list_groups(self.db, run['run_id'])['items']
        shoujo = next(group for group in groups if group['title_key'] == 'shoujo a')
        self.assertEqual(shoujo['evidence_type'], 'normalized_title')
        self.assertNotIn('bbbbbbbbbbb', {member['video_id'] for member in shoujo['members']})

    def test_schema_four_migration_keeps_existing_review_data(self):
        self.assertEqual(self.db.execute('PRAGMA user_version').fetchone()[0], 4)
        self.assertEqual(self.db.execute("SELECT user_group FROM videos WHERE id='aaaaaaaaaaa'").fetchone()[0], 'music')
        tables = {row[0] for row in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({'song_aliases', 'dedup_runs', 'dedup_groups', 'dedup_members',
                         'download_selections', 'rejected_groups'} <= tables)


if __name__ == '__main__':
    unittest.main()
