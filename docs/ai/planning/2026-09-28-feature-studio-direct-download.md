---
phase: planning
title: Implementation Plan
description: Task breakdown, sequencing, and verification criteria for Direct YouTube Download in Takeout Studio
---

# Implementation Plan: Direct YouTube Download in Takeout Studio

## Task Breakdown

- [x] **Task 1: Backend URL Extraction & Resolution (`downloader.py`, `web.py`)**
  - Implement regex URL parsing for watch, youtu.be, shorts, and playlist formats.
  - Implement `resolve_direct_urls` supporting flat playlist extraction via `yt-dlp`.
  - Add API endpoint `POST /api/download/direct/resolve`.
  - Verification: Unit test with mocked yt-dlp responses verifying video ID extraction, playlist expansion, and tracking param removal.

- [x] **Task 2: Backend Direct Batch Creation & Download Execution (`downloader.py`, `web.py`)**
  - Add API endpoint `POST /api/download/direct`.
  - Register new videos in `videos` table.
  - Create batch in `download_batches` with label `direct_url`.
  - Spawn download worker thread for direct batch items.
  - Verification: Unit test verifying batch creation, DB rows, and execution trigger.

- [x] **Task 3: Automatic Indexing into Player Cache (`downloader.py`, `player.py`)**
  - Add helper function `player.cache_single_downloaded_track(db, file_path)`.
  - Trigger track indexing on download item completion so files appear immediately in `/player`.
  - Verification: Unit test verifying that completing a download item populates `player_track_cache`.

- [x] **Task 4: Frontend API Client & Types (`api/types.ts`, `api/client.ts`)**
  - Add types: `DirectDownloadResolveRequest`, `DirectDownloadResolveResponse`, `DirectDownloadSubmitRequest`.
  - Add API methods: `api.resolveDirectUrls(...)`, `api.submitDirectDownload(...)`.
  - Verification: TypeScript build compiles cleanly.

- [x] **Task 5: Frontend Studio Navigation & Step 05 (`App.tsx`, `Header.tsx`)**
  - Extend `StudioStep` with `'direct'`.
  - Add step button `05 Direct` to `Header.tsx`.
  - Ensure step `05 Direct` is clickable even without an imported Takeout session.
  - Verification: Navigating to step 05 renders the view.

- [x] **Task 6: Frontend Direct Download View (`DirectDownloadView.tsx`)**
  - Implement textarea input with auto-formatting and paste from clipboard.
  - Implement URL preview drawer with thumbnail, title, and channel tags.
  - Implement audio format selection (Lossless ALAC vs MP3 320) and output directory selector.
  - Integrate live batch progress monitor with retry, skip, and "Nghe trong Player" button.
  - Verification: Manual UI verification and Playwright browser test.

- [x] **Task 7: Automated Tests & Validation (`tests/test_downloader.py`, `tests/browser/test_direct_download_ui.py`)**
  - Add backend integration tests for `/api/download/direct/resolve` and `/api/download/direct`.
  - Add Playwright browser test verifying pasting links, previewing, initiating download, and navigating to player.
  - Run full test suite (`uv run pytest`).
  - Production frontend build (`npm run build`).

- [x] **Task 8: Review & Documentation (`docs/ai/implementation/`, `dev-review`)**
  - Update implementation doc with evidence.
  - Run final code review and prepare commit.
