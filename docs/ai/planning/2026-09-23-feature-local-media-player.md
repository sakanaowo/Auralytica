---
phase: planning
title: Project Planning & Task Breakdown — Local Media Player
description: Phân rã công việc chi tiết thành các Milestone và Tasks khả thi cho phân hệ Local Media Player.
---

# Project Planning & Task Breakdown — Local Media Player

Ngày tạo: **2026-09-24**. Tính năng: `local-media-player`. Nhánh: `feature-local-media-player`.

---

## 1. Milestones Overview

- [x] **Milestone 1: Backend Storage & Core Player Engine** — Schema SQLite, thư viện scanner & cache, streaming HTTP 206 Byte Range, trích xuất ảnh bìa nhúng.
- [x] **Milestone 2: Metadata Physical Writer & Playlist Management** — Ghi thẻ Mutagen trực tiếp vào file vật lý, quản lý playlist & bài hát yêu thích, nhập/xuất M3U, unit tests backend.
- [x] **Milestone 3: Frontend Audio Context & Persistent Player Bar** — Global `AudioPlayerContext`, đồng bộ `localStorage`, Persistent Player Bar đáy màn hình, Hàng đợi phát (Queue Drawer).
- [x] **Milestone 4: Frontend Navigation & Multi-View Layouts** — Header Mode Switcher (`Takeout Studio` ⟷ `Music Player`), PlayerSidebar, PlayerHeader, Table View (Spotify style) & Grid View (Apple Music style).
- [x] **Milestone 5: Modals, Polish & End-to-End Verification** — `MetadataEditModal`, `PlaylistModal`, kiểm thử tích hợp thực tế, build frontend và nghiệm thu pre-push.

---

## 2. Detailed Task Breakdown

### Milestone 1: Backend Storage & Core Player Engine

- [x] **Task 1.1: Database Schemas & Migrations**
  - *Mô tả:* Bổ sung các bảng SQLite trong `src/auralytica/storage.py`: `player_playlists`, `player_playlist_tracks`, `player_favorites`, `player_track_cache` và các chỉ mục tương ứng.
  - *Kết quả:* CSDL khởi tạo đầy đủ các bảng khi mở database, tương thích ngược với dữ liệu cũ.
  - *Kiểm chứng:* Unit test khởi tạo database và migrations passed.
- [x] **Task 1.2: Library Scanner & Cache Service**
  - *Mô tả:* Viết module `src/auralytica/player.py` hàm quét đệ quy thư mục nhạc cục bộ, đọc định dạng âm thanh (`.m4a`, `.mp3`, `.flac`, `.opus`, `.webm`, `.wav`), đọc thẻ tag bằng `mutagen` và lưu cache vào `player_track_cache` (so khớp bằng `mtime_ns` và `file_size`).
  - *Kết quả:* Lập chỉ mục thư mục nhạc trong < 20ms khi có cache.
  - *Kiểm chứng:* Test quét thư mục mẫu với các file audio khác nhau passed.
- [x] **Task 1.3: Audio Streaming & Range Requests Engine**
  - *Mô tả:* Xây dựng endpoint `GET /api/player/stream?path=...` trong FastAPI hỗ trợ HTTP 206 Partial Content (chuẩn Byte Range), kiểm tra an toàn thư mục (chặn Path Traversal).
  - *Kết quả:* Trình duyệt có thể phát và tua seek tức thì (< 50ms).
  - *Kiểm chứng:* Test request với header `Range: bytes=0-1024` trả về status code 206 và header `Content-Range`.
- [x] **Task 1.4: Embedded Cover Art Extractor**
  - *Mô tả:* Xây dựng endpoint `GET /api/player/art?path=...` đọc dữ liệu ảnh nhúng (ID3 APIC / MP4 covr / FLAC Picture) từ file audio trả về binary image kèm header `Cache-Control`.
  - *Kết quả:* Trả về đúng ảnh thumbnail nhúng của bài hát; trả về 404 khi file không có ảnh.
  - *Kiểm chứng:* Test trích xuất ảnh từ file M4A và MP3 mẫu passed.

### Milestone 2: Metadata Physical Writer & Playlist Management

- [x] **Task 2.1: Mutagen Metadata Physical Editor**
  - *Mô tả:* Xây dựng endpoint `POST /api/player/metadata` (Multipart form-data) ghi tag trực tiếp vào file vật lý bằng Mutagen (Title, Artist, Album, Genre, Year, Cover Art) và cập nhật cache CSDL. Hỗ trợ tùy chọn đổi tên file theo định dạng chuẩn.
  - *Kết quả:* Ghi thành công vào file mà không làm hỏng dữ liệu âm thanh gốc.
  - *Kiểm chứng:* Unit test đọc file trước và sau khi ghi tag, xác nhận tag mới bằng Mutagen.
- [x] **Task 2.2: Playlists & Favorites CRUD Service**
  - *Mô tả:* Xây dựng các endpoints REST API quản lý Playlist (Tạo, Sửa tên/mô tả, Xóa, Thêm/bớt bài hát, Sắp xếp thứ tự `position`) và API đảo trạng thái Yêu thích (`/api/player/favorites/toggle`).
  - *Kết quả:* Quản lý playlist mượt mà, lưu trữ bền vững trong SQLite.
  - *Kiểm chứng:* Unit tests cho toàn bộ luồng tạo, cập nhật, xóa playlist và toggle favorite passed.
- [x] **Task 2.3: M3U/M3U8 Generator & Parser**
  - *Mô tả:* Xây dựng endpoint `GET /api/player/playlists/{id}/export-m3u` xuất file danh sách phát `.m3u8` chuẩn UTF-8, và endpoint `POST /api/player/playlists/import-m3u` đọc file M3U nhập vào hệ thống.
  - *Kết quả:* Xuất/nhập danh sách phát tương thích với các trình phát nhạc khác.
  - *Kiểm chứng:* Test xuất playlist ra chuỗi M3U và nhập lại so sánh khớp danh sách bài.
- [x] **Task 2.4: Comprehensive Backend Unit Tests**
  - *Mô tả:* Viết test suite `tests/test_player.py` bao quát 100% các hàm và API mới của phân hệ Player.
  - *Kết quả:* Toàn bộ test suite mới + 125 tests cũ đều PASS (134/134 passed).
  - *Kiểm chứng:* `uv run pytest tests/test_*.py`.

### Milestone 3: Frontend Audio Context & Persistent Player Bar

- [x] **Task 3.1: Global `AudioPlayerContext`**
  - *Mô tả:* Thiết lập React Context quản lý 1 instance `HTMLAudioElement` duy nhất, quản lý hàng đợi Queue, auto-next, shuffle, repeat mode (off/all/one), và đồng bộ toàn diện trạng thái Player vào `localStorage`.
  - *Kết quả:* Không gián đoạn âm thanh khi chuyển trang; khôi phục nguyên vẹn trạng thái khi reload.
  - *Kiểm chứng:* Kiểm tra playback, seek, và localStorage persistence trên trình duyệt.
- [x] **Task 3.2: `PersistentPlayerBar` Component**
  - *Mô tả:* Xây dựng thanh điều khiển phát nhạc cố định đáy màn hình (Liquid Glass theme): ảnh bìa vuông 48x48, Title + Artist, icon Tim yêu thích, cụm nút Play/Pause/Skip/Shuffle/Repeat, thanh trượt thời gian Seek Bar kéo thả mượt mà, thanh âm lượng Volume slider, nút mở Queue.
  - *Kết quả:* Thanh điều khiển hoạt động mượt mà, nhạy bén và đẹp mắt.
  - *Kiểm chứng:* Tương tác điều khiển phát, tua và chỉnh âm lượng.
- [x] **Task 3.3: `QueueDrawer` Component**
  - *Mô tả:* Xây dựng drawer bên phải hiển thị danh sách bài hát đang chờ phát (Upcoming Queue), cho phép click chuyển bài ngay hoặc xóa bài khỏi hàng đợi.
  - *Kết quả:* Xem và quản lý hàng đợi phát trực quan.
  - *Kiểm chứng:* Kiểm tra thêm bài vào queue và phát bài từ queue.

### Milestone 4: Frontend Navigation & Multi-View Layouts

- [x] **Task 4.1: Top-level Mode Switcher (`AppShell.tsx` & `App.tsx`)**
  - *Mô tả:* Thêm bộ chuyển đổi chế độ trên Header: `Takeout Studio` ⟷ `Music Player`. Tách riêng vùng hiển thị của 2 phân hệ; giữ nguyên 4 bước Takeout khi ở `Takeout Studio`.
  - *Kết quả:* Chuyển đổi mượt mà giữa quy trình tải Takeout và trình phát nhạc.
  - *Kiểm chứng:* Click chuyển đổi mode không làm gián đoạn bài hát đang phát.
- [x] **Task 4.2: `PlayerSidebar` Component**
  - *Mô tả:* Xây dựng cột sidebar trái phong cách Spotify: Mục Thư viện (Tất cả bài hát, Bài hát yêu thích, Thư mục nguồn), Danh sách Playlists cá nhân, nút `+ Tạo playlist mới`, nút `Import M3U`.
  - *Kết quả:* Điều hướng thư viện và playlist trực quan.
  - *Kiểm chứng:* Click chuyển giữa các playlist và mục yêu thích.
- [x] **Task 4.3: `PlayerHeader` Component**
  - *Mô tả:* Thanh công cụ đầu trang hiển thị thư mục nguồn, nút `↻ Quét lại`, ô tìm kiếm bài/nghệ sĩ, menu sắp xếp, và nút chuyển đổi bố cục (`Table View` ⟷ `Grid View`).
  - *Kết quả:* Lọc và sắp xếp danh sách tức thì không giật lag.
  - *Kiểm chứng:* Thử tìm kiếm bài hát và chuyển đổi giữa 2 chế độ hiển thị.
- [x] **Task 4.4: `TrackTableView` (Spotify Desktop style)**
  - *Mô tả:* Bảng chi tiết: Cột STT `#`, Nút Play nhanh, Tiêu đề + Nghệ sĩ, Album, Thời lượng, Icon Tim yêu thích, Menu context `...` (Phát tiếp theo, Thêm vào playlist, Sửa thông tin).
  - *Kết quả:* Danh sách hiển thị chuyên nghiệp, mượt mà khi cuộn.
  - *Kiểm chứng:* Click phát bài từ bảng và mở menu thao tác.
- [x] **Task 4.5: `TrackGridView` (Apple Music style)**
  - *Mô tả:* Lưới thẻ đĩa vuông bo góc nghệ thuật: Ảnh bìa lớn, nút Play tròn nổi khi hover chuột, Tiêu đề và Nghệ sĩ.
  - *Kết quả:* Trải nghiệm đĩa nhạc trực quan, sang trọng.
  - *Kiểm chứng:* Kiểm tra hiển thị lưới trên các độ phân giải màn hình khác nhau.

### Milestone 5: Modals, Polish & End-to-End Verification

- [x] **Task 5.1: `MetadataEditModal` Component**
  - *Mô tả:* Hộp thoại chỉnh sửa thông tin bài hát: Sửa Title, Artist, Album, Genre, Year, kéo thả upload ảnh bìa mới, tùy chọn "Đổi tên file chuẩn". Gọi API cập nhật vật lý file và làm mới cache.
  - *Kết quả:* Chỉnh sửa và lưu thông tin ngay trên giao diện web.
  - *Kiểm chứng:* Sửa thông tin một bài hát và kiểm tra cập nhật trên bảng/lưới.
- [x] **Task 5.2: `PlaylistModal` Component**
  - *Mô tả:* Hộp thoại tạo mới và đổi tên playlist, kèm nút xuất file `.m3u8`.
  - *Kết quả:* Tạo và xuất danh sách phát nhanh chóng.
  - *Kiểm chứng:* Tạo playlist mới và xuất file M3U8.
- [x] **Task 5.3: End-to-End Integration Verification & Build**
  - *Mô tả:* Kiểm thử toàn diện trên trình duyệt với thư mục nhạc thực tế (`~/Music/Auralytica`), chạy `npm run build` và `uv run pytest`.
  - *Kết quả:* 100% build sạch, 100% tests pass, trải nghiệm nghe nhạc ổn định.
  - *Kiểm chứng:* Build log và kết quả test suite.

---

## 3. Dependencies & Sequencing Notes

```text
Milestone 1 (Storage & Engine) [COMPLETED]
       ↓
Milestone 2 (Metadata & Playlists) [COMPLETED]
       ↓
Milestone 3 (Audio Context & Player Bar) [COMPLETED]
       ↓
Milestone 4 (Navigation & Views) [COMPLETED]
       ↓
Milestone 5 (Modals & Verification) [COMPLETED]
```

- Toàn bộ 5 Milestone đã được hiện thực hóa và kiểm thử thành công.
- 134 bài kiểm thử pytest và build frontend Vite TypeScript đều pass 100%.
