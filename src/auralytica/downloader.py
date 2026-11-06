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

from .batches import active_batch, get_batch, worker_session, _completed_file
from .converter import clean_title, convert_audio_file, parse_artist_title
from .storage import BatchBusyError, get_setting, open_database, set_setting, transaction


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
    item_dict = dict(item) if not isinstance(item, dict) else item
    raw_title = metadata.get('title') or item_dict.get('title') or 'Audio'
    raw_artist = metadata.get('artist') or item_dict.get('channel_name') or ''
    if raw_artist:
        raw_artist = re.sub(r'\s*-\s*Topic\s*$', '', raw_artist, flags=re.IGNORECASE).strip()

    if clean_names:
        clean_stem = clean_title(raw_title, strip_video_id=True, clean_youtube_tags=True)
        artist, title = parse_artist_title(clean_stem, raw_artist)
        if artist and title and ' - ' not in clean_stem:
            clean_stem = f"{artist} - {title}"
        elif artist and title:
            clean_stem = f"{artist} - {title}"
        stem = re.sub(r'[/\\:*?"<>|]', '', clean_stem).strip(' .')[:120] or 'Audio'
    else:
        stem = re.sub(r'[^\w\s.-]', '', item_dict.get('title') or 'Audio', flags=re.UNICODE)
        stem = re.sub(r'\s+', ' ', stem).strip(' .')[:80] or 'Audio'
        stem += f" [{item_dict['video_id']}]"

    previous = item_dict.get('file_path')
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
                   (str(path), staged.stat().st_size, batch_id, item_dict['video_id']))
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
        is_direct = batch['kind'] == 'direct'

        # Quick-download items carry their own edited tags; Takeout items use the shared videos row.
        items = db.execute('SELECT d.*,COALESCE(dd.title,v.title) AS title,COALESCE(dd.artist,v.channel_name) AS channel_name '
                           'FROM download_items d JOIN videos v ON v.id=d.video_id '
                           'LEFT JOIN direct_download_items dd ON dd.batch_id=d.batch_id AND dd.video_id=d.video_id '
                           'WHERE d.batch_id=? ORDER BY d.video_id', (batch_id,)).fetchall()
        items = [dict(it) for it in items]

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
            target_ext = ('.mp3' if format_type in ('mp3', 'mp3_320') else '.m4a') if format_type in ('m4a_alac', 'm4a_aac', 'mp3', 'mp3_320') else None
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
                if is_direct:
                    tag_title = (item.get('title') or '').strip() or result.get('title') or ''
                    tag_artist = (item.get('channel_name') or '').strip() or result.get('artist') or ''
                else:
                    tag_title = result.get('title') or item.get('title') or ''
                    tag_artist = result.get('artist') or item.get('channel_name') or ''

                if format_type in ('m4a_alac', 'm4a_aac', 'mp3', 'mp3_320'):
                    target_ext_file = '.mp3' if format_type in ('mp3', 'mp3_320') else '.m4a'
                    transcoded_path = directory / f'transcoded{target_ext_file}'
                    thumb = result.get('thumbnail_path') if embed_metadata else None

                    user_title = (item.get('title') or '').strip()
                    user_artist = (item.get('channel_name') or '').strip()
                    if is_direct:
                        raw_title = user_title or result.get('title') or ''
                        raw_artist = user_artist or result.get('artist') or ''
                    else:
                        raw_title = result.get('title') or user_title or ''
                        raw_artist = result.get('artist') or user_artist or ''

                    if raw_artist:
                        raw_artist = re.sub(r'\s*-\s*Topic\s*$', '', raw_artist, flags=re.IGNORECASE).strip()

                    if clean_names:
                        clean_stem = clean_title(raw_title, strip_video_id=True, clean_youtube_tags=True)
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
                            format_type='mp3' if format_type in ('mp3', 'mp3_320') else format_type,
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
                    'title': tag_title,
                    'artist': tag_artist,
                }
                with db_lock:
                    tdb = get_thread_db()
                    final = _publish(tdb, batch_id, item, final_staged, output, clean_names, meta)
                    size = final.stat().st_size
                    tdb.execute("UPDATE download_items SET status='completed',file_path=?,file_size=?,downloaded_bytes=?,total_bytes=? WHERE batch_id=? AND video_id=?",
                                (str(final), size, size, size, batch_id, video_id))
                    with suppress(Exception):
                        from .player import cache_single_track
                        cache_single_track(tdb, str(final))
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


# ---------------------------------------------------------------------------
# Direct YouTube URL Parsing & Batch Creation
# ---------------------------------------------------------------------------

YOUTUBE_WATCH_REGEX = re.compile(
    r'(?:https?:\/\/)?(?:www\.|m\.|music\.)?(?:youtube\.com\/(?:watch\?(?:.*&)?v=|embed\/|shorts\/)|youtu\.be\/)([A-Za-z0-9_-]{11})'
)
YOUTUBE_PLAYLIST_REGEX = re.compile(
    r'(?:https?:\/\/)?(?:www\.|m\.|music\.)?youtube\.com\/playlist\?(?:.*&)?list=([A-Za-z0-9_-]+)'
)
BARE_VIDEO_ID_REGEX = re.compile(r'^[A-Za-z0-9_-]{11}$')


def parse_youtube_url(url: str) -> dict | None:
    """Parse a single YouTube link and identify if it is a video or playlist."""
    if not url or not isinstance(url, str):
        return None
    url = url.strip()
    if not url:
        return None

    # Check playlist first ONLY if it is a pure playlist URL (without a watch v= parameter)
    if ('/playlist' in url or 'playlist?' in url) and 'v=' not in url:
        match = YOUTUBE_PLAYLIST_REGEX.search(url)
        if match:
            return {'type': 'playlist', 'id': match.group(1)}

    # Check watch / embed / shorts / youtu.be
    match = YOUTUBE_WATCH_REGEX.search(url)
    if match:
        return {'type': 'video', 'id': match.group(1)}

    # Fallback to playlist regex
    match = YOUTUBE_PLAYLIST_REGEX.search(url)
    if match:
        return {'type': 'playlist', 'id': match.group(1)}

    # Check bare 11-char ID
    if BARE_VIDEO_ID_REGEX.match(url):
        return {'type': 'video', 'id': url}

    return None


MAX_DIRECT_VIDEOS = 1000

# Flat playlist entries for removed videos keep their slot with one of these titles.
_PLAYLIST_PLACEHOLDER_TITLES = {'[deleted video]', '[private video]', '[unavailable video]'}


def _suggest_tags(vid: str, raw_title: str, raw_channel: str, duration, thumbnail: str | None) -> dict:
    channel_clean = re.sub(r'\s*-\s*Topic\s*$', '', raw_channel, flags=re.IGNORECASE).strip()
    title_clean = clean_title(raw_title, strip_video_id=True, clean_youtube_tags=True)
    suggested_artist, suggested_title = parse_artist_title(title_clean, channel_clean)
    return {
        'video_id': vid,
        'url': f'https://www.youtube.com/watch?v={vid}',
        'title': suggested_title or title_clean or raw_title,
        'artist': suggested_artist or channel_clean or raw_channel,
        'album': 'Auralytica',
        'channel': raw_channel,
        'duration': int(duration or 0),
        'thumbnail_url': thumbnail or f'https://i.ytimg.com/vi/{vid}/hqdefault.jpg',
    }


def _unavailable(vid: str, source: str, code: str, message: str) -> dict:
    return {'video_id': vid, 'url': source, 'code': code, 'message': message}


def _fetch_single_video_info(vid: str, source: str) -> tuple[dict | None, dict | None]:
    """Fetch metadata without downloading media; return (video, None) or (None, unavailable)."""
    url = f'https://www.youtube.com/watch?v={vid}'
    try:
        import yt_dlp
        ydl_opts = {
            'extract_flat': True,
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 10,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        from ._ytdlp import summarize_error
        code, message, _ = summarize_error(exc)
        return None, _unavailable(vid, source, code, message)
    raw_title = info.get('title') or f'YouTube Video [{vid}]'
    raw_channel = info.get('uploader') or info.get('channel') or 'YouTube'
    return _suggest_tags(vid, raw_title, raw_channel, info.get('duration'), info.get('thumbnail')), None


def resolve_direct_urls(urls: list[str]) -> dict:
    """Resolve raw URLs or IDs into downloadable videos.

    Lines that are not YouTube links go to invalid_urls; videos YouTube refuses
    (private, removed, network errors) go to unavailable so they never reach a batch.
    At most MAX_DIRECT_VIDEOS videos are returned; truncated reports the cut.
    """
    videos = []
    invalid_urls = []
    unavailable = []
    seen_ids = set()
    single_videos = []  # (video_id, source line), resolved concurrently below
    truncated = False

    def has_room():
        nonlocal truncated
        if len(videos) + len(single_videos) >= MAX_DIRECT_VIDEOS:
            truncated = True
            return False
        return True

    for raw in urls:
        if not raw or not isinstance(raw, str):
            continue
        cleaned = raw.strip()
        if not cleaned:
            continue

        parsed = parse_youtube_url(cleaned)
        if not parsed:
            invalid_urls.append(cleaned)
            continue

        if parsed['type'] == 'video':
            vid = parsed['id']
            if vid not in seen_ids and has_room():
                seen_ids.add(vid)
                single_videos.append((vid, cleaned))
        elif parsed['type'] == 'playlist':
            playlist_url = f"https://www.youtube.com/playlist?list={parsed['id']}"
            try:
                import yt_dlp
                ydl_opts = {
                    'extract_flat': 'in_playlist',
                    'skip_download': True,
                    'quiet': True,
                    'no_warnings': True,
                    'socket_timeout': 10,
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(playlist_url, download=False)
            except Exception:
                invalid_urls.append(cleaned)
                continue
            for entry in info.get('entries') or []:
                vid = (entry or {}).get('id')
                if not vid or vid in seen_ids:
                    continue
                if not has_room():
                    break
                seen_ids.add(vid)
                raw_title = entry.get('title') or f'Track [{vid}]'
                if raw_title.strip().casefold() in _PLAYLIST_PLACEHOLDER_TITLES:
                    unavailable.append(_unavailable(vid, cleaned, 'unavailable',
                                                    'Video trong playlist đã bị xóa hoặc đặt riêng tư.'))
                    continue
                raw_channel = entry.get('uploader') or entry.get('channel') or 'YouTube'
                videos.append(_suggest_tags(vid, raw_title, raw_channel, entry.get('duration'), None))

    if single_videos:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(single_videos))) as executor:
            for video, failure in executor.map(lambda item: _fetch_single_video_info(*item), single_videos):
                if video:
                    videos.append(video)
                else:
                    unavailable.append(failure)

    return {'videos': videos, 'invalid_urls': invalid_urls, 'unavailable': unavailable, 'truncated': truncated}


def start_batch_worker(database, batch_id):
    """Spawn worker process for batch."""
    from .download_controls import launch_worker
    launch_worker(database, batch_id)


def create_direct_batch(
    db,
    videos: list[dict],
    output_dir: str,
    audio_format: str = 'm4a_alac',
    concurrency: int = 3,
    launcher=None,
    database_path=None,
):
    """Create a quick-download batch and trigger the background worker.

    Edited tags live in direct_download_items so Takeout titles, channels and
    groups in the shared videos table are never rewritten.
    """
    if not videos:
        raise ValueError('Danh sách bài hát trống.')
    if len(videos) > MAX_DIRECT_VIDEOS:
        raise ValueError(f'Mỗi lượt Tải nhanh tối đa {MAX_DIRECT_VIDEOS} bài.')

    if audio_format in ('mp3', 'mp3_320'):
        format_type = 'mp3'
    elif audio_format in ('m4a_aac', 'aac'):
        format_type = 'm4a_aac'
    elif audio_format in ('raw', 'none'):
        format_type = 'raw'
    else:
        format_type = 'm4a_alac'

    output_path = str(Path(output_dir).expanduser().resolve())

    unique = {}
    for v in videos:
        unique.setdefault(v['video_id'], v)

    with transaction(db):
        active = active_batch(db)
        if active:
            raise BatchBusyError(f'Lượt tải #{active[0]} đang chờ/chạy; đợi xong hoặc tạm dừng trước khi tạo lượt mới.')

        cursor = db.execute(
            "INSERT INTO download_batches (output_dir, status, kind) VALUES (?, 'queued', 'direct')",
            (output_path,),
        )
        batch_id = cursor.lastrowid
        set_setting(db, f'batch_format:{batch_id}', format_type)
        set_setting(db, f'batch_concurrency:{batch_id}', str(max(1, min(concurrency, 8))))
        set_setting(db, f'batch_clean_names:{batch_id}', '1')
        set_setting(db, f'batch_embed_metadata:{batch_id}', '1')

        for vid, v in unique.items():
            title = (v.get('title') or '').strip() or f'YouTube Video [{vid}]'
            artist = (v.get('artist') or v.get('channel') or '').strip() or 'YouTube'
            thumb = v.get('thumbnail_url') or f'https://i.ytimg.com/vi/{vid}/hqdefault.jpg'
            # download_items needs a videos row; an existing Takeout row stays untouched.
            db.execute(
                "INSERT INTO videos (id, title, channel_name, thumbnail_url) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(id) DO NOTHING",
                (vid, title, artist, thumb),
            )
            db.execute(
                "INSERT INTO download_items (batch_id, video_id, status) VALUES (?, ?, 'queued')",
                (batch_id, vid),
            )
            db.execute(
                "INSERT INTO direct_download_items (batch_id, video_id, title, artist) VALUES (?, ?, ?, ?)",
                (batch_id, vid, title, artist),
            )

    if launcher:
        launcher(database_path or '', batch_id)
    elif database_path:
        start_batch_worker(database_path, batch_id)

    return batch_id
