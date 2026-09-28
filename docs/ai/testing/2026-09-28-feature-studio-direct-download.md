---
phase: testing
title: Test Plan & Scenarios
description: Test strategy, scenarios, fixtures, and coverage for Direct YouTube Download in Takeout Studio
---

# Test Plan: Direct YouTube Download in Takeout Studio

## Test Scenarios

### Backend Unit & Integration Tests
- [x] `test_resolve_direct_urls_standard_watch`: Single watch URL resolves video ID and cleans tracking query params (`&si=`, `&t=`).
- [x] `test_resolve_direct_urls_short_and_shorts`: Short link (`youtu.be/ID`) and shorts link (`/shorts/ID`) parse correctly.
- [x] `test_resolve_direct_urls_playlist`: Playlist URL invokes yt-dlp flat-playlist extraction and returns all entries.
- [x] `test_resolve_direct_urls_invalid`: Invalid or non-YouTube URLs are captured in `invalid_urls` list.
- [x] `test_submit_direct_download_batch_creation`: `POST /api/download/direct` creates batch in `download_batches` with label `direct_url` and inserts items into `download_items`.
- [x] `test_direct_download_auto_indexes_player_cache`: Completing an item registers track in `player_track_cache` with accurate metadata.

### Frontend Browser Tests (Playwright)
- [x] `test_direct_download_navigation`: Step `05 Direct` is visible and accessible in Studio header regardless of Takeout import state.
- [x] `test_direct_download_paste_and_resolve`: Pasting multiple YouTube links resolves and displays preview cards with count and titles.
- [x] `test_direct_download_submit_and_track`: Submitting creates a batch, updates progress bar, displays item status, and allows navigation to Player.

## Verification Evidence & Targets
- 100% pass on all new backend tests in `tests/test_direct_download.py` (5 passed).
- 100% pass on Playwright browser tests in `tests/browser/test_direct_download_ui.py` (1 passed).
- Full regression suite across unit and browser tests: 154 passed in 13.91s.
- Clean Vite frontend production build (`npm run build` in 1.20s).
- Visual verification screenshots captured:
  - `artifacts/browser-runs/direct-download-view-verified.png`
  - `artifacts/browser-runs/direct-download-verified.png`
