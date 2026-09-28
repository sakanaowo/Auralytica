---
phase: requirements
title: Requirements & Problem Understanding
description: Clarify the problem space, gather requirements, and define success criteria for Direct YouTube Link Download in Studio
---

# Requirements: Direct YouTube Download in Takeout Studio

## 1. Problem Statement
Currently, Auralytica's Takeout Studio strictly follows a 4-step linear pipeline (`01 Import` -> `02 Explore` -> `03 Deduplicate` -> `04 Download`) that requires importing an extracted Google Takeout folder containing `watch-history.json`.

When users discover new songs, music videos, or playlists on YouTube that they want to add to their offline high-fidelity library immediately, they cannot do so through the web interface without re-exporting an entire Google Takeout archive. Users need a direct, flexible way within Studio to paste one or multiple YouTube URLs and download high-quality audio directly to their local music library.

## 2. Goals & Non-Goals

### Goals
- Add a dedicated 5th step/tab in Takeout Studio: **`05 Direct Download` (Tải theo link)**.
- Provide a multi-line input (Textarea) accepting single or multiple YouTube links separated by newlines, spaces, or commas.
- Parse and validate YouTube URLs robustly:
  - Standard watch URLs (`https://www.youtube.com/watch?v=...`)
  - Shortened URLs (`https://youtu.be/...`)
  - YouTube Shorts (`https://www.youtube.com/shorts/...`)
  - YouTube Playlists (`https://www.youtube.com/playlist?list=...`) with automatic extraction of constituent video entries.
  - Sanitization of query strings (stripping tracking parameters like `&si=`, `&feature=`, `&t=`).
- Allow users to preview and inspect parsed URLs (Title/ID extraction or video counts) before initiating download.
- Output configuration:
  - Format selection: **Lossless ALAC M4A** (bit-perfect Opus extraction) vs **MP3 (320 kbps)**.
  - Output directory selection (defaulting to configured library path `~/Music/Auralytica`).
- Backend integration:
  - Backend endpoint `POST /api/download/direct` that registers the videos into the database and launches a dedicated `download_batches` task.
  - Leverage the multi-threaded download engine with mobile/web client fallbacks, retry logic, error classification, and skip controls.
  - Seamless auto-indexing: downloaded tracks are immediately registered in `player_track_cache` so they appear in `/player` without requiring a full library rescan.
- Real-time status & progress:
  - Monitor batch progress, item status, download speed, and errors directly in the view.

### Non-Goals
- Supporting non-YouTube streaming platforms (e.g. SoundCloud, Bilibili, Spotify) in this phase.
- Modifying the existing Google Takeout 4-step workflow (Steps 01-04 remain fully intact).

## 3. User Stories & Use Cases
1. **Single Video Download**: As a user, I want to paste a YouTube link (e.g., `https://youtu.be/dQw4w9WgXcQ`), click Download, and get the audio file saved to my local music library with ID3/M4A tags.
2. **Batch / Multiple Videos Download**: As a user, I want to paste a list of 10 YouTube video links copied from a forum or playlist, review the parsed list, and download all of them concurrently.
3. **Playlist Download**: As a user, I want to paste a YouTube playlist URL (e.g. `https://www.youtube.com/playlist?list=PL...`), have the system resolve all video IDs in the playlist, and download them into a batch.
4. **Instant Playback**: As a user, once my direct downloads finish, I want to switch to Music Player and find my new songs ready to play immediately.

## 4. Success Criteria
- [ ] Takeout Studio navigation displays `05 Direct` (or `05 Tải theo link`) alongside steps 01-04.
- [ ] Users can access `05 Direct` at any time, even if no Google Takeout archive has been imported yet.
- [ ] Textarea accepts multiple links with various formats (watch, youtu.be, shorts, playlist) and parses them without error.
- [ ] Backend extracts metadata, creates a `download_batches` record with status tracking, and runs downloads in parallel.
- [ ] Direct download items can be retried or skipped if YouTube blocks or returns errors.
- [ ] Downloaded tracks appear immediately in the Player workspace library.
- [ ] All unit, integration, and Playwright browser tests pass.
- [ ] Production frontend build succeeds with zero TypeScript/lint errors.

## 5. Constraints & Assumptions
- Python `yt-dlp` is used as the extraction and metadata retrieval engine.
- Network requests to YouTube may be subject to rate limiting or bot blocks; existing multi-client fallback in `downloader.py` must be utilized.
- Direct downloads do not require matching with a Google Takeout `watch-history.json` entry.
