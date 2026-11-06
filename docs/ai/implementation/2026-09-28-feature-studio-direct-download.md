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
- `storage.py`:
  - Schema v7: `download_batches.kind` (`takeout` | `direct`) and `direct_download_items(batch_id, video_id, title, artist)`. Migration converts v6 `batch_is_direct:{id}` settings into `kind='direct'`, backfills tags from `videos`, then deletes those settings.
  - `review_locked(db)`: only queued/running **Takeout** batches lock review; `assert_review_unlocked` uses it.
- `batches.py`:
  - `get_batch` returns `kind`. `_active` renamed to `active_batch` (the single queued/running batch).
  - `create_batch` raises `BatchBusyError` when the active batch is a quick download instead of returning it as "reused".
- `downloader.py`:
  - `parse_youtube_url(url) -> dict | None`: watch, `youtu.be`, shorts, embed, bare 11-char ID, playlist. Tracking parameters are dropped because only the ID is kept.
  - `_fetch_single_video_info(vid, source) -> (video, unavailable)`: yt-dlp metadata without media; failures are classified with `_ytdlp.summarize_error`.
  - `resolve_direct_urls(urls) -> {videos, invalid_urls, unavailable, truncated}`: concurrent single-video lookups (max 8 threads), flat playlist expansion, playlist `[Private video]`/`[Deleted video]` entries go to `unavailable`, capped at `MAX_DIRECT_VIDEOS = 1000`.
  - `create_direct_batch(...) -> int`:
    - Raises `BatchBusyError` if any batch is queued/running (the worker runs one batch at a time).
    - Normalizes format aliases (`mp3_320` -> `mp3`, `alac` -> `m4a_alac`, `aac` -> `m4a_aac`).
    - Inserts `download_batches(kind='direct')`, per-batch settings (`batch_format`, `batch_concurrency` 1–8, `batch_clean_names=1`, `batch_embed_metadata=1`), `download_items` and `direct_download_items`.
    - Adds a `videos` row only when the ID is new (`ON CONFLICT DO NOTHING`, no `user_group`), so Takeout rows are never rewritten.
  - `run_batch(...)`: item title/artist come from `direct_download_items` when present; for `kind='direct'` the edited tags win over yt-dlp metadata for tags and file name. Completed files are indexed with `player.cache_single_track`.
- `download_controls.py`:
  - `batch_status` shows the edited title for quick-download items.
  - `skip_item` / `skip_failed` write `download_selections.keep=0` only for Takeout batches (`_exclude_from_takeout`).
- `importer.py`: `get_import_sessions` uses `review_locked`.
- `web.py`:
  - `GET /api/workflow` adds `download_busy`; `batch_locked` now means Takeout review lock only.
  - `DirectDownloadResolveRequest`: 1–500 URLs, each ≤ 2,048 chars.
  - `DirectDownloadSubmitRequest`: `video_id` must be 11 chars, 1–1,000 videos, `format` Literal, `concurrency` 1–8. Busy worker → 409.

### 2. Frontend (`frontend/src/`)
- `components/AppShell.tsx`: `AppMode = 'takeout' | 'quick_download' | 'player'`; Takeout steps stay `01`–`04`.
- `features/download/QuickDownloadView.tsx`:
  - Textarea + clipboard paste, Ctrl+Enter to analyze.
  - Inline Title/Artist editor, `Wand2` tag cleaner, planned file name preview, remove/open-link actions.
  - `#direct-resolve-report`: unavailable videos with reason, unrecognized lines, truncation notice.
  - Options: output folder, ALAC / MP3 320 / AAC 256, concurrency 1–8.
  - Start button disabled with "Đang có lượt tải chạy" while `downloadBusy`.
  - Batch monitor: progress, status filter, pause/resume, retry/skip failed, open Player.
- `features/download/DownloadView.tsx`: batch picker labels quick-download batches; Takeout start is disabled while any batch is active ("Đợi lượt Tải nhanh xong").
- `App.tsx`: `/quick-download` route, passes `workflow.download_busy` to `QuickDownloadView`.
- `api/types.ts`: `DirectUnavailableItem`, `unavailable`/`truncated` on resolve, `kind` on `DownloadBatch`, `download_busy` on `WorkflowState`.

## Known Limitations
See [design §7](../design/2026-09-28-feature-studio-direct-download.md#7-giới-hạn-đã-biết):
- One batch at a time, no queue: a new batch is refused until the running one finishes or is paused.
- A transient network error during resolve also lands the video in `unavailable`; re-analyze to retry.

## Verification & Test Results (2026-10-26)
- `uv run --no-sync python -m unittest discover -s tests` → **160 tests OK** (15 in `tests/test_direct_download.py`).
- `uv run --no-sync python -m unittest tests.browser.test_direct_download_ui tests.browser.test_player_ui tests.browser.test_session_management_ui` → **4 tests OK**.
- `tests/browser/test_ui.py` → 10 failures that predate this branch (selectors of the pre-React UI).
- `npm --prefix frontend run build` → clean build, no TypeScript errors.
