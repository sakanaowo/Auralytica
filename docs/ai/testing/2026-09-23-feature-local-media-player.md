---
phase: testing
title: Testing Strategy — Local Media Player
description: Chiến lược kiểm thử tự động, tích hợp và kiểm thử thủ công cho phân hệ Local Media Player.
---

# Testing Strategy — Local Media Player

Ngày tạo: **2026-09-24**. Tính năng: `local-media-player`. Nhánh: `feature-local-media-player`.

---

## 1. Test Coverage Goals

- **Unit Test Coverage:** Đạt 100% cho toàn bộ các hàm mới trong `src/auralytica/player.py` và các API endpoints trong `src/auralytica/web.py`.
- **Hồi quy (Regression Testing):** 100% của 125 backend tests hiện có tiếp tục vượt qua.
- **Frontend Build & TypeScript Integrity:** 100% TypeScript compile sạch không cảnh báo hoặc lỗi kiểu (`tsc -b && vite build`).
- **An toàn tệp & Quyền riêng tư:** Chặn 100% các yêu cầu truy cập file ngoài thư mục nhạc được cấu hình (Path Traversal Protection).

---

## 2. Test Scenarios Checklist

### 2.1. Backend Unit Tests (`tests/test_player.py`)

- [ ] `T-PLAYER-DB-01`: Khởi tạo bảng CSDL SQLite (`player_playlists`, `player_playlist_tracks`, `player_favorites`, `player_track_cache`) thành công.
- [ ] `T-PLAYER-SCAN-01`: Quét đệ quy thư mục mẫu chứa các file `.m4a`, `.mp3`, `.flac`, `.opus` nhận diện chính xác số lượng file.
- [ ] `T-PLAYER-SCAN-02`: Sử dụng cache `player_track_cache` khi quét lại thư mục không bị thay đổi (`mtime_ns` khớp) mà không cần parse lại thẻ tag.
- [ ] `T-PLAYER-STREAM-01`: Endpoint `/api/player/stream` trả về `200 OK` khi không có Range header, `Content-Type` chuẩn audio.
- [ ] `T-PLAYER-STREAM-02`: Endpoint `/api/player/stream` trả về `206 Partial Content` khi có header `Range: bytes=0-1023` kèm `Content-Range`.
- [ ] `T-PLAYER-STREAM-03`: Chặn truy cập file bên ngoài thư mục nhạc (ví dụ path chứa `../` hoặc file hệ thống) trả về `403 Forbidden` hoặc `400 Bad Request`.
- [ ] `T-PLAYER-ART-01`: Trích xuất thành công ảnh bìa nhúng từ file MP3 (thẻ APIC) và M4A (thẻ covr) trả về dữ liệu ảnh binary.
- [ ] `T-PLAYER-ART-02`: Trả về `404 Not Found` khi file audio không chứa ảnh bìa nhúng.
- [ ] `T-PLAYER-META-01`: Ghi tag vật lý (Title, Artist, Album, Genre, Year) vào file MP3 và M4A; đọc lại bằng Mutagen xác nhận thông tin cập nhật chính xác.
- [ ] `T-PLAYER-META-02`: Ghi ảnh bìa mới vào file audio thành công.
- [ ] `T-PLAYER-PL-01`: Tạo, đổi tên, xóa Playlist trong SQLite.
- [ ] `T-PLAYER-PL-02`: Thêm bài hát vào playlist, xóa bài, và cập nhật vị trí thứ tự (`position`).
- [ ] `T-PLAYER-FAV-01`: Đảo trạng thái Yêu thích (toggle favorite) và lấy danh sách bài hát yêu thích.
- [ ] `T-PLAYER-M3U-01`: Xuất playlist ra chuỗi M3U8 định dạng `#EXTM3U` chuẩn UTF-8.
- [ ] `T-PLAYER-M3U-02`: Nhập file M3U8 tạo thành công playlist mới trong hệ thống.

### 2.2. Frontend Integration & UI Scenarios

- [ ] `T-FE-NAV-01`: Mode Switcher trên Header chuyển đổi mượt giữa `Takeout Studio` và `Music Player` mà không làm ngắt bài hát đang phát.
- [ ] `T-FE-PLAY-01`: Bấm phát một bài hát từ Table View hoặc Grid View kích hoạt thanh Player Bar phát nhạc.
- [ ] `T-FE-PLAY-02`: Kéo thanh trượt Seek Bar tua đến thời điểm bất kỳ mượt mà không bị giật lag.
- [ ] `T-FE-PLAY-03`: Tự động chuyển bài kế tiếp khi phát hết bài (auto-next).
- [ ] `T-FE-PLAY-04`: Chế độ Shuffle trộn bài ngẫu nhiên và Repeat (lặp 1 bài / lặp toàn bộ) hoạt động chính xác.
- [ ] `T-FE-STORE-01`: Reload trình duyệt (`F5`), khôi phục chính xác bài đang phát, vị trí giây, âm lượng và hàng đợi Queue từ `localStorage`.
- [ ] `T-FE-VIEW-01`: Nút chuyển đổi View Mode chuyển đổi tức thì giữa Table View (Spotify style) và Grid View (Apple Music style).
- [ ] `T-FE-SEARCH-01`: Ô tìm kiếm lọc nhanh danh sách bài hát theo Tên bài hoặc Tên nghệ sĩ theo thời gian thực.
- [ ] `T-FE-MODAL-01`: Mở modal chỉnh sửa metadata, lưu thành công và cập nhật ngay lập tức trên giao diện.
- [ ] `T-FE-PL-01`: Tạo playlist mới từ Sidebar, kéo/thêm bài hát vào playlist và xuất file `.m3u8`.

---

## 3. Manual Testing Checklist

- [ ] Thử nghiệm phát nhạc liên tục 5 bài hát với các định dạng khác nhau (`.m4a`, `.mp3`, `.opus`, `.flac`).
- [ ] Kiểm tra hiển thị Liquid Glass dark theme trên màn hình tối không bị chói sáng.
- [ ] Mở file sau khi chỉnh sửa tag bằng VLC hoặc Apple Music để xác nhận phần mềm bên ngoài đọc chuẩn tag mới.
- [ ] Kiểm tra tính năng xuất M3U8 bằng cách import vào phần mềm nghe nhạc ngoài (VLC).
