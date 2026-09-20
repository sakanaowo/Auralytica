"""Isolated yt-dlp child: JSON protocol on stdout, no database access."""

import json
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
                                        'video is unavailable', 'not available')):
        return 'unavailable', 'Video không khả dụng, đã bị xóa hoặc đặt riêng tư.', False
    return 'download_error', 'yt-dlp không thể tải video này.', False


def main():
    video_id, directory = sys.argv[1:]
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}',video_id):
        raise ValueError('Invalid video ID')
    def progress(data):
        emit({'type':'progress','downloaded_bytes':data.get('downloaded_bytes',0),
              'total_bytes':data.get('total_bytes') or data.get('total_bytes_estimate')})
    options = {
        'format':'bestaudio', 'noplaylist':True, 'quiet':True, 'no_warnings':True,
        'logger':QuietLogger(), 'progress_hooks':[progress],
        'outtmpl':str(Path(directory)/'audio.%(ext)s'),
        'continuedl':True, 'nopart':False, 'overwrites':False,
        'socket_timeout':15, 'retries':2, 'fragment_retries':2,
        'js_runtimes':{'node':{}},
    }
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info('https://www.youtube.com/watch?v='+video_id, download=True)
            downloaded = (info.get('requested_downloads') or [info])[0]
            emit({'type':'result','id':info['id'],
                  'path':downloaded.get('filepath') or ydl.prepare_filename(info),
                  'acodec':downloaded.get('acodec', info.get('acodec')),
                  'vcodec':downloaded.get('vcodec', info.get('vcodec'))})
    except Exception as exc:
        code, message, fatal = summarize_error(exc)
        emit({'type':'error','code':code,'message':message,'fatal':fatal})
        raise SystemExit(1)


if __name__ == '__main__':
    main()
