"""Shared local storage for web services and background workers."""

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from collections.abc import Iterator


SCHEMA_VERSION = 4


class BatchBusyError(ValueError):
    """A queued/running batch owns the current review state."""


class RevisionConflict(ValueError):
    """A persisted snapshot no longer matches the current library."""


def assert_review_unlocked(db):
    """Call inside the same write transaction as the review mutation."""
    if db.execute("SELECT 1 FROM download_batches WHERE status IN ('queued','running') LIMIT 1").fetchone():
        raise BatchBusyError('Có batch đang chờ/chạy; dừng batch trước khi thay đổi thư viện.')

# Version 1 is the initial application schema, not a notebook database upgrade.
_SCHEMA_V1 = """
CREATE TABLE imports (
    id INTEGER PRIMARY KEY,
    source_hash TEXT NOT NULL UNIQUE,
    source_name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    statistics_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE videos (
    id TEXT PRIMARY KEY NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    channel_key TEXT,
    channel_name TEXT,
    thumbnail_url TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    availability TEXT,
    auto_group TEXT NOT NULL DEFAULT 'rest' CHECK (auto_group IN ('music', 'rest')),
    auto_reason TEXT NOT NULL DEFAULT 'unknown',
    evidence_json TEXT NOT NULL DEFAULT '[]',
    user_group TEXT CHECK (user_group IN ('music', 'rest')),
    user_decided_at TEXT
);
CREATE TABLE watch_events (
    import_id INTEGER NOT NULL REFERENCES imports(id),
    source_row INTEGER NOT NULL CHECK (source_row >= 0),
    video_id TEXT REFERENCES videos(id),
    watched_at TEXT,
    PRIMARY KEY (import_id, source_row)
);
CREATE INDEX watch_events_video ON watch_events(video_id);
CREATE TABLE channel_decisions (
    channel_key TEXT PRIMARY KEY NOT NULL,
    group_name TEXT NOT NULL CHECK (group_name IN ('music', 'rest')),
    reason TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'user',
    decided_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE download_batches (
    id INTEGER PRIMARY KEY,
    output_dir TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'paused', 'completed', 'partial', 'failed', 'cancelled')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TEXT
);
CREATE TABLE download_items (
    batch_id INTEGER NOT NULL REFERENCES download_batches(id),
    video_id TEXT NOT NULL REFERENCES videos(id),
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'completed', 'skipped', 'failed', 'cancelled')),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    downloaded_bytes INTEGER NOT NULL DEFAULT 0 CHECK (downloaded_bytes >= 0),
    total_bytes INTEGER CHECK (total_bytes >= 0),
    file_path TEXT,
    file_size INTEGER CHECK (file_size >= 0),
    error_code TEXT,
    error_message TEXT,
    PRIMARY KEY (batch_id, video_id)
);
CREATE TABLE settings (
    key TEXT PRIMARY KEY NOT NULL,
    value TEXT NOT NULL
);
"""

_SCHEMA_V2 = """
CREATE TABLE audit_runs (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    import_id INTEGER NOT NULL REFERENCES imports(id),
    source_hash TEXT NOT NULL,
    version TEXT NOT NULL,
    config_json TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TEXT
);
CREATE TABLE audit_events (
    id INTEGER PRIMARY KEY,
    run_id TEXT REFERENCES audit_runs(id),
    video_id TEXT REFERENCES videos(id),
    kind TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX audit_events_run ON audit_events(run_id, id);
CREATE INDEX audit_events_video ON audit_events(video_id, id);
CREATE TABLE metadata_items (
    run_id TEXT NOT NULL REFERENCES audit_runs(id),
    video_id TEXT NOT NULL REFERENCES videos(id),
    position INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','done','failed')),
    observation_id INTEGER REFERENCES audit_events(id),
    PRIMARY KEY(run_id, video_id)
);
CREATE TABLE metadata_cache (
    provider_key TEXT NOT NULL,
    video_id TEXT NOT NULL REFERENCES videos(id),
    observation_id INTEGER NOT NULL REFERENCES audit_events(id),
    fetched_at REAL NOT NULL,
    PRIMARY KEY(provider_key, video_id)
);
"""

_SCHEMA_V3 = """
CREATE TABLE classification_previews (
    id TEXT PRIMARY KEY,
    import_id INTEGER NOT NULL REFERENCES imports(id),
    state_hash TEXT NOT NULL,
    plan_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ready' CHECK(status IN ('ready','applied','stale')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    applied_at TEXT
);
CREATE INDEX classification_previews_import ON classification_previews(import_id, created_at);
"""

_SCHEMA_V4 = """
CREATE TABLE song_aliases (
    id INTEGER PRIMARY KEY,
    song_key TEXT NOT NULL,
    alias TEXT NOT NULL,
    normalized_alias TEXT NOT NULL,
    artist_scope TEXT,
    source TEXT NOT NULL,
    confirmed INTEGER NOT NULL DEFAULT 1 CHECK(confirmed IN (0,1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX song_aliases_lookup ON song_aliases(normalized_alias, confirmed);
CREATE TABLE dedup_runs (
    id TEXT PRIMARY KEY,
    import_id INTEGER NOT NULL REFERENCES imports(id),
    input_hash TEXT NOT NULL,
    algorithm_version TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'completed',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE dedup_groups (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES dedup_runs(id),
    fingerprint TEXT NOT NULL,
    title_key TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    artist_conflict INTEGER NOT NULL DEFAULT 0 CHECK(artist_conflict IN (0,1))
);
CREATE INDEX dedup_groups_run ON dedup_groups(run_id, id);
CREATE TABLE dedup_members (
    group_id TEXT NOT NULL REFERENCES dedup_groups(id),
    video_id TEXT NOT NULL REFERENCES videos(id),
    evidence_json TEXT NOT NULL,
    version_marker TEXT,
    PRIMARY KEY(group_id, video_id)
);
CREATE TABLE download_selections (
    video_id TEXT PRIMARY KEY REFERENCES videos(id),
    keep INTEGER NOT NULL CHECK(keep IN (0,1)),
    revision INTEGER NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE rejected_groups (
    fingerprint TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


@contextmanager
def transaction(db: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Commit a unit of work, or roll it back; nesting is explicitly unsupported."""
    if db.in_transaction:
        raise RuntimeError("Nested storage transactions are not supported")
    db.execute("BEGIN IMMEDIATE")
    try:
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise


def open_database(path: str | Path) -> sqlite3.Connection:
    """Open and migrate a local DB. Caller closes it; use one per thread/request.

    Individual statements autocommit. Use transaction() for multi-step mutations.
    Taking the write lock before reading user_version serializes first-time setup.
    """
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10, isolation_level=None)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA foreign_keys=ON")
        with transaction(db):
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise ValueError(f"Database schema {version} is newer than supported {SCHEMA_VERSION}")
            if version == 0:
                # execute() preserves the surrounding transaction; executescript()
                # would commit it before applying the DDL.
                for statement in _SCHEMA_V1.split(';'):
                    if statement.strip():
                        db.execute(statement)
                db.execute("PRAGMA user_version=1")
            if version < 2:
                for statement in _SCHEMA_V2.split(';'):
                    if statement.strip():
                        db.execute(statement)
                db.execute("PRAGMA user_version=2")
            if version < 3:
                for statement in _SCHEMA_V3.split(';'):
                    if statement.strip():
                        db.execute(statement)
                db.execute("PRAGMA user_version=3")
            if version < 4:
                for statement in _SCHEMA_V4.split(';'):
                    if statement.strip():
                        db.execute(statement)
                db.execute("PRAGMA user_version=4")
        return db
    except BaseException:
        db.close()
        raise


def get_video(db: sqlite3.Connection, video_id: str) -> sqlite3.Row | None:
    return db.execute(
        "SELECT *, COALESCE(user_group, auto_group) AS effective_group FROM videos WHERE id=?",
        (video_id,),
    ).fetchone()


def set_video_group(db: sqlite3.Connection, video_id: str, group: str | None) -> None:
    """Store a manual override, or reset it to automatic classification with None."""
    if not db.in_transaction:
        with transaction(db):
            set_video_group(db, video_id, group)
        return
    from .audit import record_event
    before = get_video(db, video_id)
    if before is None:
        raise KeyError(video_id)
    cursor = db.execute(
        "UPDATE videos SET user_group=?, "
        "user_decided_at=CASE WHEN ? IS NULL THEN NULL ELSE CURRENT_TIMESTAMP END WHERE id=?",
        (group, group, video_id),
    )
    if cursor.rowcount == 0:
        raise KeyError(video_id)
    decision = db.execute("SELECT id,run_id FROM audit_events WHERE video_id=? "
                          "AND kind='classification_decided' ORDER BY id DESC LIMIT 1", (video_id,)).fetchone()
    record_event(db, 'review_changed', dict(
        decision_id=decision['id'] if decision else None, source='user',
        before_group=before['effective_group'], after_group=group or before['auto_group'],
        before_user_group=before['user_group'], after_user_group=group,
    ), run_id=decision['run_id'] if decision else None, video_id=video_id)


def get_setting(db: sqlite3.Connection, key: str) -> str | None:
    row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row[0] if row else None


def set_setting(db: sqlite3.Connection, key: str, value: str) -> None:
    db.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
