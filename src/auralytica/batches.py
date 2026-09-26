"""Persistent download snapshots and exclusive local worker ownership."""

from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from .converter import clean_title, parse_artist_title
from .storage import BatchBusyError, RevisionConflict, get_setting, set_setting, transaction


def get_batch(db, batch_id):
    row = db.execute('SELECT * FROM download_batches WHERE id=?', (batch_id,)).fetchone()
    if row is None:
        raise ValueError('Không tìm thấy batch.')
    counts = dict(db.execute('SELECT status,COUNT(*) FROM download_items WHERE batch_id=? GROUP BY status', (batch_id,)))
    fmt = get_setting(db, f'batch_format:{batch_id}') or 'raw'
    clean = get_setting(db, f'batch_clean_names:{batch_id}') == '1'
    embed = get_setting(db, f'batch_embed_metadata:{batch_id}') != '0'
    concurrency_val = get_setting(db, f'batch_concurrency:{batch_id}')
    concurrency = int(concurrency_val) if concurrency_val and concurrency_val.isdigit() else 3
    return dict(batch_id=row['id'], output_dir=row['output_dir'], status=row['status'],
                format=fmt, clean_names=clean, embed_metadata=embed, concurrency=concurrency,
                total=sum(counts.values()), queued=counts.get('queued', 0),
                skipped=counts.get('skipped', 0), counts=counts)


def _active(db):
    return db.execute("SELECT id FROM download_batches WHERE status IN ('queued','running') ORDER BY id LIMIT 1").fetchone()


AUDIO_EXTENSIONS = {'.m4a', '.mp3', '.opus', '.webm', '.flac', '.wav', '.ogg', '.aac'}


def _valid_file(file_path, file_size, output, target_ext=None):
    if not file_path or file_size is None or file_size <= 0:
        return False
    try:
        path = Path(file_path).resolve()
        output_res = Path(output).resolve()
        if not path.is_relative_to(output_res) or not path.is_file() or path.stat().st_size != file_size:
            return False
        if target_ext is not None and path.suffix.lower() != target_ext.lower():
            return False
        return True
    except (OSError, ValueError):
        return False


def _scan_disk_for_candidates(output: Path, video_rows):
    """Scan output directory and its subdirectories (e.g. Apple Music) to index existing audio files."""
    if not output.is_dir():
        return {}

    disk_by_vid = {}
    disk_by_norm = {}

    try:
        for root, dirs, files in os.walk(output):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in AUDIO_EXTENSIONS:
                    full_path = Path(root) / f
                    try:
                        st = full_path.stat()
                        if st.st_size <= 0:
                            continue
                    except OSError:
                        continue

                    stem = full_path.stem
                    info = {'file_path': str(full_path.resolve()), 'file_size': st.st_size}
                    m = re.search(r'\[([A-Za-z0-9_-]{11})\]', stem)
                    if m:
                        disk_by_vid[m.group(1)] = info
                    else:
                        norm = re.sub(r'[\W_]+', '', stem).lower()
                        if norm:
                            disk_by_norm[norm] = info
    except OSError:
        return {}

    result = {}
    for r in video_rows:
        vid = r['id']
        if vid in disk_by_vid:
            result[vid] = disk_by_vid[vid]
            continue

        title = r['title'] if 'title' in r.keys() else ''
        title = title or ''
        channel = r['channel_name'] if 'channel_name' in r.keys() else ''
        channel = channel or ''
        clean_stem = clean_title(title, strip_video_id=True, clean_youtube_tags=True)
        raw_artist = re.sub(r'\s*-\s*Topic\s*$', '', channel, flags=re.IGNORECASE).strip()
        artist, parsed_title = parse_artist_title(clean_stem, raw_artist)

        candidates = [
            title,
            clean_stem,
            f'{artist} - {parsed_title}' if artist and parsed_title else '',
            re.sub(r'[/\\:*?\"<>|]', '', clean_stem).strip(' .')[:120],
        ]

        found = None
        for c in candidates:
            if not c:
                continue
            norm = re.sub(r'[\W_]+', '', c).lower()
            if norm and norm in disk_by_norm:
                found = disk_by_norm[norm]
                break

        if not found:
            for c in candidates:
                if not c:
                    continue
                nc = re.sub(r'[\W_]+', '', c).lower()
                if len(nc) >= 8:
                    for nd, info in disk_by_norm.items():
                        if len(nd) >= 8 and (nc in nd or nd in nc):
                            found = info
                            break
                    if found:
                        break

        if found:
            result[vid] = found
            for k, v in list(disk_by_norm.items()):
                if v['file_path'] == found['file_path']:
                    del disk_by_norm[k]

    return result


def _completed_file(db, video_id, output, target_ext=None, disk_match=None):
    rows = db.execute("SELECT d.file_path,d.file_size FROM download_items d JOIN download_batches b ON b.id=d.batch_id "
                      "WHERE d.video_id=? AND d.status IN ('completed','skipped') AND b.output_dir=? ORDER BY d.batch_id DESC",
                      (video_id, str(output)))
    for row in rows:
        if _valid_file(row['file_path'], row['file_size'], output, target_ext):
            return dict(row)
    if disk_match and _valid_file(disk_match['file_path'], disk_match['file_size'], output, target_ext):
        return disk_match
    return None


def eligible_snapshot(db, output_dir):
    """Build the download candidate set and a token from persisted state and files."""
    if not str(output_dir).strip():
        raise ValueError('Cần thư mục tải.')
    active_import = get_setting(db, 'active_import')
    if active_import is None:
        raise ValueError('Hãy import Takeout trước.')
    output = Path(output_dir).expanduser().resolve()
    rows = db.execute(
        "SELECT DISTINCT v.id,v.title,v.channel_name,COALESCE(s.keep,1) AS keep FROM videos v "
        "JOIN watch_events e ON e.video_id=v.id "
        "LEFT JOIN download_selections s ON s.video_id=v.id "
        "WHERE e.import_id=? AND COALESCE(v.user_group,v.auto_group)='music' ORDER BY v.id",
        (active_import,),
    ).fetchall()
    ids = [row['id'] for row in rows if row['keep']]
    kept_rows = [row for row in rows if row['keep']]
    disk_matches = _scan_disk_for_candidates(output, kept_rows)
    file_states = []
    completed = {}
    for video_id in ids:
        previous = _completed_file(db, video_id, output, disk_match=disk_matches.get(video_id))
        completed[video_id] = previous
        if previous is None:
            file_states.append((video_id, None))
            continue
        path = Path(previous['file_path'])
        try:
            stat = path.stat()
        except OSError:
            completed[video_id] = None
            file_states.append((video_id, None))
            continue
        file_states.append((video_id, str(path.resolve()), stat.st_size, stat.st_mtime_ns))
    token_input = {
        'active_import': int(active_import),
        'output_dir': str(output),
        'selection_revision': int(get_setting(db, 'dedup_selection_revision') or 0),
        'music': [(row['id'], int(row['keep'])) for row in rows],
        'files': file_states,
    }
    token = hashlib.sha256(json.dumps(token_input, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    skipped = sum(value is not None for value in completed.values())
    return {
        'output_dir': str(output),
        'music': len(rows),
        'total': len(rows),
        'excluded': len(rows) - len(ids),
        'kept': len(ids),
        'skipped': skipped,
        'queued': len(ids) - skipped,
        'needed': len(ids) - skipped,
        'token': token,
        '_ids': ids,
        '_completed': completed,
    }


def create_batch(db, output_dir, *, expected_token=None, format_type='raw', clean_names=False, embed_metadata=False, concurrency=None):
    """Snapshot all kept music, independent of any UI filters or pagination."""
    with transaction(db):
        active = _active(db)
        if active:
            return dict(get_batch(db, active[0]), reused=True)
        snapshot = eligible_snapshot(db, output_dir)
        if expected_token is not None and expected_token != snapshot['token']:
            raise RevisionConflict('Danh sách hoặc file đã đổi; kiểm tra preview rồi tải lại.')
        ids = snapshot['_ids']
        completed = snapshot.get('_completed', {})
        if not ids:
            raise ValueError('Không còn bản nhạc nào được giữ để tải.')
        output = Path(snapshot['output_dir'])
        output.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=output):
            pass  # Check actual write permission rather than os.access().
        batch_id = db.execute('INSERT INTO download_batches(output_dir) VALUES (?)', (str(output),)).lastrowid
        set_setting(db, f'batch_format:{batch_id}', format_type)
        set_setting(db, f'batch_clean_names:{batch_id}', '1' if clean_names else '0')
        set_setting(db, f'batch_embed_metadata:{batch_id}', '1' if embed_metadata else '0')
        if concurrency is not None:
            set_setting(db, f'batch_concurrency:{batch_id}', str(max(1, min(int(concurrency), 8))))
        queued = 0
        for video_id in ids:
            # Recheck immediately before persisting: a valid preview file may have
            # disappeared while the output directory was being prepared.
            previous = completed.get(video_id) or _completed_file(db, video_id, output)
            queued += previous is None
            db.execute('INSERT INTO download_items(batch_id,video_id,status,file_path,file_size) VALUES (?,?,?,?,?)',
                       (batch_id, video_id, 'skipped' if previous else 'queued',
                        previous['file_path'] if previous else None, previous['file_size'] if previous else None))
        if not queued:
            db.execute("UPDATE download_batches SET status='completed',finished_at=CURRENT_TIMESTAMP WHERE id=?", (batch_id,))
        return dict(get_batch(db, batch_id), reused=False, music=snapshot['music'],
                    excluded=snapshot['excluded'], kept=snapshot['kept'])


@contextmanager
def _worker_lock(db):
    filename = next(row[2] for row in db.execute('PRAGMA database_list') if row[1] == 'main')
    if not filename:
        raise ValueError('Worker cần database trên đĩa.')
    # Never unlink this file: every process must lock the same inode.
    lock_path = Path(str(Path(filename).resolve()) + '.worker.lock')
    with lock_path.open('a+b') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise BatchBusyError('Worker khác đang giữ quyền tải.') from exc
        try:
            yield handle.fileno()
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def pause_batch(db, batch_id):
    with transaction(db):
        batch = get_batch(db, batch_id)
        if batch['status'] == 'running':
            raise BatchBusyError('Worker đang chạy; cần yêu cầu worker dừng trước.')
        if batch['status'] == 'queued':
            db.execute("UPDATE download_batches SET status='paused' WHERE id=?", (batch_id,))
        return get_batch(db, batch_id)


def resume_batch(db, batch_id):
    with _worker_lock(db), transaction(db):
        batch = get_batch(db, batch_id)
        active = _active(db)
        if active:
            if active[0] == batch_id and batch['status'] == 'queued':
                return batch
            raise BatchBusyError('Một batch khác đang chờ/chạy.')
        if batch['status'] not in {'paused', 'partial', 'failed', 'cancelled'}:
            raise ValueError('Batch không ở trạng thái có thể tiếp tục.')
        output = Path(batch['output_dir'])
        rows = db.execute('SELECT * FROM download_items WHERE batch_id=?', (batch_id,)).fetchall()
        for row in rows:
            if row['status'] in {'completed', 'skipped'} and _valid_file(row['file_path'], row['file_size'], output):
                continue
            db.execute("UPDATE download_items SET status='queued',error_code=NULL,error_message=NULL WHERE batch_id=? AND video_id=?",
                       (batch_id, row['video_id']))
        pending = db.execute("SELECT 1 FROM download_items WHERE batch_id=? AND status='queued' LIMIT 1", (batch_id,)).fetchone()
        db.execute('UPDATE download_batches SET status=?,finished_at=NULL WHERE id=?', ('queued' if pending else 'completed', batch_id))
        set_setting(db, 'stop_requested_batch', '')
        return get_batch(db, batch_id)


def recover_batch(db, batch_id):
    """Recover only after proving no live worker owns this database; do not auto-run."""
    with _worker_lock(db), transaction(db):
        batch = get_batch(db, batch_id)
        if batch['status'] == 'running':
            db.execute("UPDATE download_items SET status='queued' WHERE batch_id=? AND status='running'", (batch_id,))
            db.execute("UPDATE download_batches SET status='paused' WHERE id=?", (batch_id,))
        return get_batch(db, batch_id)


@contextmanager
def worker_session(db, batch_id):
    """Hold an OS lock for the worker's entire lifetime, including cleanup."""
    with _worker_lock(db) as lock_fd:
        with transaction(db):
            batch = get_batch(db, batch_id)
            if batch['status'] != 'queued':
                raise ValueError('Batch phải ở trạng thái queued trước khi chạy worker.')
            active = _active(db)
            if active is None or active[0] != batch_id:
                raise BatchBusyError('Batch khác đang giữ quyền tải.')
            db.execute("UPDATE download_batches SET status='running' WHERE id=?", (batch_id,))
        try:
            yield dict(get_batch(db, batch_id), worker_lock_fd=lock_fd)
        finally:
            with transaction(db):
                db.execute("UPDATE download_items SET status='queued' WHERE batch_id=? AND status='running'", (batch_id,))
                db.execute("UPDATE download_batches SET status='paused' WHERE id=? AND status='running'", (batch_id,))
