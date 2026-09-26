import concurrent.futures
import errno
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
from contextlib import suppress

from .batches import get_batch, worker_session, _completed_file
from .converter import clean_title, convert_audio_file, parse_artist_title
from .storage import get_setting, open_database, set_setting, transaction


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


def _publish(db, batch_id, item, staged, output, clean_names=False, metadata=None):
    """Link without overwrite. Persist the planned path before publishing for recovery."""
    metadata = metadata or {}
    if clean_names:
        raw_title = metadata.get('title') or item['title'] or 'Audio'
        clean_stem = clean_title(raw_title, strip_video_id=True, clean_youtube_tags=True)
        raw_artist = metadata.get('artist') or item['channel_name'] or ''
        if raw_artist:
            raw_artist = re.sub(r'\s*-\s*Topic\s*$', '', raw_artist, flags=re.IGNORECASE).strip()
        artist, title = parse_artist_title(clean_stem, raw_artist)
        if artist and title and ' - ' not in clean_stem:
            clean_stem = f"{artist} - {title}"
        stem = re.sub(r'[/\\:*?"<>|]', '', clean_stem).strip(' .')[:120] or 'Audio'
    else:
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
        except OSError as exc:
            if exc.errno == errno.EEXIST:
                number += 1
                continue
            shutil.copyfile(staged, path)
            return path


def run_batch(db, batch_id, *, adapter=None, concurrency=None):
    adapter = adapter or YtDlpAdapter()
    with worker_session(db, batch_id) as batch:
        output = Path(batch['output_dir'])
        if concurrency is None:
            concurrency_str = get_setting(db, f'batch_concurrency:{batch_id}')
            concurrency = int(concurrency_str) if concurrency_str and concurrency_str.isdigit() else 1
        concurrency = max(1, min(concurrency, 8))

        format_type = get_setting(db, f'batch_format:{batch_id}') or 'raw'
        clean_names = get_setting(db, f'batch_clean_names:{batch_id}') == '1'
        embed_metadata = get_setting(db, f'batch_embed_metadata:{batch_id}') != '0'

        items = db.execute('SELECT d.*,v.title,v.channel_name FROM download_items d JOIN videos v ON v.id=d.video_id '
                           'WHERE d.batch_id=? ORDER BY d.video_id', (batch_id,)).fetchall()

        db_path = next(row[2] for row in db.execute('PRAGMA database_list') if row[1] == 'main')
        db_lock = threading.Lock()
        stop_event = threading.Event()
        fatal_error = [None]
        interrupted = False
        worker_dbs = []
        worker_dbs_lock = threading.Lock()
        tls = threading.local()

        def get_thread_db():
            if not hasattr(tls, 'db'):
                conn = open_database(db_path)
                with worker_dbs_lock:
                    worker_dbs.append(conn)
                tls.db = conn
            return tls.db

        def is_stopped():
            if stop_event.is_set():
                return True
            with db_lock:
                tdb = get_thread_db()
                if get_setting(tdb, 'stop_requested_batch') == str(batch_id):
                    stop_event.set()
                    return True
            return False

        def process_item(item):
            nonlocal interrupted
            if is_stopped():
                return
            video_id = item['video_id']
            target_ext = ('.mp3' if format_type == 'mp3' else '.m4a') if format_type in ('m4a_alac', 'm4a_aac', 'mp3') else None
            with db_lock:
                tdb = get_thread_db()
                previous = _completed_file(tdb, video_id, output, target_ext=target_ext)
                if previous:
                    if item['status'] not in {'completed', 'skipped'}:
                        tdb.execute("UPDATE download_items SET status='skipped',file_path=?,file_size=? WHERE batch_id=? AND video_id=?",
                                    (previous['file_path'], previous['file_size'], batch_id, video_id))
                    return

            directory = output / '.auralytica' / f'batch-{batch_id}' / video_id
            with db_lock:
                tdb = get_thread_db()
                tdb.execute("UPDATE download_items SET status='running',attempts=attempts+1,error_code=NULL,error_message=NULL WHERE batch_id=? AND video_id=?",
                            (batch_id, video_id))

            def progress(downloaded, total):
                downloaded = downloaded if type(downloaded) is int and downloaded >= 0 else 0
                total = total if type(total) is int and total >= 0 else None
                with db_lock:
                    tdb = get_thread_db()
                    tdb.execute('UPDATE download_items SET downloaded_bytes=?,total_bytes=? WHERE batch_id=? AND video_id=?',
                                (downloaded, total, batch_id, video_id))

            try:
                directory.mkdir(parents=True, exist_ok=True)
                result = adapter(video_id, directory, progress, is_stopped, batch['worker_lock_fd'])
                staged = Path(result.get('path', '')).resolve()
                if (result.get('id') != video_id or result.get('vcodec') != 'none'
                    or not result.get('acodec') or result['acodec'] == 'none'
                    or staged.parent != directory.resolve() or not staged.is_file()
                    or not re.fullmatch(r'\.[a-zA-Z0-9]{1,10}', staged.suffix)
                    or staged.suffix in {'.part', '.ytdl'} or staged.stat().st_size <= 0):
                    raise DownloadFailure('invalid_output', 'File trả về không phải audio hoàn tất của video đã chọn.')

                final_staged = staged
                if format_type in ('m4a_alac', 'm4a_aac', 'mp3'):
                    target_ext_file = '.mp3' if format_type == 'mp3' else '.m4a'
                    transcoded_path = directory / f'transcoded{target_ext_file}'
                    thumb = result.get('thumbnail_path') if embed_metadata else None
                    raw_title = result.get('title') or item['title'] or ''
                    clean_stem = clean_title(raw_title, strip_video_id=True, clean_youtube_tags=True) if clean_names else raw_title
                    raw_artist = result.get('artist') or item['channel_name'] or ''
                    if raw_artist:
                        raw_artist = re.sub(r'\s*-\s*Topic\s*$', '', raw_artist, flags=re.IGNORECASE).strip()
                    if clean_names:
                        tag_artist, tag_title = parse_artist_title(clean_stem, raw_artist)
                    else:
                        tag_title = raw_title
                        tag_artist = raw_artist
                    tag_album = result.get('album') or 'Auralytica'
                    tag_year = str(result.get('release_year') or '') or None

                    try:
                        convert_audio_file(
                            source_path=staged,
                            target_path=transcoded_path,
                            format_type=format_type,
                            thumbnail_path=thumb,
                            artist=tag_artist if embed_metadata else '',
                            title=tag_title if embed_metadata else '',
                            album=tag_album if embed_metadata else '',
                            year=tag_year if embed_metadata else None,
                        )
                        final_staged = transcoded_path
                    except Exception as exc:
                        raise DownloadFailure('transcode_error', f'Chuyển đổi âm thanh thất bại: {exc}')

                meta = {
                    'title': result.get('title') or item['title'],
                    'artist': result.get('artist') or item['channel_name'],
                }
                with db_lock:
                    tdb = get_thread_db()
                    final = _publish(tdb, batch_id, item, final_staged, output, clean_names, meta)
                    size = final.stat().st_size
                    tdb.execute("UPDATE download_items SET status='completed',file_path=?,file_size=?,downloaded_bytes=?,total_bytes=? WHERE batch_id=? AND video_id=?",
                                (str(final), size, size, size, batch_id, video_id))
                with suppress(OSError):
                    staged.unlink()  # Cleanup cannot invalidate the published file.
                if final_staged != staged:
                    with suppress(OSError):
                        final_staged.unlink()
                if result.get('thumbnail_path'):
                    with suppress(OSError):
                        Path(result['thumbnail_path']).unlink()
            except DownloadStopped:
                interrupted = True
                stop_event.set()
                with db_lock:
                    tdb = get_thread_db()
                    tdb.execute("UPDATE download_items SET status='queued' WHERE batch_id=? AND video_id=? AND status='running'",
                                (batch_id, video_id))
            except (DownloadFailure, OSError) as exc:
                fatal = isinstance(exc, OSError) or exc.fatal
                with db_lock:
                    tdb = get_thread_db()
                    tdb.execute("UPDATE download_items SET status='failed',error_code=?,error_message=? WHERE batch_id=? AND video_id=?",
                                ('filesystem' if isinstance(exc, OSError) else exc.code, str(exc)[:1500], batch_id, video_id))
                if fatal:
                    interrupted = True
                    stop_event.set()
                    fatal_error[0] = exc

        try:
            output.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryFile(dir=output):
                pass

            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
                active_futures = set()
                item_iter = iter(items)
                for _ in range(concurrency):
                    if is_stopped():
                        break
                    try:
                        it = next(item_iter)
                        active_futures.add(executor.submit(process_item, it))
                    except StopIteration:
                        break

                while active_futures:
                    done, active_futures = concurrent.futures.wait(
                        active_futures, return_when=concurrent.futures.FIRST_COMPLETED
                    )
                    for f in done:
                        try:
                            f.result()
                        except (KeyboardInterrupt, SystemExit):
                            stop_event.set()
                            raise
                        except Exception:
                            pass

                    if not is_stopped():
                        for _ in range(len(done)):
                            if is_stopped():
                                break
                            try:
                                it = next(item_iter)
                                active_futures.add(executor.submit(process_item, it))
                            except StopIteration:
                                break
        except OSError as exc:
            # Output preflight errors keep every pending item retryable.
            raise DownloadFailure('filesystem', str(exc), fatal=True) from exc
        finally:
            for conn in worker_dbs:
                with suppress(Exception):
                    conn.close()

        counts = get_batch(db, batch_id)['counts']
        was_stopped = stop_event.is_set() or (get_setting(db, 'stop_requested_batch') == str(batch_id))
        if interrupted or counts.get('queued') or counts.get('running') or was_stopped:
            status = 'paused'
        else:
            status = 'partial' if counts.get('failed') else 'completed'
        db.execute('UPDATE download_batches SET status=?,finished_at=CASE WHEN ? IN (\'completed\',\'partial\') THEN CURRENT_TIMESTAMP ELSE NULL END WHERE id=?',
                   (status, status, batch_id))
    return get_batch(db, batch_id)
