---
phase: requirements
title: Requirements & Problem Understanding
description: Clarify the problem space, gather requirements, and define success criteria for Quick YouTube Download workspace with inline metadata editing
---

# Requirements: Quick YouTube Download (Tải Nhanh)

## 1. Problem Statement
Previously, Auralytica's Takeout Studio strictly followed a linear pipeline (`01 Import` -> `02 Explore` -> `03 Deduplicate` -> `04 Download`) that required importing an extracted Google Takeout folder containing `watch-history.json`.

When users discover new songs, music videos, or playlists on YouTube that they want to add to their offline library immediately, they cannot do so through the web interface without re-exporting an entire Google Takeout archive. Furthermore, users require:
1. An independent, parallel workspace **Tải nhanh (Quick Download)** parallel to Takeout Studio and Music Player (rather than being hidden as step 05 inside Studio).
2. The ability to **edit output metadata (Title and Artist)** inline immediately after URL analysis before downloading.
3. Accurate audio format conversion (Lossless ALAC M4A vs MP3 320 kbps vs AAC 256 kbps).
4. Full reuse of the rich download controls (output directory picker, audio format cards, concurrency slider, batch monitor with pause/resume, retry/skip, status filters).

## 2. Goals & Non-Goals

### Goals
- **Top-level Mode Switcher**: Add `[⚡ Tải nhanh]` parallel to `[Takeout Studio]` and `[Music Player]`.
- **Fast URL Input**: Provide a multi-line Textarea accepting single or multiple YouTube links with a one-click clipboard paste button.
- **Robust URL Resolution**:
  - Standard watch URLs (`https://www.youtube.com/watch?v=...`)
  - Shortened URLs (`https://youtu.be/...`)
  - YouTube Shorts (`https://www.youtube.com/shorts/...`)
  - YouTube Playlists (`https://www.youtube.com/playlist?list=...`) with automatic extraction of constituent video entries.
  - Stripping tracking parameters (`&si=`, `&feature=`, `&t=`).
  - Concurrent metadata extraction via `yt-dlp` to get real video title, channel, duration, and thumbnail.
- **Inline Metadata Editor**:
  - Editable Title and Artist inputs for each resolved video.
  - One-click `Wand2` button to clean YouTube tags (official music video, 4K, lyrics, etc.).
  - Dynamic preview of the planned output filename (`📁 Artist - Title.ext`).
  - Quick remove button and external YouTube link.
- **Reuse Rich Download Controls**:
  - Destination directory selector with fallback to `~/Music/Auralytica`.
  - Audio format selection cards: Lossless ALAC (M4A), MP3 (320 kbps), AAC (256 kbps).
  - Concurrency slider (1x - 8x parallel downloads).
  - Live batch progress monitor with real-time poll, item breakdown, and instant button to switch to Music Player.
  - Pause/Resume, Retry failed items, and Skip failed items controls.
- **Output Format Fidelity**:
  - Correctly normalize format aliases (`mp3_320` -> `mp3`, `alac` -> `m4a_alac`) so transcoding is executed properly.
- **Instant Auto-Indexing**:
  - Downloaded tracks are immediately indexed in `player_track_cache` so they are immediately available in `/player`.

### Non-Goals
- Supporting non-YouTube streaming platforms (e.g. SoundCloud, Bilibili) in this phase.
- Breaking the existing Google Takeout 4-step workflow (Steps 01-04 remain fully intact in Takeout Studio).

## 3. Success Criteria
- [x] Top-level navigation displays `[Takeout Studio]`, `[⚡ Tải nhanh]`, and `[Music Player]`.
- [x] Users can access `Tải nhanh` at any time without needing a Google Takeout import.
- [x] Textarea accepts single/multiple links and playlists, resolving real video metadata.
- [x] Users can edit Title and Artist inline and see the planned filename preview in real time.
- [x] Audio formats (ALAC M4A, MP3 320k, AAC) are accurately transcoded and tagged with cover art.
- [x] Output directory, concurrency slider, pause/resume, and retry/skip controls function identically to `DownloadView`.
- [x] Downloaded tracks appear immediately in Music Player.
- [x] All unit, integration, and browser tests pass cleanly.
- [x] Production frontend build succeeds with zero errors.
