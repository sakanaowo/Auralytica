"""Web download controls; background workers outlive the requesting client."""
from contextlib import closing
from pathlib import Path
import subprocess
import sys
import threading

from .batches import create_batch, eligible_snapshot, get_batch, pause_batch, recover_batch, resume_batch
from .downloader import request_stop
from .storage import BatchBusyError, get_setting, open_database, set_setting


def preview(db, output_dir):
    snapshot = eligible_snapshot(db, output_dir)
    return {key: value for key, value in snapshot.items() if not key.startswith('_')}


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


def start_download(db, database, *, output_dir=None, preview_token=None, batch_id=None, launcher=launch_worker):
    if batch_id is None:
        batch = create_batch(db, output_dir, expected_token=preview_token)
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
