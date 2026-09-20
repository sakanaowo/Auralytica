"""Isolated yt-dlp child: JSON protocol on stdout, no database access."""

import json
import os
from pathlib import Path
import re
import sys

import yt_dlp


def emit(message):
    print(json.dumps(message, ensure_ascii=False), flush=True)


class QuietLogger:
    def debug(self, message): pass
    def info(self, message): pass
    def warning(self, message): pass
    def error(self, message): pass


def summarize_error(exc):
    """Return a useful local status without persisting provider URLs or tokens."""
    raw = str(exc).casefold()
    fatal = isinstance(exc, OSError) or any(
        marker in raw for marker in ('no space left on device', 'permission denied', 'read-only file system'))
    if fatal:
        return 'filesystem', 'Không thể ghi file tải; kiểm tra quyền và dung lượng.', True
    if any(marker in raw for marker in ('private video', 'video unavailable', 'has been removed',
                                        'video is unavailable', 'not available', 'this video is private',
                                        'account associated with this video has been terminated')):
        return 'unavailable', 'Video không khả dụng, đã bị xóa hoặc đặt riêng tư.', False
    if any(marker in raw for marker in ('sign in to confirm your age', 'age-restricted', 'confirm your age')):
        return 'age_restricted', 'Video giới hạn độ tuổi; cần cookie đăng nhập YouTube.', False
    if any(marker in raw for marker in ('not available in your country', 'blocked in your country', 'geo-restricted', 'geographic')):
        return 'geo_restricted', 'Video bị giới hạn vùng quốc gia (Geo-restricted).', False
    if any(marker in raw for marker in ('429', 'too many requests', 'rate-limit', 'rate limited')):
        return 'rate_limited', 'YouTube tạm giới hạn tần suất (429 Too Many Requests); hãy thử lại sau ít phút.', False
    if any(marker in raw for marker in ('bot', 'sign in to confirm you’re not a bot', "sign in to confirm you're not a bot", 'captcha')):
        return 'bot_blocked', 'YouTube chặn bot/IP tạm thời; hãy thử lại hoặc dùng cookie.', False
    if any(marker in raw for marker in ('requested format is not available', 'no suitable format found')):
        return 'format_unavailable', 'Không tìm thấy định dạng âm thanh phù hợp trên YouTube.', False
    if any(marker in raw for marker in ('timed out', 'timeout', 'connection refused', 'network is unreachable', 'socket')):
        return 'network_error', 'Lỗi kết nối mạng hoặc timeout khi kết nối tới YouTube.', False
    return 'download_error', 'yt-dlp không thể tải video này.', False


def find_cookies(directory):
    candidates = [
        Path(directory) / 'cookies.txt',
        Path(directory).parent.parent / 'cookies.txt',
        Path.home() / '.local/share/auralytica/cookies.txt',
        Path.home() / '.config/auralytica/cookies.txt',
    ]
    env_cookie = os.getenv('AURALYTICA_COOKIES')
    if env_cookie:
        candidates.insert(0, Path(env_cookie))
    for c in candidates:
        try:
            if c.is_file() and c.stat().st_size > 0:
                return str(c)
        except OSError:
            pass
    return None


def main():
    video_id, directory = sys.argv[1:]
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
        raise ValueError('Invalid video ID')

    def progress(data):
        emit({'type': 'progress', 'downloaded_bytes': data.get('downloaded_bytes', 0),
              'total_bytes': data.get('total_bytes') or data.get('total_bytes_estimate')})

    cookie_file = find_cookies(directory)
    options = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'logger': QuietLogger(),
        'progress_hooks': [progress],
        'outtmpl': str(Path(directory) / 'audio.%(ext)s'),
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'best'}],
        'continuedl': True,
        'nopart': False,
        'overwrites': False,
        'socket_timeout': 15,
        'retries': 3,
        'fragment_retries': 3,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'mweb', 'web'],
            }
        },
        'js_runtimes': {'node': {}},
    }
    if cookie_file:
        options['cookiefile'] = cookie_file

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info('https://www.youtube.com/watch?v=' + video_id, download=True)
            downloaded = (info.get('requested_downloads') or [info])[0]
            actual_path = downloaded.get('filepath') or ydl.prepare_filename(info)
            if not Path(actual_path).is_file():
                matches = [f for f in Path(directory).iterdir()
                           if f.is_file() and f.name.startswith('audio.') and not f.name.endswith(('.part', '.ytdl'))]
                if matches:
                    actual_path = str(matches[0])
            emit({
                'type': 'result',
                'id': info['id'],
                'path': actual_path,
                'acodec': downloaded.get('acodec') or info.get('acodec') or 'unknown',
                'vcodec': 'none',
            })
    except Exception as exc:
        code, message, fatal = summarize_error(exc)
        emit({'type': 'error', 'code': code, 'message': message, 'fatal': fatal})
        raise SystemExit(1)


if __name__ == '__main__':
    main()
