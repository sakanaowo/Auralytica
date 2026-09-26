---
phase: implementation
title: Implementation Guide — Local Media Player
description: Tài liệu chi tiết kiến trúc kỹ thuật, cấu trúc mã nguồn, API endpoints, và tối ưu hóa phân hệ Local Media Player.
---

# Implementation Guide — Local Media Player

Tính năng: `local-media-player`. Nhánh: `feature-local-media-player`.

---

## 1. Development Setup

- **Ngôn ngữ & Runtime:** Python 3.11+ (Backend), Node.js v20+ / React 19 / TypeScript 5.7+ (Frontend).
- **Thư viện Backend:** `fastapi`, `starlette`, `mutagen`, `sqlite3`, `pydantic`.
- **Thư viện Frontend:** `@tanstack/react-query`, `lucide-react`, `tailwindcss 4`, `vite`.
- **Lệnh thực thi:**
  - Backend: `uv run uvicorn auralytica.web:create_app --reload --factory`
  - Frontend Build: `npm --prefix frontend run build`
  - Kiểm thử: `uv run pytest tests/test_*.py`

---

## 2. Code Structure

```text
├── src/auralytica/
│   ├── storage.py              # Schema SQLite v5: player_playlists, player_playlist_tracks, player_favorites, player_track_cache
│   ├── player.py               # Core Player engine: scan_library, tag writer, stream_audio_file, extract_cover_art, M3U parser
│   └── web.py                  # FastAPI REST API endpoints (/api/player/*)
├── frontend/src/
│   ├── api/
│   │   ├── types.ts            # PlayerTrack, PlayerPlaylist, PlayerPlaylistTrack, PlayerMetadataUpdatePayload
│   │   └── client.ts           # REST API client methods for Player
│   ├── context/
│   │   └── AudioPlayerContext.tsx # Global audio controller, HTMLAudioElement, range streaming, localStorage sync
│   ├── components/
│   │   └── AppShell.tsx        # Top-level Mode Switcher (Takeout Studio ⟷ Music Player) & Persistent Player Bar
│   ├── features/player/
│   │   ├── PlayerWorkspace.tsx    # Main orchestrator view
│   │   ├── PlayerSidebar.tsx      # Spotify-style library & custom playlists navigation
│   │   ├── PlayerHeader.tsx       # Search, Sort, View mode switcher, folder re-scan
│   │   ├── TrackTableView.tsx     # Spotify Desktop-style track table
│   │   ├── TrackGridView.tsx      # Apple Music-style album card grid
│   │   ├── PersistentPlayerBar.tsx # Viewport-fixed bottom playback bar (controls, seek, volume, queue trigger)
│   │   ├── QueueDrawer.tsx        # Right slide-over queue drawer
│   │   ├── MetadataEditModal.tsx  # Physical tag & cover art editor
│   │   └── PlaylistModal.tsx      # Create/edit playlist & M3U import modal
└── tests/
    └── test_player.py          # Unit tests covering scanning, streaming, metadata writing, playlists, and M3U
```

---

## 3. Implementation Details

### 3.1 Backend Core Engine (`src/auralytica/player.py`)
- **Metadata Caching & Scanning:** `scan_library(db, folder)` duyệt đệ quy thư mục, đọc các định dạng `.m4a`, `.mp3`, `.flac`, `.opus`, `.webm`, `.wav`. Sử dụng bảng `player_track_cache` so khớp `mtime_ns` và `file_size` để tăng tốc độ tải danh mục xuống < 20ms.
- **Audio Streaming with HTTP 206 Partial Content:** `stream_audio_file(path, range_header)` băm header `Range: bytes=start-end`, trả về status code 206 kèm `Content-Range`, `Accept-Ranges: bytes`, `Content-Length`. Hỗ trợ trình duyệt seek audio mượt mà tức thì (< 50ms).
- **Physical Tag Writer:** `save_track_metadata(...)` hỗ trợ ghi tag nguyên tử trực tiếp vào file vật lý:
  - ID3v2.4 (`TIT2`, `TPE1`, `TALB`, `TCON`, `TDRC`, `APIC`) cho MP3.
  - MP4 iTunes tags (`©nam`, `©ART`, `©alb`, `©gen`, `©day`, `covr`) cho M4A.
  - Vorbis Comments / FLAC Picture cho FLAC và Opus.
  - Tùy chọn đổi tên file theo quy chuẩn an toàn: `Artist - Title.ext`.
- **An toàn đường dẫn (Security):** `is_safe_path(base_dir, target)` giải phóng symlink và chuẩn hóa đường dẫn để chặn hoàn toàn lỗ hổng Path Traversal.

### 3.2 Frontend Architecture
- **Global `AudioPlayerContext`:** Quản lý một đối tượng `HTMLAudioElement` duy nhất. Duy trì trạng thái phát, hàng đợi `queue`, lịch sử bài đã nghe, chế độ lặp lại (`off` | `all` | `one`), ngẫu nhiên (`isShuffled`), âm lượng `volume` và vị trí tua `currentTime`.
- **Đồng bộ `localStorage`:** Trạng thái nghe nhạc và hàng đợi được lưu tự động vào `localStorage` key `auralytica_player_state_v1`, phục hồi nguyên vẹn khi người dùng F5 hoặc đóng/mở trình duyệt.
- **Header Mode Switcher (`AppShell.tsx`):** Tách bạch rõ ràng giữa phân hệ `Takeout Studio` (4 bước: import, explore, deduplicate, download) và phân hệ `Music Player`. Bài hát đang phát không bị ngắt khi người dùng chuyển đổi qua lại giữa hai phân hệ.
- **Multi-View System:** Cho phép chuyển đổi tức thì giữa **Table View** (bảng danh sách chi tiết kiểu Spotify Desktop) và **Grid View** (lưới thẻ bìa đĩa vuông kiểu Apple Music).

---

## 4. Verification & Testing

- **Backend Unit Tests:** 134/134 bài kiểm thử vượt qua thành công trong 6.93s (`tests/test_*.py`).
- **Frontend Compilation:** `tsc -b && vite build` hoàn thành không cảnh báo, sinh bundle tĩnh vào `src/auralytica/static/`.
- **Kiểm tra an toàn file:** Mọi thao tác chỉnh sửa thẻ nhạc kiểm tra kỹ lưỡng không gây suy hao dữ liệu âm thanh gốc.
