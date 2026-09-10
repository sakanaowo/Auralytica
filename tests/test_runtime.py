"""Verify the interpreter can persist and roll back SQLite transactions."""

from pathlib import Path
import sqlite3
import tempfile
import unittest


class RuntimeTests(unittest.TestCase):
    def test_sqlite_commit_persists_and_rollback_discards_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "probe.sqlite3"
            connection = sqlite3.connect(path)
            try:
                connection.execute("CREATE TABLE probe (value TEXT)")
                connection.execute("INSERT INTO probe VALUES (?)", ("Nhạc 音楽",))
                connection.commit()
                connection.execute("INSERT INTO probe VALUES (?)", ("discard",))
                connection.rollback()
            finally:
                connection.close()
            reopened = sqlite3.connect(path)
            try:
                self.assertEqual(
                    reopened.execute("SELECT value FROM probe").fetchall(),
                    [("Nhạc 音楽",)],
                )
            finally:
                reopened.close()
