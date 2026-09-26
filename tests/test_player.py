"""Unit tests for Auralytica Local Media Player backend engine."""

import io
import os
from pathlib import Path
import tempfile
import unittest

from auralytica import storage
from auralytica import player


class PlayerBackendTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.db_path = self.root / "state.sqlite3"
        self.music_dir = self.root / "music"
        self.music_dir.mkdir(parents=True, exist_ok=True)
        self.db = storage.open_database(self.db_path)
        self.addCleanup(self.db.close)

    def test_database_schema_v5_creates_player_tables(self):
        tables = {row[0] for row in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({'player_playlists', 'player_playlist_tracks', 'player_favorites', 'player_track_cache'} <= tables)
        self.assertEqual(self.db.execute("PRAGMA user_version").fetchone()[0], 5)

    def test_scanner_detects_audio_files_and_caches_metadata(self):
        # Create dummy audio files
        sub_dir = self.music_dir / "Apple Music"
        sub_dir.mkdir(parents=True, exist_ok=True)
        file1 = sub_dir / "Artist One - Song A.m4a"
        file1.write_bytes(b"dummy-audio-content-1")
        file2 = self.music_dir / "Artist Two - Song B.mp3"
        file2.write_bytes(b"dummy-audio-content-2")

        # Initial scan
        tracks = player.scan_library(self.db, self.music_dir)
        self.assertEqual(len(tracks), 2)
        paths = {t['path'] for t in tracks}
        self.assertIn(str(file1.resolve()), paths)
        self.assertIn(str(file2.resolve()), paths)

        # Cache check
        cached_count = self.db.execute("SELECT COUNT(*) FROM player_track_cache").fetchone()[0]
        self.assertEqual(cached_count, 2)

        # Subsequent scan should read from cache
        tracks_again = player.scan_library(self.db, self.music_dir)
        self.assertEqual(len(tracks_again), 2)

    def test_playlists_crud_operations(self):
        # 1. Create playlist
        pl1 = player.create_playlist(self.db, "Acoustic Vibes", "Chill acoustic songs")
        self.assertEqual(pl1['name'], "Acoustic Vibes")
        self.assertEqual(pl1['description'], "Chill acoustic songs")
        self.assertEqual(pl1['track_count'], 0)

        # 2. Add tracks to playlist
        track_a = str((self.music_dir / "a.mp3").resolve())
        track_b = str((self.music_dir / "b.mp3").resolve())
        player.add_tracks_to_playlist(self.db, pl1['id'], [track_a, track_b])

        pl1_updated = player.get_playlist(self.db, pl1['id'])
        self.assertEqual(pl1_updated['track_count'], 2)
        tracks = player.get_playlist_tracks(self.db, pl1['id'])
        self.assertEqual(len(tracks), 2)
        self.assertEqual(tracks[0]['track_path'], track_a)
        self.assertEqual(tracks[1]['track_path'], track_b)

        # 3. Reorder tracks
        player.reorder_playlist_tracks(self.db, pl1['id'], [track_b, track_a])
        tracks_reordered = player.get_playlist_tracks(self.db, pl1['id'])
        self.assertEqual(tracks_reordered[0]['track_path'], track_b)
        self.assertEqual(tracks_reordered[1]['track_path'], track_a)

        # 4. Remove a track
        player.remove_track_from_playlist(self.db, pl1['id'], track_b)
        tracks_after_removal = player.get_playlist_tracks(self.db, pl1['id'])
        self.assertEqual(len(tracks_after_removal), 1)
        self.assertEqual(tracks_after_removal[0]['track_path'], track_a)

        # 5. Update playlist details
        player.update_playlist(self.db, pl1['id'], "Lo-fi Chill", "Updated desc")
        pl1_renamed = player.get_playlist(self.db, pl1['id'])
        self.assertEqual(pl1_renamed['name'], "Lo-fi Chill")

        # 6. Delete playlist
        player.delete_playlist(self.db, pl1['id'])
        self.assertIsNone(player.get_playlist(self.db, pl1['id']))

    def test_favorites_toggle_and_listing(self):
        track_path = str((self.music_dir / "favorite.m4a").resolve())
        
        # Toggle ON
        is_fav = player.toggle_favorite(self.db, track_path)
        self.assertTrue(is_fav)
        favs = player.get_favorites(self.db)
        self.assertIn(track_path, favs)

        # Toggle OFF
        is_fav_again = player.toggle_favorite(self.db, track_path)
        self.assertFalse(is_fav_again)
        self.assertNotIn(track_path, player.get_favorites(self.db))

    def test_m3u8_export_and_import(self):
        file1 = self.music_dir / "Song 1.mp3"
        file2 = self.music_dir / "Song 2.m4a"
        file1.write_bytes(b"1")
        file2.write_bytes(b"2")

        pl = player.create_playlist(self.db, "Road Trip")
        player.add_tracks_to_playlist(self.db, pl['id'], [str(file1.resolve()), str(file2.resolve())])

        # Export M3U8 content
        m3u_text = player.export_m3u8(self.db, pl['id'])
        self.assertIn("#EXTM3U", m3u_text)
        self.assertIn("Song 1.mp3", m3u_text)
        self.assertIn("Song 2.m4a", m3u_text)

        # Import M3U8 content
        imported_pl = player.import_m3u8(self.db, "Imported Trip", m3u_text, base_dir=self.music_dir)
        self.assertEqual(imported_pl['name'], "Imported Trip")
        self.assertEqual(imported_pl['track_count'], 2)

    def test_save_track_metadata_and_extract_art(self):
        mp3_path = self.music_dir / "untagged.mp3"
        mp3_path.write_bytes(b"dummy-mp3-bytes")
        fake_cover = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"

        meta = player.save_track_metadata(
            self.db,
            mp3_path,
            title="Sunny Day",
            artist="Indie Band",
            album="Summer EP",
            genre="Acoustic",
            year="2024",
            cover_bytes=fake_cover,
            cover_mime="image/png",
            rename_file=False,
        )
        self.assertEqual(meta['title'], "Sunny Day")
        self.assertEqual(meta['artist'], "Indie Band")
        self.assertEqual(meta['album'], "Summer EP")
        self.assertEqual(meta['year'], "2024")
        self.assertTrue(meta['has_art'])

        # Test cover art extraction
        art = player.extract_cover_art(mp3_path)
        self.assertIsNotNone(art)
        data, mime = art
        self.assertEqual(data, fake_cover)

    def test_audio_streaming_range_request(self):
        audio_file = self.music_dir / "stream_test.mp3"
        content = b"0123456789ABCDEF" * 64  # 1024 bytes
        audio_file.write_bytes(content)

        # Full stream (200)
        res_full = player.stream_audio_file(audio_file)
        self.assertEqual(res_full.status_code, 200)
        self.assertEqual(res_full.headers["Content-Length"], "1024")

        # Range request (206)
        res_range = player.stream_audio_file(audio_file, range_header="bytes=100-199")
        self.assertEqual(res_range.status_code, 206)
        self.assertEqual(res_range.headers["Content-Range"], "bytes 100-199/1024")
        self.assertEqual(res_range.headers["Content-Length"], "100")

    def test_path_safety_check(self):
        self.assertTrue(player.is_safe_path(self.music_dir, self.music_dir / "song.mp3"))
        self.assertTrue(player.is_safe_path(self.music_dir, self.music_dir / "sub" / "song.m4a"))
        self.assertFalse(player.is_safe_path(self.music_dir, self.root / "other.txt"))
        self.assertFalse(player.is_safe_path(self.music_dir, "/etc/passwd"))

    def test_player_api_endpoints_via_testclient(self):
        from fastapi.testclient import TestClient
        from auralytica import web

        # Create audio files
        f1 = self.music_dir / "api_test_1.mp3"
        f1.write_bytes(b"content-1" * 100)

        app = web.create_app(self.db_path)
        client = TestClient(app, base_url="http://127.0.0.1:8765")

        headers = {"Origin": "http://127.0.0.1:8765"}

        # 1. Library scan
        res_lib = client.get(f"/api/player/library?folder={self.music_dir}")
        self.assertEqual(res_lib.status_code, 200)
        data = res_lib.json()
        self.assertEqual(len(data['tracks']), 1)
        self.assertEqual(data['tracks'][0]['filename'], "api_test_1.mp3")

        # 2. Audio stream
        res_stream = client.get(f"/api/player/stream?path={f1.resolve()}", headers={**headers, "Range": "bytes=0-49"})
        self.assertEqual(res_stream.status_code, 206)
        self.assertEqual(res_stream.headers["Content-Length"], "50")

        # 3. Playlists API
        res_pl_create = client.post("/api/player/playlists", json={"name": "API Playlist", "description": "Test"}, headers=headers)
        self.assertEqual(res_pl_create.status_code, 200)
        pl_id = res_pl_create.json()['id']

        res_pl_list = client.get("/api/player/playlists")
        self.assertEqual(len(res_pl_list.json()), 1)

        # Add track to playlist
        res_add = client.post(f"/api/player/playlists/{pl_id}/tracks", json={"track_paths": [str(f1.resolve())]}, headers=headers)
        self.assertEqual(res_add.status_code, 200)
        self.assertEqual(len(res_add.json()['tracks']), 1)

        # 4. Favorites toggle API
        res_fav = client.post("/api/player/favorites/toggle", json={"track_path": str(f1.resolve())}, headers=headers)
        self.assertEqual(res_fav.status_code, 200)
        self.assertTrue(res_fav.json()['is_favorite'])

        # 5. Metadata update API
        res_meta = client.post(
            "/api/player/metadata",
            data={
                "path": str(f1.resolve()),
                "title": "Renamed API Song",
                "artist": "API Artist",
                "album": "API Album",
                "genre": "Rock",
                "year": "2025",
                "rename_file": False,
            },
            headers=headers,
        )
        self.assertEqual(res_meta.status_code, 200)
        self.assertEqual(res_meta.json()['title'], "Renamed API Song")


