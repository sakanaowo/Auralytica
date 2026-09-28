import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from auralytica import downloader, storage, web


class DirectDownloadUnitTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.db_path = self.root / "state.sqlite3"
        self.db = storage.open_database(str(self.db_path))

    def tearDown(self):
        self.db.close()
        self.temp_dir.cleanup()

    def test_parse_youtube_url_variations(self):
        """Test URL parsing for watch, youtu.be, shorts, embed, and playlist."""
        # Standard watch
        res1 = downloader.parse_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ&si=12345&t=10s")
        self.assertEqual(res1, {"type": "video", "id": "dQw4w9WgXcQ"})

        # Short link
        res2 = downloader.parse_youtube_url("https://youtu.be/dQw4w9WgXcQ?feature=shared")
        self.assertEqual(res2, {"type": "video", "id": "dQw4w9WgXcQ"})

        # Shorts
        res3 = downloader.parse_youtube_url("https://www.youtube.com/shorts/dQw4w9WgXcQ")
        self.assertEqual(res3, {"type": "video", "id": "dQw4w9WgXcQ"})

        # Embed
        res4 = downloader.parse_youtube_url("https://www.youtube.com/embed/dQw4w9WgXcQ")
        self.assertEqual(res4, {"type": "video", "id": "dQw4w9WgXcQ"})

        # Bare ID
        res5 = downloader.parse_youtube_url("dQw4w9WgXcQ")
        self.assertEqual(res5, {"type": "video", "id": "dQw4w9WgXcQ"})

        # Playlist URL
        res6 = downloader.parse_youtube_url("https://www.youtube.com/playlist?list=PL1234567890abcdef")
        self.assertEqual(res6, {"type": "playlist", "id": "PL1234567890abcdef"})

        # Invalid URL
        res7 = downloader.parse_youtube_url("https://example.com/not-youtube")
        self.assertIsNone(res7)

    def test_resolve_direct_urls_videos_and_playlist(self):
        """Test resolve_direct_urls with single videos and a mocked playlist."""
        raw_urls = [
            "https://www.youtube.com/watch?v=abcdefghijk",
            "https://youtu.be/12345678901",
            "https://www.youtube.com/playlist?list=PLtestplaylist",
            "invalid-url-here",
        ]

        mock_playlist_info = {
            "_type": "playlist",
            "id": "PLtestplaylist",
            "title": "My Awesome Playlist",
            "entries": [
                {
                    "id": "playlist_v01",
                    "title": "Playlist Track 1",
                    "uploader": "Playlist Artist",
                    "duration": 210,
                },
                {
                    "id": "playlist_v02",
                    "title": "Playlist Track 2",
                    "uploader": "Playlist Artist",
                    "duration": 185,
                },
            ],
        }

        import yt_dlp
        with patch.object(yt_dlp.YoutubeDL, "extract_info", return_value=mock_playlist_info):
            result = downloader.resolve_direct_urls(raw_urls)

        self.assertEqual(len(result["invalid_urls"]), 1)
        self.assertIn("invalid-url-here", result["invalid_urls"])

        video_ids = [v["video_id"] for v in result["videos"]]
        self.assertIn("abcdefghijk", video_ids)
        self.assertIn("12345678901", video_ids)
        self.assertIn("playlist_v01", video_ids)
        self.assertIn("playlist_v02", video_ids)
        self.assertEqual(len(video_ids), 4)

    def test_create_direct_batch_creates_batch_and_items(self):
        """Test create_direct_batch registers items into database and returns batch id."""
        videos = [
            {
                "video_id": "direct_vid01",
                "title": "Direct Song One",
                "channel": "Direct Channel",
                "duration": 200,
                "thumbnail_url": "https://i.ytimg.com/vi/direct_vid01/hqdefault.jpg",
            },
            {
                "video_id": "direct_vid02",
                "title": "Direct Song Two",
                "channel": "Direct Channel",
                "duration": 150,
                "thumbnail_url": "https://i.ytimg.com/vi/direct_vid02/hqdefault.jpg",
            },
        ]
        output_dir = str(self.root / "Music")

        with patch("auralytica.downloader.start_batch_worker") as mock_start:
            batch_id = downloader.create_direct_batch(
                self.db,
                videos=videos,
                output_dir=output_dir,
                audio_format="m4a_alac",
                database_path=str(self.db_path),
            )

        self.assertIsInstance(batch_id, int)
        batch = downloader.get_batch(self.db, batch_id)
        self.assertEqual(batch["output_dir"], output_dir)
        self.assertEqual(batch["format"], "m4a_alac")
        self.assertEqual(batch["status"], "queued")
        self.assertEqual(batch["total"], 2)

        # Verify videos table populated
        vid_row = storage.get_video(self.db, "direct_vid01")
        self.assertIsNotNone(vid_row)
        self.assertEqual(vid_row["title"], "Direct Song One")
        self.assertEqual(vid_row["effective_group"], "music")
        self.assertEqual(vid_row["user_group"], "music")

        mock_start.assert_called_once()

    def test_create_direct_batch_mp3_format_normalization_and_custom_metadata(self):
        """Test that mp3_320 normalizes to mp3 and custom title/artist are preserved."""
        videos = [
            {
                "video_id": "custom_vid01",
                "title": "Custom Song Title",
                "artist": "Custom Singer",
                "album": "Custom Album",
            }
        ]
        with patch("auralytica.downloader.start_batch_worker"):
            batch_id = downloader.create_direct_batch(
                self.db,
                videos=videos,
                output_dir=str(self.root / "Music"),
                audio_format="mp3_320",
                concurrency=4,
            )
        batch = downloader.get_batch(self.db, batch_id)
        self.assertEqual(batch["format"], "mp3")
        self.assertEqual(batch["concurrency"], 4)
        vid_row = storage.get_video(self.db, "custom_vid01")
        self.assertEqual(vid_row["title"], "Custom Song Title")
        self.assertEqual(vid_row["channel_name"], "Custom Singer")

    def test_direct_download_api_endpoints(self):
        """Test API endpoints /api/download/direct/resolve and /api/download/direct."""
        app = web.create_app(str(self.db_path), port=8765)
        client = TestClient(app, base_url="http://127.0.0.1:8765")
        headers = {"Origin": "http://127.0.0.1:8765"}

        # 1. Resolve endpoint
        resolve_resp = client.post(
            "/api/download/direct/resolve",
            json={"urls": ["https://www.youtube.com/watch?v=dQw4w9WgXcQ", "garbage_link"]},
            headers=headers,
        )
        self.assertEqual(resolve_resp.status_code, 200)
        resolve_data = resolve_resp.json()
        self.assertEqual(len(resolve_data["videos"]), 1)
        self.assertEqual(resolve_data["videos"][0]["video_id"], "dQw4w9WgXcQ")
        self.assertEqual(resolve_data["invalid_urls"], ["garbage_link"])

        # 2. Submit endpoint
        with patch("auralytica.downloader.start_batch_worker"):
            submit_resp = client.post(
                "/api/download/direct",
                json={
                    "videos": [
                        {
                            "video_id": "dQw4w9WgXcQ",
                            "title": "Never Gonna Give You Up",
                            "channel": "Rick Astley",
                            "duration": 213,
                        }
                    ],
                    "output_dir": str(self.root / "Music"),
                    "format": "m4a_alac",
                },
                headers=headers,
            )
        self.assertEqual(submit_resp.status_code, 200)
        submit_data = submit_resp.json()
        self.assertIn("batch_id", submit_data)
        self.assertEqual(submit_data["total_items"], 1)
        self.assertEqual(submit_data["status"], "queued")

    def test_cache_single_track_populates_player_track_cache(self):
        """Test cache_single_track indexes newly downloaded audio files."""
        from auralytica import player
        from mutagen.id3 import ID3, TIT2, TPE1

        music_dir = self.root / "Music"
        music_dir.mkdir(parents=True, exist_ok=True)
        track_file = music_dir / "test_download.mp3"
        track_file.write_bytes(b"\xff\xfb\x90\x44" + b"\x00" * 1000)

        tags = ID3()
        tags.add(TIT2(encoding=3, text="Downloaded Song"))
        tags.add(TPE1(encoding=3, text="Downloaded Artist"))
        tags.save(str(track_file))

        res = player.cache_single_track(self.db, str(track_file))
        self.assertIsNotNone(res)
        self.assertEqual(res["title"], "Downloaded Song")
        self.assertEqual(res["artist"], "Downloaded Artist")

        # Verify database row
        row = self.db.execute("SELECT * FROM player_track_cache WHERE track_path=?", (str(track_file.resolve()),)).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["title"], "Downloaded Song")
        self.assertEqual(row["artist"], "Downloaded Artist")
