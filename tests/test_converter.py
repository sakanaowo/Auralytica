import json
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient

from auralytica.converter import clean_title, parse_artist_title, scan_directory, is_apple_music_compatible
from auralytica.web import create_app
from auralytica.storage import open_database

ORIGIN = 'http://127.0.0.1:8765'


class ConverterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.database = self.root / 'state.sqlite3'
        self.app = create_app(self.database)
        self.client = TestClient(self.app, base_url=ORIGIN)
        self.addCleanup(self.client.close)

    def test_clean_title_removes_video_ids_and_clutter(self):
        cases = [
            ('09 Pure SkyGenshin Impact [nIS-srtakdM].webm', '09 Pure SkyGenshin Impact'),
            ('400 A.M [_sOKkON_UnQ].webm', '400 A.M'),
            ('505 [qU9mHegkTc4].webm', '505'),
            ('ABBA - Lay All Your Love On Me Official Lyric Video [ulZQTrV8QlQ].webm', 'ABBA - Lay All Your Love On Me'),
            ('Adele - Skyfall Official Lyric Video [DeumyOzKqgI].webm', 'Adele - Skyfall'),
            ('Alan Walker K-391 - Ignite Instrumental [rsH1A1MX5_Q].webm', 'Alan Walker K-391 - Ignite Instrumental'),
            ('Song (Official Music Video) [abcdefghijk].m4a', 'Song'),
            ('Artist - Track [HQ Audio] [12345678901]', 'Artist - Track'),
        ]
        for raw, expected in cases:
            self.assertEqual(clean_title(raw), expected)

    def test_parse_artist_title(self):
        artist, title = parse_artist_title('ABBA - The Winner Takes It All')
        self.assertEqual(artist, 'ABBA')
        self.assertEqual(title, 'The Winner Takes It All')

        artist, title = parse_artist_title('505', fallback_artist='Arctic Monkeys')
        self.assertEqual(artist, 'Arctic Monkeys')
        self.assertEqual(title, '505')

    def test_is_apple_music_compatible(self):
        self.assertTrue(is_apple_music_compatible('.m4a'))
        self.assertTrue(is_apple_music_compatible('.mp3'))
        self.assertTrue(is_apple_music_compatible('.aiff'))
        self.assertFalse(is_apple_music_compatible('.webm'))
        self.assertFalse(is_apple_music_compatible('.opus'))
        self.assertFalse(is_apple_music_compatible('.ogg'))

    def test_scan_directory_and_api(self):
        music_dir = self.root / 'music'
        music_dir.mkdir()
        (music_dir / 'Adele - Skyfall Official Video [DeumyOzKqgI].webm').write_bytes(b'dummy webm content')
        (music_dir / 'Clean Song.m4a').write_bytes(b'dummy m4a content')

        result = scan_directory(self.database, music_dir)
        self.assertEqual(result['total'], 2)
        self.assertEqual(result['incompatible_count'], 1)
        self.assertEqual(result['compatible_count'], 1)
        self.assertEqual(result['has_video_id_count'], 1)

        # Test API
        res = self.client.get('/api/converter/scan', params={'directory': str(music_dir)})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['total'], 2)
        self.assertEqual(data['items'][0]['cleaned_stem'], 'Adele - Skyfall')

        # Test Rename API
        rename_res = self.client.post(
            '/api/converter/rename',
            headers={'Origin': ORIGIN},
            json={'items': [{'source_path': str(music_dir / 'Clean Song.m4a'), 'new_name': 'My Clean Song'}]}
        )
        self.assertEqual(rename_res.status_code, 200)
        self.assertTrue((music_dir / 'My Clean Song.m4a').exists())
