---
phase: requirements
title: Requirements & Problem Understanding — Local Media Player
description: Đặc tả yêu cầu cho phân hệ Local Media Player chuyên dụng với đa giao diện phát nhạc, chỉnh sửa metadata và quản lý playlist.
---

# Requirements & Problem Understanding — Local Media Player

Ngày tạo: **2026-09-23**. Nhánh/Tính năng: `feature-local-media-player`.

---

## 1. Problem Statement

**Vấn đề cốt lõi:**
- Hiện tại Auralytica là công cụ xử lý và tải nhạc từ Google Takeout YouTube (`01 Import` → `02 Explore` → `03 Deduplicate` → `04 Download`). 
- Sau khi tải nhạc hoàn tất về thư mục máy tính (mặc định `~/Music/Auralytica`), người dùng không có công cụ phát nhạc trực tiếp, duyệt bài, chỉnh sửa metadata (tags: ca sĩ, album, ảnh bìa...) hay tự tạo danh sách phát (playlist) ngay trong ứng dụng, mà buộc phải mở các ứng dụng bên thứ ba (như VLC, Apple Music, Spotify local files).
- Người dùng cần một không gian nghe nhạc chuyên nghiệp (**Local Media Player**) hoạt động trực tiếp trên thư mục nhạc offline cục bộ, với trải nghiệm hiện đại mượt mà (Spotify / Apple Music Desktop), tách biệt hoàn toàn khỏi luồng nhập và tải Takeout trước đó.

---

## 2. Goals & Objectives

### 2.1. Primary Goals
1. **Phân tách không gian làm việc cấp cao (Mode Switcher):**
   - Đặt bộ chuyển đổi trên Header: `Takeout Studio` ⟷ `Music Player`.
   - `Takeout Studio`: Giữ nguyên quy trình 4 bước nhập, lọc và tải nhạc Takeout hiện có.
   - `Music Player`: Không gian ứng dụng nghe nhạc độc lập với Sidebar thư viện/playlist, nội dung chính, và Persistent Audio Player Bar ở đáy màn hình.
2. **Quét & Lập chỉ mục thư mục cục bộ (Local Directory Indexing):**
   - Mặc định liên kết với thư mục đã tải nhạc trước đó (`~/Music/Auralytica`), cho phép người dùng thay đổi hoặc chọn thư mục khác.
   - Tự động quét và lập chỉ mục nhanh khi khởi động/chọn thư mục; có nút `↻ Quét lại thư viện` thủ công.
   - Hỗ trợ các định dạng âm thanh phổ biến: `.m4a`, `.mp3`, `.flac`, `.opus`, `.webm`, `.wav`.
3. **Đa giao diện phát nhạc (Multiple View Layouts):**
   - Hỗ trợ chuyển đổi linh hoạt hiển thị danh sách bài hát:
     - **Table View (Spotify Desktop style):** Bảng chi tiết với cột STT, Tiêu đề + Nghệ sĩ, Album, Thời lượng, Ngày thêm, và menu thao tác nhanh.
     - **Grid/Card View (Apple Music style):** Lưới thẻ vuông trực quan với ảnh bìa lớn, tên bài hát và nghệ sĩ.
4. **Trình phát âm thanh cố định (Persistent Player Bar):**
   - Luôn ghim ở chân trang trong chế độ Player.
   - Các nút điều khiển: Phát/Tạm dừng, Bài kế tiếp, Bài trước đó, Trộn bài (Shuffle), Lặp lại (Repeat one / all).
   - Thanh tiến trình phát mượt mà hỗ trợ tua (seek) chính xác qua cơ chế HTTP 206 Partial Content.
   - Điều khiển âm lượng và xem Hàng đợi phát (Queue).
5. **Chỉnh sửa Metadata trực tiếp vào file vật lý:**
   - Sử dụng thư viện `mutagen` ở backend để đọc và ghi tag trực tiếp vào file nhạc (`ID3` cho MP3, `MP4/iTunes tags` cho M4A/ALAC, `Vorbis Comments` cho FLAC/Opus).
   - Cho phép chỉnh sửa: Tên bài hát, Nghệ sĩ, Album, Thể loại, Năm phát hành, và Ảnh bìa (Cover art upload/replace).
   - Giữ nguyên đường dẫn file để đảm bảo an toàn, kèm tùy chọn chuẩn hóa tên file theo định dạng chuẩn khi người dùng yêu cầu.
6. **Quản lý Playlist cá nhân & Favorites:**
   - Lưu trữ bền vững trong CSDL SQLite cục bộ (`playlists`, `playlist_items`).
   - Mục đặc biệt: **Bài hát yêu thích (Favorites / Liked Songs)** với thao tác 1-click icon trái tim.
   - Tạo, đổi tên, xóa playlist; kéo thả hoặc chọn thêm/bớt bài hát từ thư viện vào playlist.
   - Hỗ trợ **Xuất / Nhập danh sách phát chuẩn (`.m3u` / `.m3u8`)** để đồng bộ sang điện thoại hoặc các phần mềm phát nhạc khác.

### 2.2. Non-Goals (Ngoài phạm vi)
- Không phát nhạc trực tuyến từ YouTube streaming hoặc Spotify Web API (chỉ phát nhạc offline có sẵn trong máy tính).
- Không làm xáo trộn hoặc thay đổi các logic cốt lõi của quy trình YouTube Takeout đã ổn định.

---

## 3. User Stories & Use Cases

- **US-01:** Là một người dùng, tôi muốn bấm chuyển giữa `Takeout Studio` và `Music Player` ở thanh Header để có thể nghe nhạc ngay sau khi vừa tải xong mà không phải mở phần mềm khác.
- **US-02:** Là một người dùng, tôi muốn duyệt thư viện bài hát dưới dạng Table chi tiết hoặc Grid ảnh bìa lớn để phù hợp với sở thích nhìn của tôi.
- **US-03:** Là một người dùng, tôi muốn nghe nhạc liên tục, chuyển bài, tua nhanh/lùi và điều chỉnh âm lượng mượt mà bằng thanh Player ở đáy màn hình.
- **US-04:** Là một người dùng, tôi muốn chỉnh sửa lại tên bài hát, ca sĩ, album hoặc thay ảnh bìa chuẩn cho các bài hát tải về bị sai tên tag, và thông tin này được lưu thẳng vào file audio trên máy.
- **US-05:** Là một người dùng, tôi muốn tạo các danh sách phát theo tâm trạng (như "Chill Acoustic", "Gym EDM") và gắn icon trái tim cho các bài hát yêu thích.
- **US-06:** Là một người dùng, tôi muốn xuất danh sách phát đã tạo ra file `.m3u8` để chuyển vào thẻ nhớ điện thoại hoặc máy nghe nhạc chuyên dụng.
- **US-07:** Là một người dùng, tôi muốn bấm "Quét lại thư viện" để ứng dụng nhận diện ngay các bài hát mới mà tôi vừa copy vào thư mục nhạc.

---

## 4. Success Criteria

| Mã tiêu chí | Tiêu chí nghiệm thu | Phương thức kiểm chứng |
| :--- | :--- | :--- |
| **AC-NAV-01** | Header có Mode Switcher chuyển mượt giữa `Takeout Studio` và `Music Player`. | Kiểm thử tương tác UI trên trình duyệt |
| **AC-PLAY-01** | Phát mượt các định dạng `.m4a`, `.mp3`, `.opus`, `.flac` với thời gian bắt đầu < 100ms. | Kiểm thử phát audio HTML5 Audio API |
| **AC-PLAY-02** | Tua thanh thời gian (seek bar) trơn tru thông qua HTTP Range (206 Partial Content). | Kiểm tra Network tab trên browser DevTools |
| **AC-VIEW-01** | Nút chuyển đổi View Mode (Table ⟷ Grid) chuyển trạng thái hiển thị tức thì không cần reload. | Kiểm thử tương tác giao diện |
| **AC-META-01** | Chỉnh sửa tags và ảnh bìa lưu thành công vào file vật lý, kiểm tra lại bằng Mutagen / VLC hiển thị đúng. | Unit test backend & mở file bằng media player ngoài |
| **AC-PL-01** | Tạo, sửa, xóa playlist và quản lý danh sách bài hát trong playlist lưu trữ bền vững vào SQLite. | Test CSDL SQLite và API endpoints |
| **AC-PL-02** | Xuất và nhập thành công file playlist `.m3u` / `.m3u8` chuẩn UTF-8. | Test nhập/xuất file M3U |
| **AC-TEST-01** | 100% unit tests và integration tests backend/frontend pass sạch không có regression. | `uv run pytest` và `npm run build` |

---

## 5. Constraints & Assumptions

- **Công nghệ Backend:** Python 3.11, FastAPI, `mutagen` cho audio tagging, SQLite cho cơ sở dữ liệu playlist và cache chỉ mục.
- **Công nghệ Frontend:** React 19, TypeScript, Tailwind CSS, HTML5 Audio API.
- **Bảo mật & Quyền riêng tư:** Hoàn toàn chạy local offline trên máy tính người dùng (`127.0.0.1`), không gửi dữ liệu ra bên ngoài.
- **An toàn tệp:** Việc sửa tag trên file vật lý sử dụng cơ chế ghi an toàn (atomic write / backup tạm) của mutagen để tránh hỏng file nếu quá trình ghi bị ngắt đột ngột.

---

## 6. Questions & Open Items

- [x] Phân tách kiến trúc: Chế độ chuyển đổi cấp cao (Mode Switcher) `Takeout Studio` ⟷ `Music Player` trên Header. *(Đã xác nhận)*
- [x] Đa giao diện: Chuyển đổi linh hoạt giữa Table View (Spotify style) và Grid View (Apple Music style). *(Đã xác nhận)*
- [x] Cơ chế ghi Metadata: Dùng Mutagen ghi trực tiếp vào file vật lý (ID3/MP4 tags) kèm ảnh bìa, giữ nguyên tên file an toàn. *(Đã xác nhận)*
- [x] Quản lý Playlist: SQLite cục bộ + mục Yêu thích (Favorites) + Xuất/Nhập file `.m3u8`. *(Đã xác nhận)*
- [x] Cơ chế quét đĩa: Tự động quét khi mở/chọn thư mục + nút quét lại thủ công. *(Đã xác nhận)*
