from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from auralytica import storage


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "nested" / "library.sqlite3"

    def open(self):
        db = storage.open_database(self.path)
        self.addCleanup(db.close)
        return db

    def seed(self, db):
        with storage.transaction(db):
            db.execute("INSERT INTO imports (id, source_hash, source_name) VALUES (1, 'hash', 'history')")
            db.execute("INSERT INTO videos (id, title) VALUES ('video000001', 'Nhạc 音楽')")

    def test_initial_migration_creates_all_entities_and_reopens_without_data_loss(self):
        db = self.open()
        self.seed(db)
        reopened = self.open()
        tables = {row[0] for row in reopened.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({'imports', 'watch_events', 'videos', 'channel_decisions', 'download_batches', 'download_items', 'settings'} <= tables)
        self.assertEqual(reopened.execute("PRAGMA user_version").fetchone()[0], 4)
        self.assertEqual(reopened.execute("SELECT title FROM videos").fetchone()[0], 'Nhạc 音楽')

    def test_transaction_rolls_back_all_changes_on_constraint_failure(self):
        db = self.open()
        with self.assertRaises(sqlite3.IntegrityError):
            with storage.transaction(db):
                db.execute("INSERT INTO videos (id) VALUES ('video000001')")
                db.execute("INSERT INTO videos (id) VALUES ('video000001')")
        self.assertEqual(db.execute("SELECT COUNT(*) FROM videos").fetchone()[0], 0)

    def test_repeated_watch_events_are_distinct_but_source_rows_are_unique(self):
        db = self.open()
        self.seed(db)
        for row in (0, 1):
            db.execute("INSERT INTO watch_events (import_id, source_row, video_id) VALUES (1, ?, 'video000001')", (row,))
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute("INSERT INTO watch_events (import_id, source_row, video_id) VALUES (1, 0, 'video000001')")
        self.assertEqual(db.execute("SELECT COUNT(*) FROM watch_events").fetchone()[0], 2)

    def test_foreign_keys_and_domain_constraints_are_enforced(self):
        db = self.open()
        self.seed(db)
        statements = [
            "INSERT INTO watch_events (import_id, source_row, video_id) VALUES (99, 0, 'video000001')",
            "INSERT INTO watch_events (import_id, source_row, video_id) VALUES (1, 0, 'missing')",
            "UPDATE videos SET user_group='unknown'",
            "INSERT INTO imports (source_hash, source_name) VALUES ('hash', 'duplicate')",
            "INSERT INTO download_batches (output_dir, status) VALUES ('/tmp/audio', 'invalid')",
        ]
        for statement in statements:
            with self.subTest(statement=statement), self.assertRaises(sqlite3.IntegrityError):
                db.execute(statement)

    def test_review_settings_and_completed_download_survive_reopen(self):
        db = self.open()
        self.seed(db)
        with storage.transaction(db):
            storage.set_video_group(db, 'video000001', 'music')
            storage.set_setting(db, 'active_import', '1')
            db.execute("INSERT INTO channel_decisions (channel_key, group_name, reason) VALUES ('channel001', 'rest', 'manual')")
            db.execute("INSERT INTO download_batches (id, output_dir) VALUES (1, '/tmp/audio')")
            db.execute("INSERT INTO download_items (batch_id, video_id, status, file_path, file_size) VALUES (1, 'video000001', 'completed', '/tmp/audio/source.webm', 42)")
        reopened = self.open()
        self.assertEqual(storage.get_video(reopened, 'video000001')['effective_group'], 'music')
        self.assertEqual(storage.get_setting(reopened, 'active_import'), '1')
        self.assertEqual(reopened.execute("SELECT file_size FROM download_items").fetchone()[0], 42)
        self.assertEqual(reopened.execute("SELECT reason FROM channel_decisions").fetchone()[0], 'manual')
        with self.assertRaises(sqlite3.IntegrityError):
            reopened.execute("INSERT INTO download_items (batch_id, video_id) VALUES (1, 'video000001')")

    def test_manual_group_wins_over_auto_group_and_can_be_reset(self):
        db = self.open()
        self.seed(db)
        storage.set_video_group(db, 'video000001', 'music')
        db.execute("UPDATE videos SET auto_group='rest', auto_reason='rerun'")
        self.assertEqual(storage.get_video(db, 'video000001')['effective_group'], 'music')
        storage.set_video_group(db, 'video000001', None)
        self.assertEqual(storage.get_video(db, 'video000001')['effective_group'], 'rest')
        with self.assertRaises(KeyError):
            storage.set_video_group(db, 'missing', 'music')

    def test_settings_upsert_and_missing_lookup(self):
        db = self.open()
        self.assertIsNone(storage.get_setting(db, 'output_dir'))
        self.assertIsNone(storage.get_video(db, 'missing'))
        storage.set_setting(db, 'output_dir', '/tmp/one')
        storage.set_setting(db, 'output_dir', '/tmp/two')
        self.assertEqual(storage.get_setting(self.open(), 'output_dir'), '/tmp/two')

    def test_future_schema_is_rejected_without_modification(self):
        self.path.parent.mkdir()
        with sqlite3.connect(self.path) as db:
            db.execute("PRAGMA user_version=99")
            db.execute("CREATE TABLE sentinel (value TEXT)")
        with self.assertRaisesRegex(ValueError, '99'):
            storage.open_database(self.path)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 99)
            self.assertEqual(db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(), [('sentinel',)])

    def test_nested_transaction_failure_does_not_commit_outer_work(self):
        db = self.open()
        with self.assertRaises(RuntimeError):
            with storage.transaction(db):
                db.execute("INSERT INTO videos (id) VALUES ('video000001')")
                with storage.transaction(db):
                    pass
        self.assertEqual(db.execute("SELECT COUNT(*) FROM videos").fetchone()[0], 0)

    def test_failed_initial_migration_preserves_existing_database(self):
        self.path.parent.mkdir()
        db = sqlite3.connect(self.path)
        try:
            db.execute("CREATE TABLE videos (legacy_value TEXT)")
            db.execute("INSERT INTO videos VALUES ('preserve')")
            db.commit()
        finally:
            db.close()

        with self.assertRaises(sqlite3.OperationalError):
            storage.open_database(self.path)
        db = sqlite3.connect(self.path)
        try:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(), [('videos',)])
            self.assertEqual(db.execute("SELECT legacy_value FROM videos").fetchone()[0], 'preserve')
        finally:
            db.close()

    def test_v1_migration_preserves_review_downloads_and_adds_audit_tables(self):
        self.path.parent.mkdir()
        with sqlite3.connect(self.path) as legacy:
            legacy.executescript(storage._SCHEMA_V1)
            legacy.execute("PRAGMA user_version=1")
            legacy.execute("INSERT INTO videos(id,user_group) VALUES('abcdefghijk','music')")
            legacy.execute("INSERT INTO download_batches(id,output_dir,status) VALUES(1,'/audio','completed')")
            legacy.execute("INSERT INTO download_items(batch_id,video_id,status,file_path) VALUES(1,'abcdefghijk','completed','/audio/source.webm')")
        db = self.open()
        self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 4)
        self.assertEqual(storage.get_video(db, 'abcdefghijk')['effective_group'], 'music')
        self.assertEqual(db.execute('SELECT file_path FROM download_items').fetchone()[0], '/audio/source.webm')
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({'audit_runs','audit_events','metadata_items','metadata_cache',
                         'classification_previews','song_aliases','dedup_runs','dedup_groups',
                         'dedup_members','download_selections','rejected_groups'} <= tables)

    def test_database_copy_preserves_manual_download_selection_and_rejects_old_code(self):
        db = self.open()
        self.seed(db)
        with storage.transaction(db):
            storage.set_video_group(db, 'video000001', 'music')
            db.execute("INSERT INTO download_batches(id,output_dir,status) VALUES(1,'/audio','completed')")
            db.execute("INSERT INTO download_items(batch_id,video_id,status,file_path,file_size) "
                       "VALUES(1,'video000001','completed','/audio/source.webm',42)")
            db.execute("INSERT INTO download_selections(video_id,keep,revision) VALUES('video000001',0,7)")
            storage.set_setting(db, 'dedup_selection_revision', '7')

        copy_path = self.path.with_name('migration-copy.sqlite3')
        with sqlite3.connect(copy_path) as destination:
            db.backup(destination)

        with storage.open_database(copy_path) as reopened:
            self.assertEqual(reopened.execute('PRAGMA user_version').fetchone()[0], 4)
            self.assertEqual(storage.get_video(reopened, 'video000001')['user_group'], 'music')
            self.assertEqual(tuple(reopened.execute(
                'SELECT status,file_path,file_size FROM download_items').fetchone()),
                ('completed', '/audio/source.webm', 42))
            self.assertEqual(tuple(reopened.execute(
                'SELECT keep,revision FROM download_selections').fetchone()), (0, 7))

        # Simulate a rollback to an application binary whose latest known schema is v3.
        # It must refuse the newer copy before it can write any review/download state.
        with patch.object(storage, 'SCHEMA_VERSION', 3), self.assertRaisesRegex(ValueError, 'newer'):
            storage.open_database(copy_path)
        with sqlite3.connect(copy_path) as untouched:
            self.assertEqual(untouched.execute('PRAGMA user_version').fetchone()[0], 4)
            self.assertEqual(untouched.execute(
                'SELECT user_group FROM videos WHERE id=\'video000001\'').fetchone()[0], 'music')
            self.assertEqual(untouched.execute(
                'SELECT keep,revision FROM download_selections').fetchone(), (0, 7))

    def test_failed_v2_migration_rolls_back_new_tables_and_version(self):
        self.path.parent.mkdir()
        with sqlite3.connect(self.path) as legacy:
            legacy.executescript(storage._SCHEMA_V1)
            legacy.execute('PRAGMA user_version=1')
            legacy.execute('CREATE TABLE audit_events(legacy TEXT)')
            legacy.execute("INSERT INTO videos(id,user_group) VALUES('abcdefghijk','music')")
        with self.assertRaises(sqlite3.OperationalError):
            storage.open_database(self.path)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 1)
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='audit_runs'").fetchone())
            self.assertEqual(db.execute('SELECT user_group FROM videos').fetchone()[0], 'music')

    def test_review_update_rolls_back_when_audit_write_fails(self):
        db = self.open()
        self.seed(db)
        db.execute("CREATE TRIGGER fail_audit BEFORE INSERT ON audit_events BEGIN SELECT RAISE(ABORT,'fixture disk failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            storage.set_video_group(db, 'video000001', 'music')
        self.assertIsNone(storage.get_video(db, 'video000001')['user_group'])
