"""Audio conversion and title/filename sanitizer for Apple Music compatibility."""

import os
from pathlib import Path
import re
import shlex
import subprocess
import threading
import time
from typing import Any

from .storage import open_database

# Regex pattern for YouTube 11-char video ID in brackets, e.g. [nIS-srtakdM]
VIDEO_ID_BRACKET_RE = re.compile(r'\s*\[[A-Za-z0-9_-]{11}\](?=\.[a-zA-Z0-9]+$|$)', re.IGNORECASE)

# YouTube clutter tags inside parentheses or brackets
BRACKETED_TAGS_RE = re.compile(
    r'\s*[\(\[\{]\s*(?:'
    r'official\s+(?:music\s+)?video|official\s+audio|official\s+lyric\s+video|'
    r'music\s+video|lyric\s+video|audio\s+video|full\s+audio|'
    r'hq\s+audio|high\s+quality\s+audio|audio|lyrics?|visualizer|'
    r'mv|hd|hq|4k|1080p|720p|original|full\s+song|topic'
    r')\s*[\)\]\}]',
    re.IGNORECASE,
)

# Unbracketed trailing clutter keywords
TRAILING_CLUTTER_RE = re.compile(
    r'\s*[-–—|/]?\s*\b(?:'
    r'official\s+music\s+video|official\s+lyric\s+video|official\s+video|official\s+audio|'
    r'music\s+video|lyric\s+video|full\s+audio|high\s+quality\s+audio|'
    r'official\s+hd|official\s+mv|official'
    r')\b\s*$',
    re.IGNORECASE,
)


def clean_title(
    raw_name: str,
    *,
    strip_video_id: bool = True,
    clean_youtube_tags: bool = True,
) -> str:
    """Clean video titles or filenames by stripping YouTube video IDs and clutter tags."""
    # Split extension if present
    path = Path(raw_name)
    suffix = path.suffix if re.fullmatch(r'\.[a-zA-Z0-9]{1,10}', path.suffix) else ''
    stem = path.stem if suffix else raw_name

    # 1. Strip video ID in brackets [xyz123]
    if strip_video_id:
        stem = VIDEO_ID_BRACKET_RE.sub('', stem)

    # 2. Strip bracketed YouTube tags e.g. (Official Music Video), [Audio], etc.
    if clean_youtube_tags:
        # Repeat until all matched bracket tags are removed
        for _ in range(3):
            new_stem = BRACKETED_TAGS_RE.sub('', stem)
            if new_stem == stem:
                break
            stem = new_stem

        # Strip trailing clutter keywords
        stem = TRAILING_CLUTTER_RE.sub('', stem)

    # 3. Clean up spacing and separators
    stem = re.sub(r'[\t\r\n]+', ' ', stem)
    stem = re.sub(r'\s*[–—]\s*', ' - ', stem)
    stem = re.sub(r'\s+-\s*|\s*-\s+', ' - ', stem)
    stem = re.sub(r'\s{2,}', ' ', stem)
    stem = stem.strip(' .-_')

    return stem or 'Audio'


def parse_artist_title(cleaned_stem: str, fallback_artist: str = '') -> tuple[str, str]:
    """Extract (artist, title) from a cleaned stem like 'Artist - Title'."""
    if ' - ' in cleaned_stem:
        parts = cleaned_stem.split(' - ', 1)
        artist = parts[0].strip()
        title = parts[1].strip()
        if artist and title:
            return artist, title
    return fallback_artist.strip(), cleaned_stem.strip()


def is_apple_music_compatible(suffix: str) -> bool:
    """Check if file format is natively compatible with Apple Music / iTunes."""
    return suffix.lower() in ('.m4a', '.mp3', '.aiff', '.aif', '.wav', '.alac')


def scan_directory(db_path: str | Path | None, directory_path: str | Path) -> dict[str, Any]:
    """Scan directory for audio files and prepare clean name and compatibility analysis."""
    root = Path(directory_path).expanduser().resolve()
    if not root.is_dir():
        raise ValueError(f'Thư mục không tồn tại: {directory_path}')

    # Map video_id to database title and channel if available
    db_info: dict[str, dict[str, str]] = {}
    if db_path and Path(db_path).is_file():
        try:
            with open_database(db_path) as db:
                rows = db.execute(
                    'SELECT id, title, channel_name FROM videos'
                ).fetchall()
                for r in rows:
                    db_info[r['id']] = {
                        'title': r['title'] or '',
                        'channel_name': r['channel_name'] or '',
                    }
        except Exception:
            pass

    supported_suffixes = {'.webm', '.m4a', '.mp3', '.opus', '.ogg', '.wav', '.flac', '.aac'}
    items = []
    compatible_count = 0
    incompatible_count = 0
    has_video_id_count = 0

    # Sort files naturally
    for file in sorted(root.iterdir(), key=lambda f: f.name.lower()):
        if not file.is_file() or file.name.startswith('.'):
            continue
        suffix = file.suffix.lower()
        if suffix not in supported_suffixes:
            continue

        size = file.stat().st_size
        if size <= 0:
            continue

        raw_stem = file.stem
        # Detect video ID in brackets [xyz...]
        video_id_match = re.search(r'\[([A-Za-z0-9_-]{11})\]$', raw_stem)
        video_id = video_id_match.group(1) if video_id_match else None
        if video_id:
            has_video_id_count += 1

        db_entry = db_info.get(video_id) if video_id else None
        fallback_artist = db_entry['channel_name'] if db_entry else ''
        if fallback_artist:
            fallback_artist = re.sub(r'\s*-\s*Topic\s*$', '', fallback_artist, flags=re.IGNORECASE).strip()

        # Calculate suggested clean name
        cleaned_stem = clean_title(raw_stem, strip_video_id=True, clean_youtube_tags=True)
        artist, title = parse_artist_title(cleaned_stem, fallback_artist)

        apple_ok = is_apple_music_compatible(suffix)
        if apple_ok:
            compatible_count += 1
        else:
            incompatible_count += 1

        items.append({
            'source_path': str(file),
            'filename': file.name,
            'raw_stem': raw_stem,
            'suffix': suffix,
            'size': size,
            'video_id': video_id,
            'cleaned_stem': cleaned_stem,
            'artist': artist,
            'title': title,
            'is_apple_compatible': apple_ok,
            'suggested_apple_filename': f'{cleaned_stem}.m4a',
        })

    return {
        'directory': str(root),
        'total': len(items),
        'compatible_count': compatible_count,
        'incompatible_count': incompatible_count,
        'has_video_id_count': has_video_id_count,
        'items': items,
    }


def convert_audio_file(
    source_path: str | Path,
    target_path: str | Path,
    *,
    format_type: str = 'm4a_alac',
    artist: str = '',
    title: str = '',
    album: str = 'Auralytica',
) -> None:
    """Convert an audio file using ffmpeg with metadata."""
    source = Path(source_path)
    target = Path(target_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    # Base ffmpeg command
    cmd = ['ffmpeg', '-y', '-i', str(source), '-vn']

    if format_type == 'm4a_alac':
        cmd.extend(['-c:a', 'alac'])
    elif format_type == 'm4a_aac':
        cmd.extend(['-c:a', 'aac', '-b:a', '256k'])
    elif format_type == 'mp3':
        cmd.extend(['-c:a', 'libmp3lame', '-b:a', '320k'])
    else:
        # Default to alac
        cmd.extend(['-c:a', 'alac'])

    # Metadata flags
    if title:
        cmd.extend(['-metadata', f'title={title}'])
    if artist:
        cmd.extend(['-metadata', f'artist={artist}'])
    if album:
        cmd.extend(['-metadata', f'album={album}'])

    cmd.append(str(target))

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode != 0:
        err = res.stderr.decode('utf-8', errors='ignore')
        raise RuntimeError(f'Lỗi ffmpeg (exit {res.returncode}): {err[-500:]}')

    if not target.is_file() or target.stat().st_size <= 0:
        raise RuntimeError('File đầu ra không hợp lệ hoặc rỗng.')


class ConversionManager:
    """Background conversion coordinator."""

    def __init__(self):
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop_requested = False
        self._status = {
            'state': 'idle',  # 'idle' | 'running' | 'completed' | 'paused' | 'failed'
            'format': 'm4a_alac',
            'output_dir': '',
            'total': 0,
            'completed': 0,
            'failed': 0,
            'current_file': '',
            'items': [],
            'error': None,
            'started_at': None,
            'finished_at': None,
        }

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._status)

    def stop(self) -> dict[str, Any]:
        with self._lock:
            if self._status['state'] == 'running':
                self._stop_requested = True
        return self.get_status()

    def start_conversion(
        self,
        items: list[dict[str, Any]],
        output_dir: str | Path,
        *,
        format_type: str = 'm4a_alac',
        remove_source: bool = False,
    ) -> dict[str, Any]:
        with self._lock:
            if self._status['state'] == 'running':
                raise RuntimeError('Một tiến trình chuyển đổi đang chạy.')

            self._stop_requested = False
            out_path = Path(output_dir).expanduser().resolve()
            out_path.mkdir(parents=True, exist_ok=True)

            self._status = {
                'state': 'running',
                'format': format_type,
                'output_dir': str(out_path),
                'total': len(items),
                'completed': 0,
                'failed': 0,
                'current_file': '',
                'items': [],
                'error': None,
                'started_at': time.time(),
                'finished_at': None,
            }

            self._thread = threading.Thread(
                target=self._run_conversion,
                args=(items, out_path, format_type, remove_source),
                daemon=True,
            )
            self._thread.start()

        return self.get_status()

    def _run_conversion(
        self,
        items: list[dict[str, Any]],
        output_dir: Path,
        format_type: str,
        remove_source: bool,
    ) -> None:
        target_ext = '.mp3' if format_type == 'mp3' else '.m4a'
        used_names: set[str] = set()

        for item in items:
            with self._lock:
                if self._stop_requested:
                    self._status['state'] = 'paused'
                    self._status['finished_at'] = time.time()
                    return

            source_file = Path(item['source_path'])
            cleaned_stem = item.get('cleaned_stem') or clean_title(source_file.stem)
            artist = item.get('artist', '')
            title = item.get('title', '') or cleaned_stem

            # Ensure unique filename in target directory
            stem_candidate = cleaned_stem
            num = 0
            while True:
                filename = (stem_candidate + (f' ({num})' if num else '')) + target_ext
                if filename.lower() not in used_names and not (output_dir / filename).exists():
                    used_names.add(filename.lower())
                    target_path = output_dir / filename
                    break
                num += 1

            with self._lock:
                self._status['current_file'] = source_file.name

            try:
                convert_audio_file(
                    source_file,
                    target_path,
                    format_type=format_type,
                    artist=artist,
                    title=title,
                )

                if remove_source and target_path != source_file:
                    try:
                        source_file.unlink()
                    except OSError:
                        pass

                with self._lock:
                    self._status['completed'] += 1
                    self._status['items'].append({
                        'source': str(source_file),
                        'target': str(target_path),
                        'status': 'completed',
                        'error': None,
                    })
            except Exception as exc:
                with self._lock:
                    self._status['failed'] += 1
                    self._status['items'].append({
                        'source': str(source_file),
                        'target': str(target_path),
                        'status': 'failed',
                        'error': str(exc),
                    })

        with self._lock:
            self._status['state'] = 'completed'
            self._status['current_file'] = ''
            self._status['finished_at'] = time.time()


def rename_files_in_place(
    file_renames: list[tuple[str, str]],
) -> list[dict[str, Any]]:
    """Rename files in place according to requested cleaned names."""
    results = []
    for source_path_str, new_name in file_renames:
        source = Path(source_path_str)
        if not source.is_file():
            results.append({
                'source': source_path_str,
                'status': 'error',
                'error': 'File không tồn tại.',
            })
            continue

        parent = source.parent
        suffix = source.suffix
        cleaned_stem = clean_title(new_name, strip_video_id=True, clean_youtube_tags=True)
        target_name = cleaned_stem + suffix
        target = parent / target_name

        if target == source:
            results.append({
                'source': source_path_str,
                'target': str(target),
                'status': 'skipped',
                'error': None,
            })
            continue

        # Prevent collision
        num = 0
        while target.exists() and target != source:
            num += 1
            target = parent / f'{cleaned_stem} ({num}){suffix}'

        try:
            source.rename(target)
            results.append({
                'source': source_path_str,
                'target': str(target),
                'status': 'renamed',
                'error': None,
            })
        except OSError as exc:
            results.append({
                'source': source_path_str,
                'status': 'error',
                'error': str(exc),
            })

    return results


# Global singleton manager
conversion_manager = ConversionManager()
