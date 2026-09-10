"""Import local Google Takeout history."""

import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import parse_qs, urlparse

from .storage import set_setting, transaction, assert_review_unlocked
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
