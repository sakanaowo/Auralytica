"""Local media player engine for Auralytica.

Handles local audio scanning, mutagen metadata tag read/write,
audio streaming with byte ranges (HTTP 206), embedded cover art,
playlists, favorites, and M3U/M3U8 import/export.
"""

from collections.abc import Generator
from datetime import datetime, timezone
import hashlib
import io
import json
import logging
import mimetypes
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import tempfile
from typing import Any
import urllib.parse
import urllib.request

import mutagen
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TCON, TDRC, APIC, ID3NoHeaderError
from mutagen.mp4 import MP4, MP4Cover
from mutagen.flac import FLAC, Picture
from mutagen.oggopus import OggOpus
from starlette.responses import StreamingResponse, Response

from .storage import transaction
from .converter import clean_title, parse_artist_title

AUDIO_EXTENSIONS = {'.m4a', '.mp3', '.flac', '.opus', '.webm', '.wav', '.ogg', '.aac'}

AUDIO_MIME_TYPES = {
    '.mp3': 'audio/mpeg',
    '.m4a': 'audio/mp4',
    '.aac': 'audio/aac',
    '.flac': 'audio/flac',
    '.opus': 'audio/ogg; codecs=opus',
    '.ogg': 'audio/ogg',
    '.wav': 'audio/wav',
    '.webm': 'audio/webm',
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_safe_path(base_dir: str | Path, target_path: str | Path) -> bool:
    """Ensure target_path resolves strictly within base_dir."""
    try:
        base = Path(base_dir).expanduser().resolve()
        target = Path(target_path).expanduser().resolve()
        return target.is_relative_to(base)
    except (OSError, ValueError):
        return False


# ---------------------------------------------------------------------------
# Library Scanner & Cache
# ---------------------------------------------------------------------------

def _extract_track_metadata(path: Path) -> dict[str, Any]:
    """Extract metadata tags and duration using mutagen with fallback to filename."""
    stat = path.stat()
    stem = path.stem
    ext = path.suffix.lower()

    title = ""
    artist = ""
    album = ""
    genre = ""
    year = ""
    duration = 0.0
    has_art = False

    try:
        try:
            audio = mutagen.File(str(path))
        except Exception:
            audio = None
        if audio is None and ext == '.mp3':
            try:
                audio = ID3(str(path))
            except Exception:
                audio = None

        if audio is not None:
            if hasattr(audio, 'info') and hasattr(audio.info, 'length'):
                duration = float(audio.info.length or 0.0)

            tags = audio if isinstance(audio, ID3) else getattr(audio, 'tags', None)
            if tags:
                # MP3 (ID3)
                if isinstance(tags, ID3) or hasattr(tags, 'getall'):
                    if 'TIT2' in tags:
                        title = str(tags['TIT2'].text[0]) if tags['TIT2'].text else ""
                    if 'TPE1' in tags:
                        artist = str(tags['TPE1'].text[0]) if tags['TPE1'].text else ""
                    if 'TALB' in tags:
                        album = str(tags['TALB'].text[0]) if tags['TALB'].text else ""
                    if 'TCON' in tags:
                        genre = str(tags['TCON'].text[0]) if tags['TCON'].text else ""
                    if 'TDRC' in tags:
                        year = str(tags['TDRC'].text[0]) if tags['TDRC'].text else ""
                    has_art = bool(tags.getall('APIC'))
                # MP4 / M4A
                elif hasattr(tags, 'get'):
                    def _get_mp4(key):
                        val = tags.get(key)
                        if isinstance(val, (list, tuple)) and val:
                            return str(val[0])
                        return str(val) if val else ""

                    title = _get_mp4('\xa9nam')
                    artist = _get_mp4('\xa9ART') or _get_mp4('aART')
                    album = _get_mp4('\xa9alb')
                    genre = _get_mp4('\xa9gen')
                    year = _get_mp4('\xa9day')
                    has_art = bool(tags.get('covr'))
                # FLAC / OGG / Opus
                if isinstance(audio, FLAC):
                    has_art = bool(audio.pictures)
    except Exception:
        pass

    # Fallback to parsed stem if title or artist is empty
    if not title or not artist:
        cleaned = clean_title(stem, strip_video_id=True, clean_youtube_tags=True)
        p_artist, p_title = parse_artist_title(cleaned, "")
        if not title:
            title = p_title or cleaned or stem
        if not artist and p_artist:
            artist = p_artist

    return {
        'path': str(path.resolve()),
        'filename': path.name,
        'title': title or stem,
        'artist': artist or 'Unknown Artist',
        'album': album or '',
        'genre': genre or '',
        'year': str(year)[:4] if year else '',
        'duration': round(duration, 2),
        'file_size': stat.st_size,
        'mtime_ns': stat.st_mtime_ns,
        'has_art': int(has_art),
        'has_cover_art': bool(has_art),
    }


def scan_library(db: sqlite3.Connection, folder: str | Path) -> list[dict[str, Any]]:
    """Scan folder recursively and return cached or newly indexed audio tracks."""
    root = Path(folder).expanduser().resolve()
    if not root.is_dir():
        return []

    # 1. Load existing cache for fast comparison
    cached_rows = db.execute("SELECT * FROM player_track_cache").fetchall()
    cache_by_path = {r['track_path']: dict(r) for r in cached_rows}

    # 2. Load favorites
    fav_rows = db.execute("SELECT track_path FROM player_favorites").fetchall()
    favorites = {r['track_path'] for r in fav_rows}

    results: list[dict[str, Any]] = []
    to_insert: list[dict[str, Any]] = []

    try:
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in AUDIO_EXTENSIONS:
                    full_path = Path(dirpath) / f
                    try:
                        st = full_path.stat()
                        if st.st_size <= 0:
                            continue
                    except OSError:
                        continue

                    str_path = str(full_path.resolve())
                    cached = cache_by_path.get(str_path)

                    if cached and cached['mtime_ns'] == st.st_mtime_ns and cached['file_size'] == st.st_size:
                        track_info = {
                            'path': str_path,
                            'filename': cached['file_name'],
                            'title': cached['title'],
                            'artist': cached['artist'],
                            'album': cached['album'],
                            'genre': cached['genre'],
                            'year': cached['year'],
                            'duration': cached['duration'],
                            'file_size': cached['file_size'],
                            'mtime_ns': cached['mtime_ns'],
                            'has_cover_art': bool(cached['has_art']),
                            'is_favorite': str_path in favorites,
                        }
                    else:
                        meta = _extract_track_metadata(full_path)
                        to_insert.append(meta)
                        track_info = {
                            'path': str_path,
                            'filename': meta['filename'],
                            'title': meta['title'],
                            'artist': meta['artist'],
                            'album': meta['album'],
                            'genre': meta['genre'],
                            'year': meta['year'],
                            'duration': meta['duration'],
                            'file_size': meta['file_size'],
                            'mtime_ns': meta['mtime_ns'],
                            'has_cover_art': bool(meta['has_art']),
                            'is_favorite': str_path in favorites,
                        }
                    results.append(track_info)
    except OSError:
        pass

    # Batch save new / updated cache entries
    if to_insert:
        now = _now_iso()
        with transaction(db):
            for m in to_insert:
                db.execute(
                    "INSERT INTO player_track_cache "
                    "(track_path, file_name, title, artist, album, genre, year, duration, file_size, mtime_ns, has_art, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(track_path) DO UPDATE SET "
                    "file_name=excluded.file_name, title=excluded.title, artist=excluded.artist, "
                    "album=excluded.album, genre=excluded.genre, year=excluded.year, "
                    "duration=excluded.duration, file_size=excluded.file_size, mtime_ns=excluded.mtime_ns, "
                    "has_art=excluded.has_art, updated_at=excluded.updated_at",
                    (
                        m['path'], m['filename'], m['title'], m['artist'], m['album'],
                        m['genre'], m['year'], m['duration'], m['file_size'], m['mtime_ns'],
                        m['has_art'], now,
                    )
                )

    results.sort(key=lambda t: (t['artist'].lower(), t['title'].lower()))
    return results


# ---------------------------------------------------------------------------
# Cover Art Extraction & Physical Tag Writing
# ---------------------------------------------------------------------------

def extract_cover_art(file_path: str | Path) -> tuple[bytes, str] | None:
    """Extract embedded cover image binary and MIME type from audio file."""
    path = Path(file_path).expanduser().resolve()
    if not path.is_file():
        return None

    try:
        try:
            audio = mutagen.File(str(path))
        except Exception:
            audio = None
        if audio is None and path.suffix.lower() == '.mp3':
            try:
                audio = ID3(str(path))
            except Exception:
                audio = None

        if audio is None:
            return None

        # MP3 ID3
        tags = audio if isinstance(audio, ID3) else getattr(audio, 'tags', None)
        if tags and (isinstance(tags, ID3) or hasattr(tags, 'getall')):
            apics = tags.getall('APIC')
            if apics:
                apic = apics[0]
                mime = apic.mime or 'image/jpeg'
                return apic.data, mime

        # MP4 / M4A
        if hasattr(audio.tags, 'get'):
            covers = audio.tags.get('covr')
            if covers:
                cov = covers[0]
                mime = 'image/png' if getattr(cov, 'imageformat', None) == MP4Cover.FORMAT_PNG else 'image/jpeg'
                return bytes(cov), mime

        # FLAC
        if isinstance(audio, FLAC) and audio.pictures:
            pic = audio.pictures[0]
            return pic.data, pic.mime or 'image/jpeg'

    except Exception:
        pass
    return None


def save_track_metadata(
    db: sqlite3.Connection,
    file_path: str | Path,
    title: str,
    artist: str,
    album: str = "",
    genre: str = "",
    year: str = "",
    cover_bytes: bytes | None = None,
    cover_mime: str | None = None,
    rename_file: bool = False,
) -> dict[str, Any]:
    """Write tags and cover art directly to physical audio file and update cache."""
    path = Path(file_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Tệp không tồn tại: {file_path}")

    ext = path.suffix.lower()

    # 1. Update tags based on file format
    try:
        if ext == '.mp3':
            try:
                tags = ID3(str(path))
            except ID3NoHeaderError:
                tags = ID3()
            tags.setall('TIT2', [TIT2(encoding=3, text=title)])
            tags.setall('TPE1', [TPE1(encoding=3, text=artist)])
            tags.setall('TALB', [TALB(encoding=3, text=album)])
            tags.setall('TCON', [TCON(encoding=3, text=genre)])
            if year:
                tags.setall('TDRC', [TDRC(encoding=3, text=str(year))])
            if cover_bytes:
                mime = cover_mime or 'image/jpeg'
                tags.setall('APIC', [APIC(encoding=3, mime=mime, type=3, desc='Cover', data=cover_bytes)])
            tags.save(str(path))

        elif ext in {'.m4a', '.mp4'}:
            tags = MP4(str(path))
            tags['\xa9nam'] = [title]
            tags['\xa9ART'] = [artist]
            tags['\xa9alb'] = [album]
            tags['\xa9gen'] = [genre]
            if year:
                tags['\xa9day'] = [str(year)]
            if cover_bytes:
                img_fmt = MP4Cover.FORMAT_PNG if (cover_mime and 'png' in cover_mime) else MP4Cover.FORMAT_JPEG
                tags['covr'] = [MP4Cover(cover_bytes, imageformat=img_fmt)]
            tags.save()

        elif ext == '.flac':
            audio = FLAC(str(path))
            audio['title'] = [title]
            audio['artist'] = [artist]
            audio['album'] = [album]
            audio['genre'] = [genre]
            if year:
                audio['date'] = [str(year)]
            if cover_bytes:
                pic = Picture()
                pic.data = cover_bytes
                pic.type = 3
                pic.mime = cover_mime or 'image/jpeg'
                audio.clear_pictures()
                audio.add_picture(pic)
            audio.save()

        elif ext in {'.opus', '.ogg'}:
            audio = OggOpus(str(path))
            audio['title'] = [title]
            audio['artist'] = [artist]
            audio['album'] = [album]
            audio['genre'] = [genre]
            if year:
                audio['date'] = [str(year)]
            audio.save()
    except Exception as exc:
        raise RuntimeError(f"Lỗi ghi tag vật lý: {exc}") from exc

    # 2. Optional file rename
    final_path = path
    if rename_file and title and artist:
        clean_stem = f"{artist} - {title}"
        sanitized = re.sub(r'[/\\:*?\"<>|]', '', clean_stem).strip(' .')[:120]
        new_name = f"{sanitized}{ext}"
        new_path = path.parent / new_name
        if new_path != path and not new_path.exists():
            path.rename(new_path)
            final_path = new_path

    # 3. Update DB cache
    meta = _extract_track_metadata(final_path)
    now = _now_iso()
    with transaction(db):
        if str(final_path.resolve()) != str(path.resolve()):
            db.execute("DELETE FROM player_track_cache WHERE track_path=?", (str(path.resolve()),))
            db.execute("UPDATE player_playlist_tracks SET track_path=? WHERE track_path=?", (str(final_path.resolve()), str(path.resolve())))
            db.execute("UPDATE player_favorites SET track_path=? WHERE track_path=?", (str(final_path.resolve()), str(path.resolve())))
            db.execute("UPDATE player_lyrics_cache SET track_path=? WHERE track_path=?", (str(final_path.resolve()), str(path.resolve())))

        db.execute(
            "INSERT INTO player_track_cache "
            "(track_path, file_name, title, artist, album, genre, year, duration, file_size, mtime_ns, has_art, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(track_path) DO UPDATE SET "
            "file_name=excluded.file_name, title=excluded.title, artist=excluded.artist, "
            "album=excluded.album, genre=excluded.genre, year=excluded.year, "
            "duration=excluded.duration, file_size=excluded.file_size, mtime_ns=excluded.mtime_ns, "
            "has_art=excluded.has_art, updated_at=excluded.updated_at",
            (
                meta['path'], meta['filename'], meta['title'], meta['artist'], meta['album'],
                meta['genre'], meta['year'], meta['duration'], meta['file_size'], meta['mtime_ns'],
                meta['has_art'], now,
            )
        )

    meta['has_cover_art'] = bool(meta.get('has_art'))
    fav_row = db.execute("SELECT 1 FROM player_favorites WHERE track_path=?", (str(final_path.resolve()),)).fetchone()
    meta['is_favorite'] = bool(fav_row)
    return meta


# ---------------------------------------------------------------------------
# Audio Streaming (HTTP 206 Byte Range)
# ---------------------------------------------------------------------------

def _file_chunk_generator(file_path: Path, start: int, length: int, chunk_size: int = 65536) -> Generator[bytes, None, None]:
    """Yield file chunks for Range requests."""
    with open(file_path, "rb") as f:
        f.seek(start)
        remaining = length
        while remaining > 0:
            read_size = min(chunk_size, remaining)
            data = f.read(read_size)
            if not data:
                break
            remaining -= len(data)
            yield data


def _is_alac(path: Path) -> bool:
    """Check if an audio file is encoded in ALAC (incompatible with HTML5 <audio> in Chromium)."""
    if path.suffix.lower() not in {'.m4a', '.mp4'}:
        return False
    try:
        f = mutagen.File(str(path))
        return bool(f and getattr(f.info, 'codec', None) == 'alac')
    except Exception:
        return False


def _get_transcoded_flac_path(path: Path) -> Path:
    """Transcode ALAC file to lossless FLAC in temp cache for native browser playback."""
    st = path.stat()
    cache_dir = Path(tempfile.gettempdir()) / "auralytica_transcode_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = hashlib.md5(f"{path.resolve()}:{st.st_mtime_ns}:{st.st_size}".encode()).hexdigest()
    flac_path = cache_dir / f"{key}.flac"
    if not flac_path.exists() or flac_path.stat().st_size == 0:
        tmp_target = cache_dir / f"{key}.tmp.flac"
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(path), "-c:a", "flac", str(tmp_target)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        tmp_target.rename(flac_path)
    return flac_path


def stream_audio_file(file_path: str | Path, range_header: str | None = None) -> Response:
    """Stream an audio file with full HTTP 206 Partial Content support."""
    path = Path(file_path).expanduser().resolve()
    if not path.is_file():
        return Response("File not found", status_code=404)

    # Transcode browser-incompatible codecs (e.g. ALAC) to lossless FLAC on the fly
    if _is_alac(path):
        try:
            path = _get_transcoded_flac_path(path)
        except Exception as exc:
            logging.warning("Failed to transcode ALAC to FLAC: %s", exc)

    file_size = path.stat().st_size
    content_type = AUDIO_MIME_TYPES.get(path.suffix.lower(), "application/octet-stream")

    if not range_header:
        def full_iter():
            with open(path, "rb") as f:
                while chunk := f.read(65536):
                    yield chunk
        return StreamingResponse(
            full_iter(),
            status_code=200,
            headers={
                "Content-Length": str(file_size),
                "Content-Type": content_type,
                "Accept-Ranges": "bytes",
            },
        )

    # Parse Range: bytes=start-end
    m = re.match(r"^bytes=(\d+)-(\d*)$", range_header.strip())
    if not m:
        return Response("Invalid Range Header", status_code=416, headers={"Content-Range": f"bytes */{file_size}"})

    start = int(m.group(1))
    end = int(m.group(2)) if m.group(2) else file_size - 1

    if start >= file_size or end >= file_size or start > end:
        return Response("Range Not Satisfiable", status_code=416, headers={"Content-Range": f"bytes */{file_size}"})

    content_length = end - start + 1
    return StreamingResponse(
        _file_chunk_generator(path, start, content_length),
        status_code=206,
        headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Content-Length": str(content_length),
            "Content-Type": content_type,
            "Accept-Ranges": "bytes",
        },
    )


# ---------------------------------------------------------------------------
# Playlists & Favorites Operations
# ---------------------------------------------------------------------------

def create_playlist(db: sqlite3.Connection, name: str, description: str = "") -> dict[str, Any]:
    name = (name or "").strip()
    if not name:
        raise ValueError("Tên danh sách phát không được để trống.")
    now = _now_iso()
    with transaction(db):
        cur = db.execute(
            "INSERT INTO player_playlists (name, description, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (name, description or "", now, now),
        )
        pid = cur.lastrowid
    return get_playlist(db, pid)


def get_playlist(db: sqlite3.Connection, playlist_id: int) -> dict[str, Any] | None:
    row = db.execute(
        "SELECT p.*, COUNT(t.track_path) AS track_count FROM player_playlists p "
        "LEFT JOIN player_playlist_tracks t ON t.playlist_id=p.id "
        "WHERE p.id=? GROUP BY p.id",
        (playlist_id,),
    ).fetchone()
    return dict(row) if row else None


def get_playlists(db: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = db.execute(
        "SELECT p.*, COUNT(t.track_path) AS track_count FROM player_playlists p "
        "LEFT JOIN player_playlist_tracks t ON t.playlist_id=p.id "
        "GROUP BY p.id ORDER BY p.updated_at DESC",
    ).fetchall()
    return [dict(r) for r in rows]


def update_playlist(db: sqlite3.Connection, playlist_id: int, name: str, description: str | None = None) -> dict[str, Any]:
    name = (name or "").strip()
    if not name:
        raise ValueError("Tên playlist không được để trống.")
    now = _now_iso()
    with transaction(db):
        if description is not None:
            db.execute("UPDATE player_playlists SET name=?, description=?, updated_at=? WHERE id=?", (name, description, now, playlist_id))
        else:
            db.execute("UPDATE player_playlists SET name=?, updated_at=? WHERE id=?", (name, now, playlist_id))
    return get_playlist(db, playlist_id)


def delete_playlist(db: sqlite3.Connection, playlist_id: int) -> None:
    with transaction(db):
        db.execute("DELETE FROM player_playlists WHERE id=?", (playlist_id,))


def get_playlist_tracks(db: sqlite3.Connection, playlist_id: int) -> list[dict[str, Any]]:
    rows = db.execute(
        "SELECT t.playlist_id, t.track_path, t.position, t.added_at, "
        "c.file_name, c.title, c.artist, c.album, c.genre, c.year, c.duration, c.has_art "
        "FROM player_playlist_tracks t "
        "LEFT JOIN player_track_cache c ON c.track_path=t.track_path "
        "WHERE t.playlist_id=? ORDER BY t.position ASC",
        (playlist_id,),
    ).fetchall()
    fav_rows = db.execute("SELECT track_path FROM player_favorites").fetchall()
    favorites = {r['track_path'] for r in fav_rows}

    results = []
    for r in rows:
        results.append({
            'track_path': r['track_path'],
            'position': r['position'],
            'added_at': r['added_at'],
            'title': r['title'] or Path(r['track_path']).stem,
            'artist': r['artist'] or 'Unknown Artist',
            'album': r['album'] or '',
            'duration': r['duration'] or 0.0,
            'has_cover_art': bool(r['has_art']),
            'is_favorite': r['track_path'] in favorites,
        })
    return results


def add_tracks_to_playlist(db: sqlite3.Connection, playlist_id: int, track_paths: list[str]) -> None:
    if not track_paths:
        return
    now = _now_iso()
    with transaction(db):
        max_pos = db.execute("SELECT COALESCE(MAX(position), -1) FROM player_playlist_tracks WHERE playlist_id=?", (playlist_id,)).fetchone()[0]
        for i, tp in enumerate(track_paths):
            pos = max_pos + 1 + i
            db.execute(
                "INSERT OR IGNORE INTO player_playlist_tracks (playlist_id, track_path, position, added_at) VALUES (?, ?, ?, ?)",
                (playlist_id, str(Path(tp).expanduser().resolve()), pos, now),
            )
        db.execute("UPDATE player_playlists SET updated_at=? WHERE id=?", (now, playlist_id))


def remove_track_from_playlist(db: sqlite3.Connection, playlist_id: int, track_path: str) -> None:
    resolved = str(Path(track_path).expanduser().resolve())
    now = _now_iso()
    with transaction(db):
        db.execute("DELETE FROM player_playlist_tracks WHERE playlist_id=? AND track_path=?", (playlist_id, resolved))
        db.execute("UPDATE player_playlists SET updated_at=? WHERE id=?", (now, playlist_id))


def reorder_playlist_tracks(db: sqlite3.Connection, playlist_id: int, ordered_paths: list[str]) -> None:
    now = _now_iso()
    with transaction(db):
        for pos, path_str in enumerate(ordered_paths):
            resolved = str(Path(path_str).expanduser().resolve())
            db.execute(
                "UPDATE player_playlist_tracks SET position=? WHERE playlist_id=? AND track_path=?",
                (pos, playlist_id, resolved),
            )
        db.execute("UPDATE player_playlists SET updated_at=? WHERE id=?", (now, playlist_id))


def toggle_favorite(db: sqlite3.Connection, track_path: str) -> bool:
    resolved = str(Path(track_path).expanduser().resolve())
    with transaction(db):
        exists = db.execute("SELECT 1 FROM player_favorites WHERE track_path=?", (resolved,)).fetchone()
        if exists:
            db.execute("DELETE FROM player_favorites WHERE track_path=?", (resolved,))
            return False
        else:
            db.execute("INSERT INTO player_favorites (track_path, added_at) VALUES (?, ?)", (resolved, _now_iso()))
            return True


def get_favorites(db: sqlite3.Connection) -> list[str]:
    rows = db.execute("SELECT track_path FROM player_favorites ORDER BY added_at DESC").fetchall()
    return [r['track_path'] for r in rows]


# ---------------------------------------------------------------------------
# M3U / M3U8 Export & Import
# ---------------------------------------------------------------------------

def export_m3u8(db: sqlite3.Connection, playlist_id: int) -> str:
    """Generate #EXTM3U playlist text."""
    tracks = get_playlist_tracks(db, playlist_id)
    lines = ["#EXTM3U"]
    for t in tracks:
        sec = int(t['duration'] or -1)
        artist = t['artist']
        title = t['title']
        lines.append(f"#EXTINF:{sec},{artist} - {title}")
        lines.append(t['track_path'])
    return "\n".join(lines) + "\n"


def import_m3u8(db: sqlite3.Connection, name: str, m3u_text: str, base_dir: Path | None = None) -> dict[str, Any]:
    """Parse #EXTM3U text and create a new playlist."""
    lines = m3u_text.splitlines()
    paths: list[str] = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        p = Path(line)
        if not p.is_absolute() and base_dir:
            p = base_dir / p
        paths.append(str(p.resolve()))

    pl = create_playlist(db, name, f"Imported from M3U at {_now_iso()}")
    if paths:
        add_tracks_to_playlist(db, pl['id'], paths)
    return get_playlist(db, pl['id'])


# ---------------------------------------------------------------------------
# Lyrics Retrieval & Management (LRCLIB, Embedded, .lrc sidecar)
# ---------------------------------------------------------------------------

def _clean_lrc_to_plain(text: str) -> str:
    lines = []
    for line in text.splitlines():
        cleaned = re.sub(r'\[\d{2}:\d{2}(?:\.\d{1,3})?\]\s*', '', line).strip()
        if cleaned:
            lines.append(cleaned)
    return "\n".join(lines)


def _check_sidecar_lrc(path: Path) -> tuple[str | None, str | None]:
    """Check for a .lrc sidecar file next to the audio file.
    Returns (plain_lyrics, synced_lyrics).
    """
    lrc_path = path.with_suffix('.lrc')
    if lrc_path.is_file():
        try:
            content = lrc_path.read_text(encoding='utf-8', errors='replace').strip()
            if content:
                if re.search(r'\[\d{2}:\d{2}', content):
                    plain = _clean_lrc_to_plain(content)
                    return plain or None, content
                return content, None
        except OSError:
            pass
    return None, None


def _extract_embedded_lyrics(path: Path) -> tuple[str | None, str | None]:
    """Check for embedded lyrics in audio tags.
    Returns (plain_lyrics, synced_lyrics).
    """
    ext = path.suffix.lower()
    plain: str | None = None
    synced: str | None = None

    try:
        if ext == '.mp3':
            try:
                tags = ID3(str(path))
            except Exception:
                tags = None
            if tags:
                for key, frame in tags.items():
                    if key.startswith('USLT'):
                        plain = str(frame.text) if hasattr(frame, 'text') else str(frame)
                        break
        elif ext in {'.m4a', '.mp4'}:
            tags = MP4(str(path))
            lyr = tags.get('\xa9lyr')
            if lyr:
                plain = str(lyr[0]) if isinstance(lyr, (list, tuple)) else str(lyr)
        elif ext in {'.flac', '.opus', '.ogg'}:
            audio = mutagen.File(str(path))
            if audio and hasattr(audio, 'get'):
                lyr = audio.get('lyrics') or audio.get('unsyncedlyrics') or audio.get('LYRICS')
                if lyr:
                    plain = str(lyr[0]) if isinstance(lyr, (list, tuple)) else str(lyr)
    except Exception:
        pass

    if plain and re.search(r'\[\d{2}:\d{2}', plain):
        synced = plain
        plain = _clean_lrc_to_plain(plain)

    return (plain or None), (synced or None)


def _fetch_lrclib_lyrics(title: str, artist: str, duration: float | None = None) -> dict[str, Any] | None:
    """Fetch lyrics from LRCLIB public API (https://lrclib.net)."""
    if not title:
        return None
    headers = {'User-Agent': 'Auralytica/1.0 (https://github.com/sakanaowo/Auralytica)'}

    # 1. Exact match via /api/get
    params = {'track_name': title}
    if artist and artist != 'Unknown Artist':
        params['artist_name'] = artist
    if duration and duration > 0:
        params['duration'] = int(round(duration))

    query_str = urllib.parse.urlencode(params)
    url = f"https://lrclib.net/api/get?{query_str}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=3.5) as res:
            if res.status == 200:
                data = json.loads(res.read().decode('utf-8'))
                return {
                    'plain_lyrics': data.get('plainLyrics'),
                    'synced_lyrics': data.get('syncedLyrics'),
                    'is_instrumental': bool(data.get('instrumental')),
                    'source': 'lrclib',
                }
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            logging.debug("LRCLIB /api/get HTTP error %s for %s", exc.code, title)
    except Exception as exc:
        logging.debug("LRCLIB /api/get error: %s", exc)

    # 2. Search fallback via /api/search
    search_q = f"{artist} {title}".strip() if artist and artist != 'Unknown Artist' else title
    search_url = f"https://lrclib.net/api/search?{urllib.parse.urlencode({'q': search_q})}"
    search_req = urllib.request.Request(search_url, headers=headers)
    try:
        with urllib.request.urlopen(search_req, timeout=3.5) as res:
            if res.status == 200:
                items = json.loads(res.read().decode('utf-8'))
                if isinstance(items, list) and len(items) > 0:
                    first = items[0]
                    return {
                        'plain_lyrics': first.get('plainLyrics'),
                        'synced_lyrics': first.get('syncedLyrics'),
                        'is_instrumental': bool(first.get('instrumental')),
                        'source': 'lrclib',
                    }
    except Exception as exc:
        logging.debug("LRCLIB /api/search error: %s", exc)

    return None


def _save_lyrics_to_cache(db: sqlite3.Connection, data: dict[str, Any]) -> None:
    now = _now_iso()
    with transaction(db):
        db.execute(
            "INSERT INTO player_lyrics_cache "
            "(track_path, plain_lyrics, synced_lyrics, is_instrumental, source, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(track_path) DO UPDATE SET "
            "plain_lyrics=excluded.plain_lyrics, synced_lyrics=excluded.synced_lyrics, "
            "is_instrumental=excluded.is_instrumental, source=excluded.source, updated_at=excluded.updated_at",
            (
                data['track_path'],
                data['plain_lyrics'],
                data['synced_lyrics'],
                1 if data.get('is_instrumental') else 0,
                data.get('source', 'unknown'),
                now,
            ),
        )


def get_lyrics(db: sqlite3.Connection, track_path: str, force_refresh: bool = False) -> dict[str, Any]:
    """Retrieve lyrics for a given track from cache, sidecar .lrc, embedded tags, or LRCLIB."""
    path = Path(track_path).expanduser().resolve()
    str_path = str(path)

    if not force_refresh:
        row = db.execute("SELECT * FROM player_lyrics_cache WHERE track_path=?", (str_path,)).fetchone()
        if row:
            return {
                'track_path': str_path,
                'plain_lyrics': row['plain_lyrics'],
                'synced_lyrics': row['synced_lyrics'],
                'is_instrumental': bool(row['is_instrumental']),
                'source': row['source'],
            }

    # 1. Sidecar .lrc
    sidecar_plain, sidecar_synced = _check_sidecar_lrc(path)
    if sidecar_plain or sidecar_synced:
        data = {
            'track_path': str_path,
            'plain_lyrics': sidecar_plain,
            'synced_lyrics': sidecar_synced,
            'is_instrumental': False,
            'source': 'file',
        }
        _save_lyrics_to_cache(db, data)
        return data

    # 2. Embedded tags
    emb_plain, emb_synced = _extract_embedded_lyrics(path)
    if emb_plain or emb_synced:
        data = {
            'track_path': str_path,
            'plain_lyrics': emb_plain,
            'synced_lyrics': emb_synced,
            'is_instrumental': False,
            'source': 'embedded',
        }
        _save_lyrics_to_cache(db, data)
        return data

    # 3. LRCLIB public API
    meta_row = db.execute("SELECT title, artist, duration FROM player_track_cache WHERE track_path=?", (str_path,)).fetchone()
    if meta_row:
        title = meta_row['title']
        artist = meta_row['artist']
        duration = float(meta_row['duration'] or 0)
    else:
        meta = _extract_track_metadata(path)
        title = meta['title']
        artist = meta['artist']
        duration = float(meta['duration'] or 0)

    lrclib_data = _fetch_lrclib_lyrics(title=title, artist=artist or '', duration=duration)
    if lrclib_data:
        data = {
            'track_path': str_path,
            'plain_lyrics': lrclib_data['plain_lyrics'],
            'synced_lyrics': lrclib_data['synced_lyrics'],
            'is_instrumental': lrclib_data['is_instrumental'],
            'source': lrclib_data['source'],
        }
        _save_lyrics_to_cache(db, data)
        return data

    # 4. Not found -> record empty in cache so we don't spam the network
    data = {
        'track_path': str_path,
        'plain_lyrics': None,
        'synced_lyrics': None,
        'is_instrumental': False,
        'source': 'not_found',
    }
    _save_lyrics_to_cache(db, data)
    return data


def save_lyrics(
    db: sqlite3.Connection,
    track_path: str,
    plain_lyrics: str | None = None,
    synced_lyrics: str | None = None,
    is_instrumental: bool = False,
) -> dict[str, Any]:
    """Manually update or override lyrics for a track."""
    path = str(Path(track_path).expanduser().resolve())
    data = {
        'track_path': path,
        'plain_lyrics': plain_lyrics,
        'synced_lyrics': synced_lyrics,
        'is_instrumental': is_instrumental,
        'source': 'manual',
    }
    _save_lyrics_to_cache(db, data)
    return data
