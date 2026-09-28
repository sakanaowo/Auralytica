---
phase: implementation
title: Implementation Guide
description: Technical implementation notes, patterns, and code guidelines for Direct YouTube Download in Takeout Studio
---

# Implementation Guide: Direct YouTube Download in Takeout Studio

## Code Structure & Changes

### 1. Backend (`src/auralytica/`)
- `downloader.py`:
  - `parse_youtube_url(url: str) -> dict`: Parses watch (`/watch?v=`), short (`youtu.be/`), Shorts (`/shorts/`), embed (`/embed/`), bare 11-char ID, and playlist (`list=PL...`) URLs; strips tracking query parameters (`&si=`, `&t=`).
  - `resolve_direct_urls(urls: list[str]) -> dict`: Resolves single videos and flattens playlists using `yt_dlp.YoutubeDL(extract_flat=True)`. Returns deduplicated list of valid items (`video_id`, `title`, `channel_name`, `duration`, `thumbnail`) and invalid URLs list.
  - `start_batch_worker(database, batch_id)`: Helper to spawn background thread executing `process_batch`.
  - `create_direct_batch(db, videos, output_dir, audio_format, launcher, database_path) -> dict`: Registers videos into `videos` table (`channel_name`, `user_group='music'`), writes settings (`batch_format`, `batch_clean_names`, `batch_embed_metadata`), registers batch in `download_batches`, inserts items into `download_items`, and spawns the background worker.
  - Post-publish hook in `_publish`: Triggers `cache_single_track(tdb, str(final))` after file publish to automatically index downloaded track into `player_track_cache`.
- `player.py`:
  - `cache_single_track(db, file_path: str)`: Calls `_extract_track_metadata(Path(file_path))` and updates/inserts `player_track_cache` row immediately.
- `web.py`:
  - Models: `DirectDownloadResolveRequest`, `DirectVideoItem`, `DirectDownloadSubmitRequest`.
  - Endpoints:
    - `POST /api/download/direct/resolve`: Resolves input URLs to metadata items.
    - `POST /api/download/direct`: Creates and triggers the direct download batch.

### 2. Frontend (`frontend/src/`)
- `api/types.ts`:
  - Added types `DirectVideoItem`, `DirectDownloadResolveRequest`, `DirectDownloadResolveResponse`, `DirectDownloadSubmitRequest`.
- `api/client.ts`:
  - Added methods `api.resolveDirectUrls(...)` and `api.submitDirectDownload(...)`.
- `components/AppShell.tsx`:
  - Added `direct` to `StudioStep` and added `{ key: 'direct', label: 'Direct', num: '05' }` navigation item.
- `features/download/DirectDownloadView.tsx`:
  - Hero header with step indicator and explanation.
  - Multi-line textarea for pasting URLs with fast clipboard paste button.
  - Resolved items preview grid with thumbnail, title, channel, duration, external YouTube link, and individual remove button.
  - Audio format selector (Lossless ALAC M4A vs MP3 320 kbps) and custom destination folder.
  - Live batch progress monitor with real-time poll, item breakdown, and instant button to switch to Music Player.
- `App.tsx`:
  - Wired `DirectDownloadView` for `currentStep === 'direct'`.
  - Allowed direct download access even when no Google Takeout archive has been imported yet.

## Testing & Verification Evidence
- Backend Tests: `tests/test_direct_download.py` (5 tests passing).
- Browser Acceptance Tests: `tests/browser/test_direct_download_ui.py` (Playwright Chromium test passing).
  - Navigating to step 05 without Takeout import.
  - URL input & analysis resolution.
  - Preview card rendering.
  - Audio format selection and batch submission.
  - Active batch progress monitor and transition to Music Player.
- Screenshots saved:
  - `artifacts/browser-runs/direct-download-view-verified.png`
  - `artifacts/browser-runs/direct-download-verified.png`
- Full regression suite: 154 passed.
