---
phase: implementation
title: Implementation Guide
description: Technical implementation notes, patterns, and code guidelines for Quick YouTube Download workspace with inline metadata editor
---

# Implementation Guide: Quick YouTube Download (Tải Nhanh)

## Architecture Overview

The Direct YouTube Download feature was evolved from a step inside Takeout Studio into an independent, parallel top-level workspace called **Tải nhanh (Quick Download)**:
1. **Takeout Studio (`takeout`)**: Steps 01 Import, 02 Explore, 03 Deduplicate, 04 Download for large Google Takeout watch history.
2. **Tải nhanh (`quick_download`)**: Instant URL analysis for individual videos or playlists with inline metadata editing (Title, Artist), clean naming, output formatting, concurrency control, and batch monitoring.
3. **Music Player (`player`)**: Spotify-styled local player with synchronized lyrics and metadata inspector.

## Code Structure & Key Changes

### 1. Backend (`src/auralytica/`)
- `downloader.py`:
  - `parse_youtube_url(url: str) -> dict`: Parses watch (`/watch?v=`), short (`youtu.be/`), Shorts (`/shorts/`), embed (`/embed/`), bare 11-char ID, and playlist (`list=PL...`) URLs; strips tracking query parameters (`&si=`, `&t=`).
  - `_fetch_single_video_info(vid: str) -> dict`: Uses `yt_dlp` with `extract_flat=True` concurrently via `ThreadPoolExecutor` to fetch genuine title, channel, duration, and thumbnail without downloading media.
  - `resolve_direct_urls(urls: list[str]) -> dict`: Concurrently resolves individual videos and flattens playlists. Returns deduplicated list of items (`video_id`, `title`, `artist`, `channel`, `duration`, `thumbnail_url`) and invalid URLs.
  - `create_direct_batch(...) -> int`:
    - Normalizes format aliases (`mp3_320` / `mp3` -> `mp3`, `m4a_alac` / `alac` -> `m4a_alac`, `m4a_aac` / `aac` -> `m4a_aac`).
    - Sets `batch_is_direct:{batch_id} = '1'`, `batch_concurrency:{batch_id}`, `batch_clean_names = '1'`, `batch_embed_metadata = '1'`.
    - Inserts user-edited `title` and `artist` into `videos` table and creates `download_batches` / `download_items`.
  - `run_batch(...)`:
    - Reads `is_direct = get_setting(db, f'batch_is_direct:{batch_id}') == '1'`.
    - When `is_direct` is true, prioritizes user-edited `title` and `artist` from `videos` table over `result` from `yt-dlp`.
    - Transcodes into selected audio format with embedded cover art and metadata.
    - Post-publish hook indexes the completed file into `player_track_cache` via `cache_single_track`.
- `converter.py`:
  - Normalized format strings and mapped `mp3_320` to `mp3`.
- `web.py`:
  - Endpoints:
    - `POST /api/download/direct/resolve`: Accepts `DirectDownloadResolveRequest(urls=...)` and returns resolved metadata.
    - `POST /api/download/direct`: Accepts `DirectDownloadSubmitRequest(videos=..., output_dir=..., format=..., concurrency=...)` and starts batch download.

### 2. Frontend (`frontend/src/`)
- `components/AppShell.tsx`:
  - AppMode expanded to `'takeout' | 'quick_download' | 'player'`.
  - Navigation bar has top-level mode switcher: `[Takeout Studio] [⚡ Tải nhanh] [Music Player]`.
  - Takeout Studio steps remain clean: `01 Import`, `02 Explore`, `03 Deduplicate`, `04 Download`.
- `features/download/QuickDownloadView.tsx`:
  - Multi-line textarea for pasting URLs with one-click clipboard paste.
  - Resolved tracks list with **inline metadata editor**: editable Title and Artist text inputs, one-click `Wand2` button to clean YouTube tags, planned filename preview (`📁 Artist - Title.ext`), remove button, external link.
  - Download options card reused from `DownloadView`: output folder, Lossless ALAC (M4A) vs MP3 (320 kbps) vs AAC (256 kbps), concurrency slider (1x - 8x).
  - Batch monitor reused from `DownloadView`: live progress bar, status filter tabs (`all`, `failed`, `running`, `queued`, `completed`), Pause/Resume, Retry/Skip failed items, individual item error labels, and "Mở trong Player nghe ngay" shortcut.
- `App.tsx`:
  - Added routing for `/quick-download` and wired `QuickDownloadView`.

## Verification & Test Results
- Backend unit & API tests:
  - `tests/test_direct_download.py` (6 passed in 2.12s)
  - `tests/test_downloader.py` (16 passed in 1.01s)
  - Full backend suite `tests/test_*.py` (151 passed in 9.47s)
- Browser acceptance tests:
  - `tests/browser/test_direct_download_ui.py` (passed in 2.13s)
  - `tests/browser/test_player_ui.py` (2 passed)
  - `tests/browser/test_session_management_ui.py` (1 passed)
- Frontend build:
  - `npm run build` cleanly compiled Vite bundle without errors in 1.68s.
