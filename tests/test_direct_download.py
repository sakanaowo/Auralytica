import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from auralytica import download_controls, downloader, storage, web


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
        self.assertEqual(batch["kind"], "direct")
        self.assertEqual(batch["output_dir"], output_dir)
        self.assertEqual(batch["format"], "m4a_alac")
        self.assertEqual(batch["status"], "queued")
        self.assertEqual(batch["total"], 2)

        # A videos row backs the download_items FK, without claiming a Takeout group.
        vid_row = storage.get_video(self.db, "direct_vid01")
        self.assertIsNotNone(vid_row)
        self.assertIsNone(vid_row["user_group"])
        tags = self.db.execute(
            "SELECT title, artist FROM direct_download_items WHERE batch_id=? AND video_id=?",
            (batch_id, "direct_vid01"),
        ).fetchone()
        self.assertEqual(tuple(tags), ("Direct Song One", "Direct Channel"))

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
        tags = self.db.execute(
            "SELECT title, artist FROM direct_download_items WHERE batch_id=?", (batch_id,)
        ).fetchone()
        self.assertEqual(tuple(tags), ("Custom Song Title", "Custom Singer"))

    def test_direct_download_api_endpoints(self):
        """Test API endpoints /api/download/direct/resolve and /api/download/direct."""
        app = web.create_app(str(self.db_path), port=8765)
        client = TestClient(app, base_url="http://127.0.0.1:8765")
        headers = {"Origin": "http://127.0.0.1:8765"}

        # 1. Resolve endpoint (yt-dlp metadata mocked: no network in unit tests)
        fake_info = {"title": "Rick Astley - Never Gonna Give You Up", "uploader": "Rick Astley", "duration": 213}
        import yt_dlp
        with patch.object(yt_dlp.YoutubeDL, "extract_info", return_value=fake_info):
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


class DirectDownloadResolveTests(unittest.TestCase):
    def test_unreachable_videos_and_playlist_placeholders_are_reported_not_queued(self):
        import yt_dlp

        playlist = {"entries": [
            {"id": "okPlaylist1", "title": "Artist - Song", "uploader": "Artist"},
            {"id": "gonePlayli1", "title": "[Private video]", "uploader": None},
            {"id": "gonePlayli2", "title": "[Deleted video]"},
        ]}

        def extract(self_, url, download=False):
            if "playlist" in url:
                return playlist
            if "privateVid1" in url:
                raise yt_dlp.utils.DownloadError("ERROR: [youtube] privateVid1: Private video. Sign in")
            return {"title": "Live Song", "uploader": "Live Artist", "duration": 100}

        with patch.object(yt_dlp.YoutubeDL, "extract_info", extract):
            result = downloader.resolve_direct_urls([
                "https://youtu.be/privateVid1",
                "https://youtu.be/liveVideo01",
                "https://www.youtube.com/playlist?list=PLx",
            ])

        self.assertEqual(sorted(v["video_id"] for v in result["videos"]), ["liveVideo01", "okPlaylist1"])
        gone = {item["video_id"]: item for item in result["unavailable"]}
        self.assertEqual(set(gone), {"privateVid1", "gonePlayli1", "gonePlayli2"})
        self.assertEqual(gone["privateVid1"]["code"], "unavailable")
        self.assertEqual(gone["privateVid1"]["url"], "https://youtu.be/privateVid1")
        self.assertEqual(result["invalid_urls"], [])
        self.assertFalse(result["truncated"])

    def test_resolve_caps_video_count(self):
        import yt_dlp
        playlist = {"entries": [{"id": f"capVideo{i:03d}", "title": f"Song {i}"} for i in range(5)]}
        with patch.object(downloader, "MAX_DIRECT_VIDEOS", 3), \
                patch.object(yt_dlp.YoutubeDL, "extract_info", return_value=playlist):
            result = downloader.resolve_direct_urls(["https://www.youtube.com/playlist?list=PLcap"])
        self.assertEqual(len(result["videos"]), 3)
        self.assertTrue(result["truncated"])


class DirectDownloadIsolationTests(unittest.TestCase):
    """Quick-download batches must not alter Takeout review state."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.db_path = self.root / "state.sqlite3"
        self.db = storage.open_database(str(self.db_path))
        self.addCleanup(self.db.close)
        self.db.execute(
            "INSERT INTO videos(id, title, channel_name, auto_group, user_group) "
            "VALUES ('takeoutVid1', 'Takeout Title', 'Takeout Channel', 'rest', 'rest')"
        )

    def _direct(self, video_id="takeoutVid1", title="Edited Title", artist="Edited Artist"):
        return downloader.create_direct_batch(
            self.db, videos=[{"video_id": video_id, "title": title, "artist": artist}],
            output_dir=str(self.root / "Music"), audio_format="raw", launcher=lambda *_: None,
        )

    def test_existing_takeout_video_is_not_rewritten(self):
        batch_id = self._direct()
        row = storage.get_video(self.db, "takeoutVid1")
        self.assertEqual((row["title"], row["channel_name"], row["user_group"]),
                         ("Takeout Title", "Takeout Channel", "rest"))
        status = download_controls.batch_status(self.db, batch_id)
        self.assertEqual(status["items"][0]["title"], "Edited Title")

    def test_direct_batch_does_not_lock_review_but_occupies_worker(self):
        from auralytica import batches
        self._direct()
        storage.assert_review_unlocked(self.db)  # does not raise
        self.assertFalse(storage.review_locked(self.db))
        with self.assertRaisesRegex(storage.BatchBusyError, "Tải nhanh"):
            batches.create_batch(self.db, str(self.root / "Music"))
        with self.assertRaises(storage.BatchBusyError):
            self._direct(video_id="anotherVid1")

    def test_takeout_batch_still_locks_review(self):
        self.db.execute("INSERT INTO download_batches(output_dir, status) VALUES ('/tmp/x', 'running')")
        self.assertTrue(storage.review_locked(self.db))
        with self.assertRaises(storage.BatchBusyError):
            self._direct()

    def test_skipping_failed_direct_items_keeps_takeout_selection(self):
        batch_id = self._direct()
        self.db.execute("UPDATE download_items SET status='failed' WHERE batch_id=?", (batch_id,))
        self.db.execute("UPDATE download_batches SET status='partial' WHERE id=?", (batch_id,))
        download_controls.skip_failed(self.db, batch_id)
        self.assertIsNone(self.db.execute(
            "SELECT 1 FROM download_selections WHERE video_id='takeoutVid1'").fetchone())

    def test_run_batch_tags_and_names_files_from_edited_metadata(self):
        batch_id = self._direct(title="Edited Title", artist="Edited Artist")

        def adapter(video_id, directory, progress, stopped, lock_fd):
            path = directory / "audio.webm"
            path.write_bytes(b"fixture audio")
            return dict(id=video_id, path=str(path), acodec="opus", vcodec="none",
                        title="YouTube Title", artist="YouTube Channel")

        result = downloader.run_batch(self.db, batch_id, adapter=adapter)
        self.assertEqual(result["status"], "completed")
        file_path = Path(self.db.execute(
            "SELECT file_path FROM download_items WHERE batch_id=?", (batch_id,)).fetchone()[0])
        self.assertEqual(file_path.name, "Edited Artist - Edited Title.webm")

    def test_workflow_reports_busy_without_review_lock(self):
        self._direct()
        app = web.create_app(str(self.db_path), port=8765)
        client = TestClient(app, base_url="http://127.0.0.1:8765")
        workflow = client.get("/api/workflow").json()
        self.assertFalse(workflow["batch_locked"])
        self.assertTrue(workflow["download_busy"])
        busy = client.post("/api/download/direct", headers={"Origin": "http://127.0.0.1:8765"}, json={
            "videos": [{"video_id": "anotherVid1"}], "output_dir": str(self.root / "Music")})
        self.assertEqual(busy.status_code, 409)
        invalid = client.post("/api/download/direct", headers={"Origin": "http://127.0.0.1:8765"}, json={
            "videos": [{"video_id": "bad"}], "output_dir": str(self.root / "Music")})
        self.assertEqual(invalid.status_code, 422)


class DirectDownloadMigrationTests(unittest.TestCase):
    def test_v6_direct_batches_get_kind_and_backfilled_tags(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "legacy.sqlite3"
            db = storage.open_database(path)
            db.close()
            legacy = sqlite3.connect(path)
            # Rebuild the v6 shape: drop what v7 added, keep a v6-era direct batch.
            legacy.executescript("""
                DROP TABLE direct_download_items;
                ALTER TABLE download_batches DROP COLUMN kind;
                INSERT INTO videos(id, title, channel_name) VALUES ('legacyVid01', 'Old Edited', 'Old Artist');
                INSERT INTO download_batches(id, output_dir, status) VALUES (5, '/tmp/m', 'completed');
                INSERT INTO download_batches(id, output_dir, status) VALUES (6, '/tmp/m', 'completed');
                INSERT INTO download_items(batch_id, video_id, status) VALUES (5, 'legacyVid01', 'completed');
                INSERT INTO settings(key, value) VALUES ('batch_is_direct:5', '1');
                PRAGMA user_version=6;
            """)
            legacy.close()
            db = storage.open_database(path)
            try:
                kinds = dict(db.execute("SELECT id, kind FROM download_batches").fetchall())
                self.assertEqual(kinds, {5: "direct", 6: "takeout"})
                tags = db.execute("SELECT title, artist FROM direct_download_items WHERE batch_id=5").fetchone()
                self.assertEqual(tuple(tags), ("Old Edited", "Old Artist"))
                self.assertIsNone(db.execute("SELECT 1 FROM settings WHERE key LIKE 'batch_is_direct:%'").fetchone())
            finally:
                db.close()
