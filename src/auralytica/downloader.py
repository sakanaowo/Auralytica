"""Sequential audio worker with resumable staging and process cancellation."""

import json
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import sys
import tempfile
from contextlib import suppress

from .batches import get_batch, worker_session, _completed_file
from .storage import get_setting, set_setting, transaction


class DownloadStopped(Exception):
    pass


class DownloadFailure(Exception):
    def __init__(self, code, message, *, fatal=False):
        super().__init__(message)
        self.code = code
        self.fatal = fatal


class YtDlpAdapter:
    def __init__(self, command=None):
        self.command = command or [sys.executable, '-m', 'auralytica._ytdlp']

    def __call__(self, video_id, directory, progress, stopped, lock_fd):
        if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
            raise DownloadFailure('invalid_id', 'Video ID không hợp lệ.')
        process = subprocess.Popen([*self.command, video_id, str(directory)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True,
            pass_fds=(lock_fd,) if lock_fd is not None else ())
        result, failure = None, None
        pending = b''
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while selector.get_map():
                    if stopped():
                        raise DownloadStopped()
                    for key, _ in selector.select(.2):
                        chunk = os.read(key.fd, 65536)
                        if not chunk:
                            selector.unregister(key.fileobj)
                            continue
                        pending += chunk
                        while b'\n' in pending:
                            line, pending = pending.split(b'\n', 1)
                            try:
                                message = json.loads(line)
                            except (ValueError, UnicodeError):
                                continue
                            if not isinstance(message, dict):
                                continue
                            if message.get('type') == 'progress':
                                progress(message.get('downloaded_bytes', 0), message.get('total_bytes'))
                            elif message.get('type') == 'result':
                                result = message
                            elif message.get('type') == 'error':
                                failure = DownloadFailure(message.get('code','download_error'),
                                    str(message.get('message','Tải thất bại.'))[:1500], fatal=message.get('fatal') is True)
                        if len(pending) > 65536:
                            pending = b''
                while process.poll() is None:
                    if stopped():
                        raise DownloadStopped()
                    try: process.wait(timeout=.2)
                    except subprocess.TimeoutExpired: pass
            if process.returncode or failure or result is None:
                raise failure or DownloadFailure('download_error', f'yt-dlp không trả file hoàn tất (exit {process.returncode}).')
            return result
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try: process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
            process.stdout.close()


def request_stop(db, batch_id):
    with transaction(db):
        batch = get_batch(db, batch_id)
        if batch['status'] == 'queued':
            db.execute("UPDATE download_batches SET status='paused' WHERE id=?", (batch_id,))
        elif batch['status'] == 'running':
            set_setting(db, 'stop_requested_batch', str(batch_id))
        return get_batch(db, batch_id)


def _publish(db, batch_id, item, staged, output):
    """Link without overwrite. Persist the planned path before publishing for recovery."""
    stem = re.sub(r'[^\w\s.-]', '', item['title'], flags=re.UNICODE)
    stem = re.sub(r'\s+', ' ', stem).strip(' .')[:80] or 'Audio'
    stem += f" [{item['video_id']}]"
    previous = item['file_path']
    if previous:
        previous = Path(previous)
        if previous.parent == output and previous.exists() and os.path.samefile(staged, previous):
            return previous
    suffix = staged.suffix
    number = 0
    while True:
        path = output / (stem + (f' ({number})' if number else '') + suffix)
        # A crash after link leaves the staging hardlink and this planned path,
        # allowing the next run to recognize the already-published file by inode.
        db.execute('UPDATE download_items SET file_path=?,file_size=? WHERE batch_id=? AND video_id=?',
                   (str(path), staged.stat().st_size, batch_id, item['video_id']))
        try:
            os.link(staged, path)
            return path
        except FileExistsError:
            number += 1


def run_batch(db, batch_id, *, adapter=None):
    adapter = adapter or YtDlpAdapter()
    with worker_session(db, batch_id) as batch:
        output = Path(batch['output_dir'])
        stopped = lambda: get_setting(db, 'stop_requested_batch') == str(batch_id)
        items = db.execute('SELECT d.*,v.title FROM download_items d JOIN videos v ON v.id=d.video_id '
                           'WHERE d.batch_id=? ORDER BY d.video_id', (batch_id,)).fetchall()
        interrupted = False
        try:
            output.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryFile(dir=output): pass
            for item in items:
                if stopped(): break
                video_id = item['video_id']
                previous = _completed_file(db, video_id, output)
                if previous:
                    if item['status'] not in {'completed', 'skipped'}:
                        db.execute("UPDATE download_items SET status='skipped',file_path=?,file_size=? WHERE batch_id=? AND video_id=?",
                                   (previous['file_path'], previous['file_size'], batch_id, video_id))
                    continue
                directory = output / '.auralytica' / f'batch-{batch_id}' / video_id
                db.execute("UPDATE download_items SET status='running',attempts=attempts+1,error_code=NULL,error_message=NULL WHERE batch_id=? AND video_id=?",
                           (batch_id, video_id))

                def progress(downloaded, total):
                    downloaded = downloaded if type(downloaded) is int and downloaded >= 0 else 0
                    total = total if type(total) is int and total >= 0 else None
                    db.execute('UPDATE download_items SET downloaded_bytes=?,total_bytes=? WHERE batch_id=? AND video_id=?',
                               (downloaded, total, batch_id, video_id))
                try:
                    directory.mkdir(parents=True, exist_ok=True)
                    result = adapter(video_id, directory, progress, stopped, batch['worker_lock_fd'])
                    staged = Path(result.get('path','')).resolve()
                    if (result.get('id') != video_id or result.get('vcodec') != 'none'
                        or not result.get('acodec') or result['acodec'] == 'none'
                        or staged.parent != directory.resolve() or not staged.is_file()
                        or not re.fullmatch(r'\.[a-zA-Z0-9]{1,10}', staged.suffix)
                        or staged.suffix in {'.part','.ytdl'} or staged.stat().st_size <= 0):
                        raise DownloadFailure('invalid_output','File trả về không phải audio hoàn tất của video đã chọn.')
                    final = _publish(db, batch_id, item, staged, output)
                    size = final.stat().st_size
                    db.execute("UPDATE download_items SET status='completed',file_path=?,file_size=?,downloaded_bytes=?,total_bytes=? WHERE batch_id=? AND video_id=?",
                               (str(final), size, size, size, batch_id, video_id))
                    with suppress(OSError):
                        staged.unlink()  # Cleanup cannot invalidate the published file.
                except DownloadStopped:
                    interrupted = True
                    break
                except (DownloadFailure, OSError) as exc:
                    fatal = isinstance(exc, OSError) or exc.fatal
                    db.execute("UPDATE download_items SET status='failed',error_code=?,error_message=? WHERE batch_id=? AND video_id=?",
                               ('filesystem' if isinstance(exc,OSError) else exc.code, str(exc)[:1500], batch_id, video_id))
                    if fatal:
                        interrupted = True
                        break
            counts = get_batch(db, batch_id)['counts']
            if interrupted or counts.get('queued') or counts.get('running') or stopped():
                status = 'paused'
            else:
                status = 'partial' if counts.get('failed') else 'completed'
            db.execute('UPDATE download_batches SET status=?,finished_at=CASE WHEN ? IN (\'completed\',\'partial\') THEN CURRENT_TIMESTAMP ELSE NULL END WHERE id=?',
                       (status, status, batch_id))
        except OSError as exc:
            # Output preflight errors keep every pending item retryable.
            raise DownloadFailure('filesystem',str(exc),fatal=True) from exc
    return get_batch(db, batch_id)
