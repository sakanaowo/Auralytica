"""Persistent download snapshots and exclusive local worker ownership."""

from contextlib import contextmanager
import fcntl
from pathlib import Path
import tempfile

from .storage import BatchBusyError, get_setting, set_setting, transaction


def get_batch(db, batch_id):
    row = db.execute('SELECT * FROM download_batches WHERE id=?', (batch_id,)).fetchone()
    if row is None:
        raise ValueError('Không tìm thấy batch.')
    counts = dict(db.execute('SELECT status,COUNT(*) FROM download_items WHERE batch_id=? GROUP BY status', (batch_id,)))
    return dict(batch_id=row['id'], output_dir=row['output_dir'], status=row['status'],
                total=sum(counts.values()), queued=counts.get('queued', 0),
                skipped=counts.get('skipped', 0), counts=counts)


def _active(db):
    return db.execute("SELECT id FROM download_batches WHERE status IN ('queued','running') ORDER BY id LIMIT 1").fetchone()


def _valid_file(file_path, file_size, output):
    if not file_path or file_size is None or file_size <= 0:
        return False
    try:
        path = Path(file_path).resolve()
        return path.parent == output and path.is_file() and path.stat().st_size == file_size
    except OSError:
        return False


def _completed_file(db, video_id, output):
    rows = db.execute("SELECT d.file_path,d.file_size FROM download_items d JOIN download_batches b ON b.id=d.batch_id "
                      "WHERE d.video_id=? AND d.status IN ('completed','skipped') AND b.output_dir=? ORDER BY d.batch_id DESC",
                      (video_id, str(output)))
    return next((row for row in rows if _valid_file(row['file_path'], row['file_size'], output)), None)


def create_batch(db, output_dir):
    """Snapshot the whole effective music group, independent of any UI filters."""
    with transaction(db):
        active = _active(db)
        if active:
            return dict(get_batch(db, active[0]), reused=True)
        active_import = get_setting(db, 'active_import')
        if active_import is None:
            raise ValueError('Hãy import Takeout trước.')
        ids = [row[0] for row in db.execute(
            "SELECT DISTINCT v.id FROM videos v JOIN watch_events e ON e.video_id=v.id "
            "WHERE e.import_id=? AND COALESCE(v.user_group,v.auto_group)='music' ORDER BY v.id", (active_import,))]
        if not ids:
            raise ValueError('Nhóm nhạc đang trống.')
        if not str(output_dir).strip():
            raise ValueError('Cần thư mục tải.')
        output = Path(output_dir).expanduser().resolve()
        output.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=output):
            pass  # Check actual write permission rather than os.access().
        batch_id = db.execute('INSERT INTO download_batches(output_dir) VALUES (?)', (str(output),)).lastrowid
        queued = 0
        for video_id in ids:
            previous = _completed_file(db, video_id, output)
            queued += previous is None
            db.execute('INSERT INTO download_items(batch_id,video_id,status,file_path,file_size) VALUES (?,?,?,?,?)',
                       (batch_id, video_id, 'skipped' if previous else 'queued',
                        previous['file_path'] if previous else None, previous['file_size'] if previous else None))
        if not queued:
            db.execute("UPDATE download_batches SET status='completed',finished_at=CURRENT_TIMESTAMP WHERE id=?", (batch_id,))
        return dict(get_batch(db, batch_id), reused=False)


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
