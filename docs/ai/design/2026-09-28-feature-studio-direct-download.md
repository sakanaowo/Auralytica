---
phase: design
title: Architecture & System Design
description: Technical architecture, data models, APIs, and component specifications for Direct YouTube Download in Takeout Studio
---

# Design: Direct YouTube Download in Takeout Studio

## 1. Architecture Overview

```mermaid
graph TD
    subgraph Frontend Studio
        Header[Studio Header: Steps 01..05]
        DDV[DirectDownloadView: Step 05]
        URLInput[Multi-line URL Textarea & Client-Side Parser]
        Config[Format ALAC/MP3 & Output Directory Config]
        BatchTracker[Direct Batch Progress & Item List Monitor]
    end

    subgraph Backend FastAPI
        API_Direct["POST /api/download/direct"]
        API_Resolve["POST /api/download/direct/resolve"]
        API_BatchStatus["GET /api/download/batches/{id}"]
        API_Controls["POST /api/download/items/{id}/retry | skip"]
    end

    subgraph Download Engine & Storage
        Resolver[yt-dlp Flat Playlist & Metadata Resolver]
        BatchWorker[Multi-threaded Download Worker (yt-dlp + ffmpeg)]
        DB[(SQLite: download_batches, download_items, videos)]
        PlayerCache[(SQLite: player_track_cache)]
        FS[(Local Music Directory: ~/Music/Auralytica)]
    end

    Header -->|Navigates to 05| DDV
    DDV --> URLInput
    DDV --> Config
    URLInput -->|Validate & Resolve| API_Resolve
    DDV -->|Submit Batch| API_Direct
    API_Direct --> DB
    API_Direct --> BatchWorker
    BatchWorker --> Resolver
    BatchWorker --> FS
    BatchWorker -->|On Success Index Track| PlayerCache
    DDV --> BatchTracker
    BatchTracker -->|Poll State| API_BatchStatus
    BatchTracker -->|Retry / Skip| API_Controls
```

## 2. API Specifications

### 2.1 `POST /api/download/direct/resolve`
Fast client-side / server-side resolution of URLs to identify video count, playlist expansions, and video titles before starting download.
- **Request Body**:
  ```json
  {
    "urls": [
      "https://www.youtube.com/watch?v=VIDEO_ID",
      "https://youtu.be/SHORT_ID",
      "https://www.youtube.com/playlist?list=PLAYLIST_ID"
    ]
  }
  ```
- **Response**:
  ```json
  {
    "videos": [
      {
        "video_id": "VIDEO_ID",
        "url": "https://www.youtube.com/watch?v=VIDEO_ID",
        "title": "Song Title",
        "channel": "Artist / Channel",
        "duration": 240,
        "thumbnail_url": "https://i.ytimg.com/vi/VIDEO_ID/hqdefault.jpg"
      }
    ],
    "invalid_urls": []
  }
  ```

### 2.2 `POST /api/download/direct`
Creates a dedicated download batch and triggers the background multi-threaded download engine.
- **Request Body**:
  ```json
  {
    "videos": [
      {
        "video_id": "VIDEO_ID",
        "title": "Song Title",
        "channel": "Artist / Channel",
        "duration": 240,
        "thumbnail_url": "..."
      }
    ],
    "output_dir": "~/Music/Auralytica",
    "format": "m4a_alac"
  }
  ```
- **Response**:
  ```json
  {
    "batch_id": 12,
    "status": "queued",
    "total_items": 1
  }
  ```

### 2.3 Status & Controls
Reuses existing endpoints:
- `GET /api/download/batches/{batch_id}`: Polls progress, speed, item states (`queued`, `running`, `completed`, `failed`, `skipped`).
- `POST /api/download/items/{item_id}/retry`: Retries failed items with client fallbacks.
- `POST /api/download/items/{item_id}/skip`: Skips problematic items.

## 3. Frontend Component Design

### 3.1 Studio Navigation Integration
- In `frontend/src/App.tsx`:
  - Extend `StudioStep` union: `'import' | 'explore' | 'dedup' | 'download' | 'direct'`.
  - Add `DirectDownloadView` rendering under `{mode === 'takeout' && currentStep === 'direct' && <DirectDownloadView />}`.
- In `frontend/src/components/Header.tsx`:
  - Add `05 Direct` (or `05 Tải theo link`) to the navigation steps.
  - Unlike steps 02-04, step `05 Direct` is always enabled, even if no Takeout history is loaded.

### 3.2 `DirectDownloadView.tsx`
- **Header Card**: Title, description, and link guidance.
- **Input Area**:
  - Resizable textarea for pasting links.
  - "Dán từ clipboard" (Paste from clipboard) button for one-click insertion.
  - Live count indicator: `X liên kết hợp lệ` | `Y liên kết không hợp lệ`.
- **Download Settings**:
  - Thư mục lưu trên máy: input with default `~/Music/Auralytica`.
  - Định dạng âm thanh: **Lossless ALAC (M4A)** vs **MP3 (320 kbps)** cards.
- **Resolution & Preview Drawer**:
  - Visual list of resolved videos with thumbnail, title, channel, duration.
  - Option to remove individual items before downloading.
- **Batch Progress Monitor**:
  - Live progress bar, speed, running item indicator, failed item retry/skip buttons.
  - Success banner with button: "Mở trong Player để nghe ngay" (navigates to `/player`).

## 4. Backend Engine & Database Integration

### 4.1 URL Regex & Playlist Expansion
- Standard Watch: `(?:v=|vi=|youtu\.be\/|shorts\/)([a-zA-Z0-9_-]{11})`
- Playlist: `(?:list=)([a-zA-Z0-9_-]+)`
- For playlist URLs, use `yt_dlp.YoutubeDL({'extract_flat': 'in_playlist', 'skip_download': True})` to extract individual video entries without downloading video media during resolution.

### 4.2 Database Recording
- Insert resolved videos into `videos` table with `user_group = 'music'` so they are recognized by the system.
- Create a batch in `download_batches` with `label = 'direct_url'`.
- Insert items into `download_items`.

### 4.3 Automatic Indexing into Player Cache
- In `downloader.py`, upon successful download of an item, call `storage.add_or_update_player_track(db, file_path)` or `player.cache_single_track(db, file_path)`.
- This ensures newly downloaded tracks appear in the player immediately without requiring a full manual rescan.

## 5. Security & Performance
- Rate limiting protection: yt-dlp fallback clients (`android`, `ios`, `web`) already implemented in `downloader.py`.
- Concurrent resolution: resolve playlists and single links using thread pools with a timeout (10s max per playlist).
- Input sanitization: clean invalid characters from URLs and paths before execution.
