---
phase: requirements
title: Requirements — Local Desktop App, In-Stream Audio Pipeline & Metadata Embedding
description: Yêu cầu mở rộng Auralytica thành ứng dụng local desktop chuẩn Linux, tích hợp làm sạch tên và chuyển đổi định dạng Apple Music ngay trong luồng tải, và tự động thu thập & nhúng metadata bài hát.
---

# Requirements — Local Desktop App, In-Stream Audio Pipeline & Metadata Embedding

Cập nhật: **2026-09-22**. Tính năng: `local-app-and-audio-pipeline`.

---

## 1. Problem Statement

1. **Tách rời luồng xử lý (Disconnected Pipeline):**
   - Hiện tại, luồng tải (bước 04 Download) chỉ lưu file thô `.webm` và bắt buộc gắn mã `[video_id]` vào tên file (`Song Title [ulZQTrV8QlQ].webm`).
   - Người dùng muốn nghe nhạc trên hệ sinh thái Apple Music / macOS / iOS hoặc quản lý thư viện phải trải qua thêm một bước phụ (bước 05 Convert) để chuyển đổi từ WebM sang M4A và xóa mã video ID.
   - **Yêu cầu:** Bước làm sạch tên (loại bỏ `[video_id]` và các hậu tố rác của YouTube) cùng việc chuyển đổi sang định dạng đích tương thích (M4A ALAC Lossless / AAC) cần được cấu hình và thực thi **tự động ngay trong luồng tải (bước 04 Download)**.

2. **Thiếu vắng Siêu dữ liệu bài hát (Missing Metadata & Cover Art):**
   - File âm thanh tải về hiện tại không có thẻ metadata (ID3 / MP4 atoms: Title, Artist, Album, Year, Genre) và không có ảnh bìa album (Cover Art / Thumbnail). Khi đưa vào trình phát nhạc (Apple Music, Rhythmbox, Amberol, VLC), bài hát hiển thị thiếu thông tin, không gom album và không có artwork.
   - **Yêu cầu:** Cần có cơ chế tự động trích xuất metadata chuẩn (từ YouTube Music enrichment, yt-dlp info dict, cấu trúc `Artist - Title`) và tự động nhúng (embed) thẻ metadata + ảnh thumbnail trực tiếp vào file âm thanh khi tải/chuyển đổi.

3. **Phạm vi ứng dụng chưa tối ưu trải nghiệm Desktop (App Scope Limitation):**
   - Auralytica hiện đang chạy dưới dạng server web console (`uv run auralytica`) và mở trên trình duyệt. Người dùng muốn Auralytica trở thành một **ứng dụng cục bộ (local app) thực thụ** trên hệ điều hành (trước mắt tập trung vào **Linux**, chuẩn bị kiến trúc cho macOS và Windows).
   - Cần có: File khởi chạy `.desktop`, icon ứng dụng trên app launcher của hệ thống, desktop notifications (thông báo khi hoàn thành batch tải/convert), mở nhanh thư mục lưu trữ qua file manager hệ thống (`xdg-open`), và cơ chế chạy nền (daemon/headless).

4. **Kế thừa và lộ trình trang chuyển đổi tạm thời (Apple Music Page Retention):**
   - Trang bước 05 (Apple Music) hiện tại được giữ nguyên trong phiên này để người dùng có thể lọc và xử lý nhanh 493 file `.webm` đã tải từ trước.
   - Trang này sẽ chỉ được gỡ bỏ khi người dùng yêu cầu rõ ràng.

---

## 2. Goals & Objectives

### Primary Goals
1. **In-Stream Sanitization & Conversion (Tích hợp ngay bước Download):**
   - Người dùng có thể chọn định dạng đích ngay tại bước 04 (Download):
     - `M4A · Apple Lossless (ALAC)` *(Khuyên dùng cho Apple Music — bit-perfect, không suy hao âm thanh)*.
     - `M4A · AAC (256 kbps)` *(Chuẩn nén iTunes Store gọn nhẹ)*.
     - `MP3 (320 kbps)` *(Tương thích phổ thông)*.
     - `Nguyên bản (WebM Opus)` *(Giữ file gốc từ YouTube)*.
   - Tên file tải về được làm sạch tự động ngay tại khâu publish:
     - Loại bỏ mã `[video_id]` ở đuôi tên file.
     - Lọc bỏ các hậu tố thừa của YouTube (`Official Music Video`, `Lyric Video`, `MV`, `HD`, `Audio`...).
     - Tự động định dạng `Artist - Title` và đánh số `(1)`, `(2)` nếu phát hiện trùng tên mà không phụ thuộc vào mã video ID.
2. **Metadata Enrichment & Embedding (Nhúng thẻ & Ảnh bìa):**
   - Thu thập metadata từ 3 nguồn:
     - YouTube Music metadata cache (từ bước Explore/Enrichment).
     - Info JSON của yt-dlp (chứa thumbnail chất lượng cao, artist, track name, album).
     - Bộ phân tích cú pháp thông minh từ tiêu đề (`Artist - Title`).
   - Tự động nhúng trực tiếp vào container âm thanh qua FFmpeg:
     - Thẻ: `Title`, `Artist`, `Album`, `Date`.
     - Ảnh bìa (Attached picture / Cover art): Tự động nạp thumbnail YouTube và nhúng vào metadata của file M4A/MP3.
3. **Bảo tồn trang chuyển đổi tạm thời (Apple Music Page Retention):**
   - Giữ nguyên bước `05 · Apple Music` trong phiên này để người dùng lọc và xử lý nhanh 493 file `.webm` đã tải từ trước.
   - Chỉ xóa bước này khi có yêu cầu cụ thể từ người dùng.

### Non-Goals
- **Đóng gói Desktop App OS:** Đóng gói ứng dụng desktop native / installer / `.desktop` launcher được dời sang lifecycle tiếp theo theo chỉ đạo của người dùng.
- Không phụ thuộc vào các dịch vụ đám mây trả phí hoặc telemetry bên ngoài (100% xử lý cục bộ, bảo vệ quyền riêng tư).
- Không ép buộc người dùng chuyển đổi sang MP3 làm giảm chất lượng nếu họ chọn giữ nguyên bản Opus hoặc chọn ALAC Lossless.

---

## 3. User Stories & Use Cases

- **US01 - Cấu hình tải chuẩn Apple Music:** Là người dùng, tôi muốn ngay tại bước Download có thể chọn lưu file thành M4A (ALAC Lossless) hoặc M4A (AAC), để khi tải xong tôi có thể kéo trực tiếp vào Apple Music trên máy mà không cần làm thêm bước convert thủ công.
- **US02 - Tên file sạch sẽ:** Là người dùng, tôi muốn các file tải về có tên đẹp đẽ như `Adele - Skyfall.m4a` thay vì bị dính mã `[DeumyOzKqgI]` và các chữ `Official Lyric Video`.
- **US03 - Nhúng Metadata & Ảnh bìa:** Là người dùng, tôi muốn khi mở file âm thanh trong Apple Music hoặc trình phát nhạc Linux, bài hát có đầy đủ tên ca sĩ, tên bài, tên album và ảnh bìa minh họa sắc nét.
- **US04 - Ứng dụng Desktop Linux:** Là người dùng Linux, tôi muốn khởi chạy Auralytica từ menu ứng dụng của OS như một app thông thường, nhận được thông báo hệ thống khi tải xong và bấm một nút để mở thư mục nhạc trong Nautilus/Dolphin.
- **US05 - Xử lý thư viện cũ:** Là người dùng, tôi muốn giữ lại màn hình Apple Music hiện tại để xử lý xong đợt 493 bài đã tải trước đó, trước khi chuyển giao hoàn toàn sang luồng in-stream download mới.

---

## 4. Technical Architecture & Decisions

### 4.1. Kiến trúc Luồng Tải & Xử lý (In-Stream Audio Pipeline)
```
[YouTube Source]
       │
       ▼ (yt-dlp extract audio + thumbnail)
[Staging Directory (.auralytica/batch-X/video_id/)]
  ├── audio.opus / audio.webm
  └── thumbnail.jpg (Cover Art)
       │
       ▼ (FFmpeg In-Stream Post-Processing)
  1. Lossless Decode & Transcode (ALAC / AAC / MP3)
  2. Embed Tags (Title, Artist, Album, Year)
  3. Embed Cover Art Thumbnail
       │
       ▼ (Publish with Clean Name)
  Path: ~/Music/Auralytica/{Artist - Title}.m4a (hoặc {Title}.m4a)
  * Loại bỏ hoàn toàn [video_id], tự động giải quyết trùng tên bằng (1), (2).
```

### 4.2. Chiến lược Thu thập & Áp dụng Metadata (Brainstorming Outcome)
- **Nguồn 1: SQLite DB (`videos` & `metadata_cache`):** Đã có sẵn dữ liệu chuẩn từ YouTube Music API nếu người dùng đã chạy enrich.
- **Nguồn 2: yt-dlp Info Dict:** Khi trích xuất, yt-dlp trả về metadata chi tiết của video, bao gồm URL thumbnail kích thước lớn (`thumbnails[-1]`). Download thumbnail này về staging directory tạm thời.
- **Nguồn 3: Heuristic Parser:** Phân tích tiêu đề nếu thiếu tag:
  - Cắt các tag `Official Video`, `MV`, `HD`...
  - Tách `Artist - Title`.
  - Loại bỏ hậu tố ` - Topic` từ tên kênh YouTube Music để lấy ca sĩ chuẩn.
- **Cơ chế nhúng (FFmpeg parameters):**
  - M4A (ALAC / AAC):
    ```bash
    ffmpeg -y -i audio.webm -i thumbnail.jpg \
      -map 0:a -map 1:v \
      -c:a alac (hoặc aac -b:a 256k) \
      -c:v copy -disposition:v:0 attached_pic \
      -metadata title="Title" \
      -metadata artist="Artist" \
      -metadata album="Album" \
      output.m4a
    ```
  - MP3:
    ```bash
    ffmpeg -y -i audio.webm -i thumbnail.jpg \
      -map 0:a -map 1:v \
      -c:a libmp3lame -b:a 320k \
      -c:v copy -id3v2_version 3 \
      -metadata title="Title" \
      -metadata artist="Artist" \
      output.mp3
    ```

### 4.3. Linux Desktop Integration
- **Desktop Entry (`~/.local/share/applications/auralytica.desktop`):**
  - Đăng ký MIME types, categories `AudioVideo;Audio;`.
  - Icon đồ họa vector đặt tại `~/.local/share/icons/hicolor/scalable/apps/auralytica.svg`.
- **System Notification (`notify-send` / Desktop Notification):**
  - Khi worker hoàn thành lượt tải: gửi thông báo qua D-Bus `notify-send "Auralytica" "Đã tải xong X bài hát."`.
- **File Manager Integration:**
  - API endpoint `POST /api/system/open-directory`: Gọi `xdg-open <path>` mở ngay cửa sổ file manager trên Linux.

---

## 5. Success Criteria

1. **Chất lượng âm thanh & Tên file:** File tải về ở bước Download lưu trực tiếp dưới dạng `.m4a` (ALAC hoặc AAC theo lựa chọn), tên file không chứa `[video_id]`, không chứa các từ rác YouTube.
2. **Metadata hiển thị chuẩn:** File `.m4a` mở trong Apple Music / VLC / Rhythmbox hiển thị đúng Tên bài, Ca sĩ và có ảnh bìa Cover Art.
3. **Trải nghiệm Desktop Linux:** Khởi chạy được từ Application Launcher của Linux; gửi được thông báo khi hoàn thành; có nút mở thư mục trực tiếp.
4. **Tính tương thích:** Giữ nguyên trang chuyển đổi Apple Music hiện tại cho phiên này; toàn bộ test suite Python (121 tests) tiếp tục vượt qua thành công.

---

## 6. Constraints & Assumptions

- **OS:** Tập trung tối ưu hóa cho **Linux (Ubuntu, Debian, Fedora, Arch)**.
- **Dependencies:** Sử dụng FFmpeg (đã xác nhận có sẵn trên máy người dùng, hỗ trợ đầy đủ `alac`, `aac`, `libmp3lame`).
- **Data Safety:** Mọi thao tác đổi tên hoặc ghi file đều có cơ chế tránh ghi đè làm mất dữ liệu gốc.
