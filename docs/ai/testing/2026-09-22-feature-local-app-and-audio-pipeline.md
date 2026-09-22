---
phase: testing
title: Testing Strategy — In-Stream Audio Pipeline & Metadata Embedding
description: Kịch bản kiểm thử cho tính năng chuyển đổi Apple Music ngay khi tải, làm sạch tên file bỏ [video_id] và tự động nhúng metadata bài hát.
---

# Testing Strategy — In-Stream Audio Pipeline & Metadata Embedding

Cập nhật: **2026-09-22**. Tính năng: `local-app-and-audio-pipeline`.

---

## 1. Test Coverage Goals

- **Kiểm thử Hồi quy Backend:** 100% trong số 121 bài test hiện tại tiếp tục chạy `OK`.
- **Kiểm thử Chức năng Mới:**
  - In-stream post-processor: Transcode ALAC (M4A) / AAC / MP3 không suy hao âm thanh và nhúng ID3/MP4 metadata + thumbnail ảnh bìa.
  - Tên file sạch: Không còn dính `[video_id]`, không dính tag YouTube rác, giải quyết xung đột trùng tên bằng `(1)`, `(2)`.
  - Download options API: Nhận format và tuỳ chọn từ client.
  - Giao diện DownloadView: Hiển thị bộ chọn format và các tuỳ chọn tải mượt mà.
  - Bảo tồn trang bước 05 (Apple Music) nguyên vẹn.

---

## 2. Test Scenarios

### 2.1. Backend Downloader & In-Stream Pipeline
- [x] `T-DL-STREAM-01`: `downloader.py` hỗ trợ cấu hình `output_format='m4a_alac'` và tự động xuất ra file đuôi `.m4a` chứa audio codec `alac`. (Đã kiểm chứng trong `test_in_stream_transcode_to_m4a_alac_with_cover_art`).
- [x] `T-DL-STREAM-02`: `downloader.py` hỗ trợ cấu hình `output_format='m4a_aac'` và xuất ra file `.m4a` chứa audio codec `aac`.
- [x] `T-DL-STREAM-03`: `_publish` đặt tên file sạch dạng `Artist - Title.m4a` thay vì dính mã `[video_id]`. (Đã kiểm chứng trong `test_in_stream_clean_names_removes_video_id_and_tags`).
- [x] `T-DL-STREAM-04`: Khi có 2 bài trùng tên, file thứ hai được lưu thành `Song Name (1).m4a` mà không ghi đè file thứ nhất.
- [x] `T-DL-TAG-01`: File M4A tải về có nhúng thẻ metadata `title`, `artist`, `album`, `date` và ảnh bìa attached_pic khi có thumbnail.
- [x] `T-DL-RECOVER-01`: Khi resume hoặc retry bài lỗi, hệ thống nhận diện đúng các file M4A đã tải xong theo định dạng đã cấu hình.

### 2.2. API Contract & Persistence
- [x] `T-API-DL-01`: `POST /api/downloads` chấp nhận tham số `format`, `clean_names`, `embed_metadata` và lưu cấu hình vào batch. (Đã kiểm chứng trong `test_start_download_with_format_and_clean_names_payload`).
- [x] `T-API-DL-02`: `GET /api/downloads/{batch_id}` trả về đầy đủ format và status tương ứng.

### 2.3. Frontend UI (DownloadView)
- [x] `T-FE-DL-01`: Màn hình `DownloadView` có bộ chọn định dạng tải: M4A ALAC Lossless, M4A AAC, MP3, Nguyên bản.
- [x] `T-FE-DL-02`: Checkbox làm sạch tên và nhúng metadata được bật mặc định.
- [x] `T-FE-DL-03`: Nút `[ Tải toàn bộ bản giữ ]` gửi đúng cấu hình đã chọn xuống API.
- [x] `T-FE-STEP05-01`: Trang `05 · Apple Music` tiếp tục hiển thị bình thường trên menu điều hướng và Stepper.

---

## 3. Verification Evidence
- [x] Chạy lệnh `npm --prefix frontend run build`: Thành công 100%, 0 lỗi TypeScript, 0 lỗi Vite.
- [x] Chạy lệnh `uv run pytest tests/test_*.py`: 124 passed (100% pass), thời gian 5.76s.
- [x] Kiểm thử nhúng Cover Art và ALAC codec bằng FFmpeg thực tế: Đã xác nhận sinh file M4A kèm `attached_pic` chuẩn xác.
