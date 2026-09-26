"""Web download controls; background workers outlive the requesting client."""
from contextlib import closing
from pathlib import Path
import subprocess
import sys
import threading

from .batches import create_batch, eligible_snapshot, get_batch, pause_batch, recover_batch, resume_batch
from .downloader import request_stop
from .storage import BatchBusyError, get_setting, open_database, set_setting, transaction


def preview(db, output_dir):
    snapshot = eligible_snapshot(db, output_dir)
    return {key: value for key, value in snapshot.items() if not key.startswith('_')}


def batch_status(db, batch_id=None, *, page=1, page_size=50, status=None):
    if page < 1 or not 1 <= page_size <= 1000:
        raise ValueError('Phân trang không hợp lệ.')
    if batch_id is None:
        row = db.execute("SELECT id FROM download_batches ORDER BY status IN ('queued','running') DESC,id DESC LIMIT 1").fetchone()
        if row is None:
            return None
        batch_id = row[0]
    batch = get_batch(db, batch_id)

    where_conditions = ['d.batch_id=?']
    params = [batch_id]
    if status and status != 'all':
        if status == 'completed':
            where_conditions.append("d.status IN ('completed', 'skipped')")
        else:
            where_conditions.append("d.status = ?")
            params.append(status)

    where_clause = ' WHERE ' + ' AND '.join(where_conditions)
    filtered_total = db.execute(f'SELECT COUNT(*) FROM download_items d {where_clause}', params).fetchone()[0]

    query = (
        f'SELECT d.*,v.title FROM download_items d JOIN videos v ON v.id=d.video_id {where_clause} '
        "ORDER BY CASE d.status WHEN 'running' THEN 0 WHEN 'failed' THEN 1 ELSE 2 END,d.video_id LIMIT ? OFFSET ?"
    )
    items = [dict(row) for row in db.execute(query, (*params, page_size, (page-1)*page_size))]
    return dict(batch, items=items, page=page, page_size=page_size,
                filtered_total=filtered_total, filter_status=status or 'all',
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


def start_download(db, database, *, output_dir=None, preview_token=None, batch_id=None,
                   format_type='raw', clean_names=False, embed_metadata=False,
                   concurrency=None, launcher=launch_worker):
    if batch_id is None:
        batch = create_batch(db, output_dir, expected_token=preview_token,
                             format_type=format_type, clean_names=clean_names,
                             embed_metadata=embed_metadata, concurrency=concurrency)
    else:
        if concurrency is not None:
            set_setting(db, f'batch_concurrency:{batch_id}', str(max(1, min(int(concurrency), 8))))
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


def retry_failed(db, database, batch_id, launcher=launch_worker):
    batch = get_batch(db, batch_id)
    if batch['status'] == 'running':
        raise BatchBusyError('Worker đang tải; hãy tạm dừng trước khi thử lại bài lỗi.')
    with transaction(db):
        db.execute("UPDATE download_items SET status='queued',error_code=NULL,error_message=NULL WHERE batch_id=? AND status='failed'", (batch_id,))
        pending = db.execute("SELECT 1 FROM download_items WHERE batch_id=? AND status='queued' LIMIT 1", (batch_id,)).fetchone()
        if pending:
            db.execute("UPDATE download_batches SET status='queued',finished_at=NULL WHERE id=?", (batch_id,))
            set_setting(db, 'stop_requested_batch', '')
            set_setting(db, f'batch_error:{batch_id}', '')
    batch = get_batch(db, batch_id)
    if batch['status'] == 'queued':
        launcher(database, batch_id)
    return batch


def retry_item(db, database, batch_id, video_id, launcher=launch_worker):
    batch = get_batch(db, batch_id)
    if batch['status'] == 'running':
        raise BatchBusyError('Worker đang tải; hãy tạm dừng trước khi thử lại bài lỗi.')
    with transaction(db):
        db.execute("UPDATE download_items SET status='queued',error_code=NULL,error_message=NULL WHERE batch_id=? AND video_id=?", (batch_id, video_id))
        db.execute("UPDATE download_batches SET status='queued',finished_at=NULL WHERE id=?", (batch_id,))
        set_setting(db, 'stop_requested_batch', '')
        set_setting(db, f'batch_error:{batch_id}', '')
    batch = get_batch(db, batch_id)
    if batch['status'] == 'queued':
        launcher(database, batch_id)
    return batch


def skip_item(db, batch_id, video_id):
    """Mark a specific failed item as skipped and exclude it from future downloads."""
    batch = get_batch(db, batch_id)
    if batch['status'] == 'running':
        raise BatchBusyError('Worker đang tải; hãy tạm dừng trước khi bỏ qua bài lỗi.')
    with transaction(db):
        row = db.execute(
            "SELECT status FROM download_items WHERE batch_id=? AND video_id=?",
            (batch_id, video_id),
        ).fetchone()
        if not row:
            raise ValueError("Không tìm thấy bài hát trong lượt tải.")
        db.execute(
            "UPDATE download_items SET status='skipped', error_code=NULL, error_message='Đã bỏ qua bài lỗi do người dùng chọn' "
            "WHERE batch_id=? AND video_id=?",
            (batch_id, video_id),
        )
        current_rev = int(get_setting(db, 'dedup_selection_revision') or 0)
        new_rev = current_rev + 1
        db.execute(
            "INSERT INTO download_selections(video_id, keep, revision) VALUES(?, 0, ?) "
            "ON CONFLICT(video_id) DO UPDATE SET keep=0, revision=excluded.revision, updated_at=CURRENT_TIMESTAMP",
            (video_id, new_rev),
        )
        set_setting(db, 'dedup_selection_revision', str(new_rev))

        counts = get_batch(db, batch_id)['counts']
        if not counts.get('failed') and not counts.get('queued') and not counts.get('running'):
            db.execute("UPDATE download_batches SET status='completed', finished_at=CURRENT_TIMESTAMP WHERE id=?", (batch_id,))
    return get_batch(db, batch_id)


def skip_failed(db, batch_id):
    """Mark all failed items in the batch as skipped and exclude them from future downloads."""
    batch = get_batch(db, batch_id)
    if batch['status'] == 'running':
        raise BatchBusyError('Worker đang tải; hãy tạm dừng trước khi bỏ qua các bài lỗi.')
    with transaction(db):
        failed_rows = db.execute(
            "SELECT video_id FROM download_items WHERE batch_id=? AND status='failed'",
            (batch_id,),
        ).fetchall()
        if not failed_rows:
            return get_batch(db, batch_id)

        failed_ids = [r['video_id'] for r in failed_rows]
        db.execute(
            "UPDATE download_items SET status='skipped', error_code=NULL, error_message='Đã bỏ qua bài lỗi do người dùng chọn' "
            "WHERE batch_id=? AND status='failed'",
            (batch_id,),
        )
        current_rev = int(get_setting(db, 'dedup_selection_revision') or 0)
        new_rev = current_rev + 1
        for vid in failed_ids:
            db.execute(
                "INSERT INTO download_selections(video_id, keep, revision) VALUES(?, 0, ?) "
                "ON CONFLICT(video_id) DO UPDATE SET keep=0, revision=excluded.revision, updated_at=CURRENT_TIMESTAMP",
                (vid, new_rev),
            )
        set_setting(db, 'dedup_selection_revision', str(new_rev))

        counts = get_batch(db, batch_id)['counts']
        if not counts.get('failed') and not counts.get('queued') and not counts.get('running'):
            db.execute("UPDATE download_batches SET status='completed', finished_at=CURRENT_TIMESTAMP WHERE id=?", (batch_id,))
    return get_batch(db, batch_id)


