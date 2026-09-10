"""Shared CLI/web download controls; workers outlive the requesting client."""
from contextlib import closing
from pathlib import Path
import subprocess
import sys
import threading

from .batches import create_batch, get_batch, pause_batch, recover_batch, resume_batch, _completed_file
from .downloader import request_stop
from .storage import BatchBusyError, get_setting, open_database, set_setting


def preview(db, output_dir):
    if not str(output_dir).strip():
        raise ValueError('Cần thư mục tải.')
    output = Path(output_dir).expanduser().resolve()
    ids = [row[0] for row in db.execute(
        "SELECT DISTINCT v.id FROM videos v JOIN watch_events e ON e.video_id=v.id "
        "WHERE e.import_id=? AND COALESCE(v.user_group,v.auto_group)='music'", (get_setting(db, 'active_import'),))]
    skipped = sum(_completed_file(db, video_id, output) is not None for video_id in ids)
    return dict(output_dir=str(output), total=len(ids), skipped=skipped, needed=len(ids)-skipped)


def batch_status(db, batch_id=None, *, page=1, page_size=50):
    if page < 1 or not 1 <= page_size <= 1000:
        raise ValueError('Phân trang không hợp lệ.')
    if batch_id is None:
        row = db.execute("SELECT id FROM download_batches ORDER BY status IN ('queued','running') DESC,id DESC LIMIT 1").fetchone()
        if row is None:
            return None
        batch_id = row[0]
    batch = get_batch(db, batch_id)
    items = [dict(row) for row in db.execute(
        "SELECT d.*,v.title FROM download_items d JOIN videos v ON v.id=d.video_id WHERE batch_id=? "
        "ORDER BY CASE d.status WHEN 'running' THEN 0 WHEN 'failed' THEN 1 ELSE 2 END,d.video_id LIMIT ? OFFSET ?",
        (batch_id, page_size, (page-1)*page_size))]
    return dict(batch, items=items, page=page, page_size=page_size,
                error=get_setting(db, f'batch_error:{batch_id}'),
                stop_requested=get_setting(db, 'stop_requested_batch') == str(batch_id))


def list_batches(db):
    return {'batches': [get_batch(db, row[0]) for row in db.execute(
        "SELECT id FROM download_batches ORDER BY status IN ('queued','running') DESC,id DESC LIMIT 50")]}


def launch_worker(database, batch_id):
    process = subprocess.Popen([sys.executable, '-m', 'auralytica.worker', str(Path(database).resolve()), str(batch_id)],
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               start_new_session=True)
    # Reap children while the web server remains alive; do not block its shutdown.
    threading.Thread(target=process.wait, daemon=True).start()


def start_download(db, database, *, output_dir=None, batch_id=None, launcher=launch_worker):
    if batch_id is None:
        batch = create_batch(db, output_dir)
    else:
        current = get_batch(db, batch_id)
        if current['status'] == 'running':
            recover_batch(db, batch_id)  # Refuses recovery while another worker holds the lock.
        batch = resume_batch(db, batch_id)
    if batch['status'] == 'queued':
        set_setting(db, f"batch_error:{batch['batch_id']}", '')
        try:
            launcher(database, batch['batch_id'])
        except OSError as exc:
            pause_batch(db, batch['batch_id'])
            set_setting(db, f"batch_error:{batch['batch_id']}", str(exc)[:1500])
            return get_batch(db, batch['batch_id'])
    return batch


def stop_download(db, batch_id):
    if get_batch(db, batch_id)['status'] == 'running':
        try:
            return recover_batch(db, batch_id)
        except BatchBusyError:
            pass
    return request_stop(db, batch_id)
