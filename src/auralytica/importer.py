"""Import local Google Takeout history."""

import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3
from typing import Any
from urllib.parse import parse_qs, urlparse

from .storage import get_setting, set_setting, transaction, assert_review_unlocked
from .classification import classify_import


VIDEO_ID = re.compile(r'[A-Za-z0-9_-]{11}')


def video_id_from_url(value):
    if not isinstance(value, str):
        return None
    try:
        url = urlparse(value)
        if url.scheme not in {'https', 'http'}:
            return None
        parts = url.path.strip('/').split('/')
        candidate = None
        if url.hostname in {'youtu.be', 'www.youtu.be'} and len(parts) == 1:
            candidate = parts[0]
        elif url.hostname in {'youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com'}:
            if url.path.rstrip('/') == '/watch':
                candidate = parse_qs(url.query).get('v', [None])[0]
            elif len(parts) == 2 and parts[0] in {'shorts', 'live', 'embed'}:
                candidate = parts[1]
        return candidate if candidate and VIDEO_ID.fullmatch(candidate) else None
    except ValueError:
        return None


def _objects(value):
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def import_folder(db: sqlite3.Connection, folder: str | Path, *, history: str | None = None) -> dict:
    root = Path(folder).expanduser().resolve()
    if not root.is_dir():
        raise ValueError('Folder Takeout không tồn tại hoặc không phải thư mục.')
    if history:
        source = (root / history).resolve()
        if not source.is_relative_to(root) or source.name != 'watch-history.json' or not source.is_file():
            raise ValueError('--history phải trỏ đến watch-history.json bên trong folder Takeout.')
    else:
        sources = sorted(p for p in root.rglob('watch-history.json') if p.is_file() and p.resolve().is_relative_to(root))
        if len(sources) > 1:
            names = ', '.join(str(p.relative_to(root)) for p in sources)
            raise ValueError(f'Có nhiều nguồn; chọn --history <đường dẫn tương đối>: {names}')
        if not sources:
            suffix = ' HTML chưa hỗ trợ; hãy export JSON.' if any(root.rglob('watch-history.html')) else ''
            raise ValueError('Không tìm thấy watch-history.json.' + suffix)
        source = sources[0]
    raw = source.read_bytes()
    try:
        rows = json.loads(raw.decode('utf-8-sig'))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('watch-history.json không phải JSON UTF-8 hợp lệ.') from exc
    if not isinstance(rows, list) or (rows and not any(isinstance(r, dict) for r in rows)):
        raise ValueError('Lịch sử phải là danh sách bản ghi JSON.')

    # Scope library discovery to the selected export, not neighbouring exports.
    export_root = source.parent.parent if source.parent.name == 'history' else source.parent
    libraries = sorted(export_root.rglob('music library songs.csv'))
    if len(libraries) > 1:
        raise ValueError('Có nhiều music library songs.csv; chọn folder của một export.')
    library_ids = set()
    if libraries:
        if not libraries[0].resolve().is_relative_to(root):
            raise ValueError('Music library nằm ngoài folder đã chọn.')
        with libraries[0].open(encoding='utf-8-sig', newline='') as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or 'Video ID' not in reader.fieldnames:
                raise ValueError('music library songs.csv thiếu cột Video ID.')
            library_ids = {value for row in reader if VIDEO_ID.fullmatch(value := (row.get('Video ID') or '').strip())}

    stats = dict(source_rows=len(rows), video_events=0, unique_videos=0, ads=0,
                 invalid_rows=0, non_video_rows=0, invalid_times=0, missing_titles=0,
                 missing_channels=0, library_matches=0)
    events, videos = [], {}
    shorts_ids = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            stats['invalid_rows'] += 1
            continue
        if any(str(d.get('name', '')).strip().casefold() == 'from google ads' for d in _objects(row.get('details'))):
            stats['ads'] += 1
            continue
        video_id = video_id_from_url(row.get('titleUrl'))
        watched_at = None
        try:
            timestamp = datetime.fromisoformat(row.get('time', '').replace('Z', '+00:00'))
            if timestamp.tzinfo is None:
                raise ValueError('Missing timezone')
            watched_at = timestamp.astimezone(timezone.utc).isoformat()
        except (ValueError, TypeError, AttributeError):
            if video_id:
                stats['invalid_times'] += 1
        events.append((index, video_id, watched_at))
        if not video_id:
            stats['non_video_rows'] += 1
            continue
        stats['video_events'] += 1
        if urlparse(row['titleUrl']).path.startswith('/shorts/'):
            shorts_ids.add(video_id)
        title = row.get('title') if isinstance(row.get('title'), str) else ''
        title = re.sub(r'^(?:Watched|Đã xem)\s+', '', title).strip()
        channels = _objects(row.get('subtitles'))
        channel = channels[0] if channels else {}
        name = channel.get('name') if isinstance(channel.get('name'), str) else None
        key = channel.get('url') if isinstance(channel.get('url'), str) else None
        stats['missing_titles'] += int(not title)
        stats['missing_channels'] += int(not name)
        # Takeout is normally newest-first. Prefer the first nonempty metadata.
        previous = videos.get(video_id, ('', None, None))
        videos[video_id] = (previous[0] or title, previous[1] or key, previous[2] or name)
    stats['unique_videos'] = len(videos)
    stats['library_matches'] = len(videos.keys() & library_ids)
    digest = sha256(raw).hexdigest()
    with transaction(db):
        assert_review_unlocked(db)
        existing = db.execute('SELECT id FROM imports WHERE source_hash=?', (digest,)).fetchone()
        if existing:
            import_id = existing[0]
        else:
            import_id = db.execute('INSERT INTO imports (source_hash, source_name) VALUES (?, ?)',
                                   (digest, str(source.relative_to(root)))).lastrowid
        for video_id, (title, key, name) in videos.items():
            db.execute("INSERT INTO videos (id, title, channel_key, channel_name) VALUES (?, ?, ?, ?) "
                       "ON CONFLICT(id) DO UPDATE SET title=CASE WHEN excluded.title='' THEN videos.title ELSE excluded.title END, "
                       "channel_key=COALESCE(excluded.channel_key,videos.channel_key), "
                       "channel_name=COALESCE(excluded.channel_name,videos.channel_name)", (video_id, title, key, name))
            metadata = json.loads(db.execute('SELECT metadata_json FROM videos WHERE id=?', (video_id,)).fetchone()[0])
            metadata['music_library'] = video_id in library_ids
            metadata['takeout_shorts_url'] = video_id in shorts_ids
            db.execute('UPDATE videos SET metadata_json=? WHERE id=?', (json.dumps(metadata), video_id))
        if not existing:
            db.executemany('INSERT INTO watch_events (import_id, source_row, video_id, watched_at) VALUES (?, ?, ?, ?)',
                           ((import_id, *e) for e in events))
        db.execute('UPDATE imports SET statistics_json=? WHERE id=?', (json.dumps(stats), import_id))
        set_setting(db, 'active_import', str(import_id))
        classification = classify_import(db, import_id)
    return dict(import_id=import_id, reused=bool(existing), statistics=stats, classification=classification)


def get_import_sessions(db: sqlite3.Connection) -> dict[str, Any]:
    """Retrieve all import sessions with their counts, statistics, and active status."""
    active_str = get_setting(db, 'active_import')
    active_id = int(active_str) if active_str else None

    # Check if download batches are currently locked
    batches = db.execute("SELECT status FROM download_batches").fetchall()
    batch_locked = any(row['status'] in ('queued', 'running') for row in batches)

    rows = db.execute(
        "SELECT id, source_hash, source_name, created_at, statistics_json "
        "FROM imports ORDER BY id DESC"
    ).fetchall()

    items = []
    for r in rows:
        try:
            stats = json.loads(r['statistics_json'])
        except Exception:
            stats = {}

        counts_row = db.execute(
            "SELECT "
            "SUM(CASE WHEN COALESCE(v.user_group, v.auto_group) = 'music' THEN 1 ELSE 0 END) AS music_count, "
            "SUM(CASE WHEN COALESCE(v.user_group, v.auto_group) = 'rest' THEN 1 ELSE 0 END) AS rest_count "
            "FROM videos v WHERE v.id IN (SELECT video_id FROM watch_events WHERE import_id = ?)",
            (r['id'],),
        ).fetchone()

        music_c = counts_row['music_count'] or 0
        rest_c = counts_row['rest_count'] or 0

        items.append({
            'id': r['id'],
            'source_name': r['source_name'],
            'source_path': r['source_name'],
            'source_hash': r['source_hash'],
            'created_at': r['created_at'],
            'imported_at': r['created_at'],
            'is_active': (r['id'] == active_id),
            'statistics': stats,
            'counts': {
                'music': music_c,
                'rest': rest_c,
                'total': music_c + rest_c,
            },
        })

    return {
        'items': items,
        'sessions': items,
        'active_import': active_id,
        'batch_locked': batch_locked,
    }


def activate_import_session(db: sqlite3.Connection, import_id: int) -> dict[str, Any]:
    """Switch the current active import session safely."""
    with transaction(db):
        assert_review_unlocked(db)
        row = db.execute("SELECT id FROM imports WHERE id = ?", (import_id,)).fetchone()
        if not row:
            raise ValueError(f"Không tìm thấy phiên import #{import_id}.")
        set_setting(db, 'active_import', str(import_id))
    return {'status': 'activated', 'active_import': import_id}


def delete_import_session(db: sqlite3.Connection, import_id: int) -> dict[str, Any]:
    """Delete an inactive import session and its associated watch events."""
    with transaction(db):
        assert_review_unlocked(db)
        active_str = get_setting(db, 'active_import')
        if active_str and int(active_str) == import_id:
            raise ValueError("Không thể xóa phiên đang hoạt động. Vui lòng kích hoạt phiên khác trước khi xóa.")

        row = db.execute("SELECT id FROM imports WHERE id = ?", (import_id,)).fetchone()
        if not row:
            raise ValueError(f"Không tìm thấy phiên import #{import_id}.")

        # 1. Classification previews
        try:
            db.execute("DELETE FROM classification_previews WHERE import_id = ?", (import_id,))
        except sqlite3.OperationalError:
            pass

        # 2. Dedup runs and children
        try:
            db.execute(
                "DELETE FROM dedup_members WHERE group_id IN ("
                "SELECT id FROM dedup_groups WHERE run_id IN (SELECT id FROM dedup_runs WHERE import_id = ?))",
                (import_id,),
            )
            db.execute(
                "DELETE FROM dedup_groups WHERE run_id IN (SELECT id FROM dedup_runs WHERE import_id = ?)",
                (import_id,),
            )
            db.execute("DELETE FROM dedup_runs WHERE import_id = ?", (import_id,))
        except sqlite3.OperationalError:
            pass

        # 3. Audit runs and metadata
        try:
            db.execute(
                "DELETE FROM metadata_cache WHERE observation_id IN ("
                "SELECT id FROM audit_events WHERE run_id IN (SELECT id FROM audit_runs WHERE import_id = ?))",
                (import_id,),
            )
            db.execute(
                "DELETE FROM metadata_items WHERE run_id IN (SELECT id FROM audit_runs WHERE import_id = ?)",
                (import_id,),
            )
            db.execute(
                "DELETE FROM audit_events WHERE run_id IN (SELECT id FROM audit_runs WHERE import_id = ?)",
                (import_id,),
            )
            db.execute("DELETE FROM audit_runs WHERE import_id = ?", (import_id,))
        except sqlite3.OperationalError:
            pass

        # 4. Delete associated watch events
        db.execute("DELETE FROM watch_events WHERE import_id = ?", (import_id,))
        # 5. Delete import record
        db.execute("DELETE FROM imports WHERE id = ?", (import_id,))

    return {'status': 'deleted', 'deleted_id': import_id}

