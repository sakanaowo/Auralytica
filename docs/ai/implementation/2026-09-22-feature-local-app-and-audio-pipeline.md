---
phase: implementation
title: Implementation Log — In-Stream Audio Pipeline & Metadata Embedding
description: Nhật ký và bằng chứng triển khai kỹ thuật cho tính năng chuyển đổi Apple Music và làm sạch tên ngay trong bước tải.
---

# Implementation Log — In-Stream Audio Pipeline & Metadata Embedding

Cập nhật: **2026-09-22**. Tính năng: `local-app-and-audio-pipeline`.

---

## 1. Overview
Triển khai nâng cấp luồng tải tuần tự (Sequential Audio Downloader) sang mô hình In-Stream Audio Pipeline:
- Tự động làm sạch tên file (loại bỏ `[video_id]` và hậu tố rác của YouTube).
- Chuyển đổi sang M4A (ALAC Lossless / AAC) hoặc MP3 ngay tại bước tải (bước 04 Download).
- Tự động thu thập và nhúng metadata bài hát (Title, Artist, Album) + ảnh thumbnail Cover Art.
- Duy trì trang `05 · Apple Music` cho phiên này để xử lý 493 file hiện có.

---

## 2. Progress Tracker

- [x] **Milestone 1: Backend Core In-Stream Pipeline**
  - [x] Task 1.1: `_ytdlp.py` thumbnail & cover art extraction
  - [x] Task 1.2: `downloader.py` in-stream transcode & clean name publishing
  - [x] Task 1.3: `download_controls.py` & `web.py` API parameters & persistence
  - [x] Task 1.4: Unit tests in `tests/` (124/124 tests pass)
- [x] **Milestone 2: Frontend DownloadView Integration**
  - [x] Task 2.1: Types & client API updates
  - [x] Task 2.2: DownloadView format cards & options
  - [x] Task 2.3: Production build & verification (`npm run build` thành công 100%)

---

## 3. Implementation Details & Evidence
1. **Lấy Thumbnail & Metadata tại `_ytdlp.py`:**
   - Cấu hình `'writethumbnail': True` và `'postprocessors': [{'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'}]`.
   - Trích xuất `thumbnail_path`, `title`, `artist` (bỏ `- Topic`), `album`, `release_year` và emit trong `result` dict.
2. **In-stream Transcoding & Clean Publishing tại `downloader.py` & `converter.py`:**
   - Nâng cấp `convert_audio_file` nhúng Cover Art (`attached_pic` cho M4A / ID3v2 attached picture cho MP3) và metadata tags (`title`, `artist`, `album`, `date`).
   - `_publish`: Khi `clean_names=True`, áp dụng `clean_title` loại bỏ hoàn toàn `[video_id]` và YouTube tags, format chuẩn `Artist - Title.m4a`, chống ghi đè bằng đánh số thứ tự `(1)`, `(2)`.
   - `run_batch`: Đọc format từ `settings` (`batch_format:{batch_id}`, `batch_clean_names:{batch_id}`, `batch_embed_metadata:{batch_id}`). Transcode in-stream trước khi publish.
3. **Web API & Controls:**
   - `DownloadRequest` nhận `format`, `clean_names`, `embed_metadata`.
   - `start_download` truyền cấu hình sang `create_batch`, lưu vào DB settings.
4. **Frontend DownloadView:**
   - Khối chọn định dạng 4 Cards: M4A ALAC Lossless (Apple Music Khuyên dùng), M4A AAC (256k), MP3 (320k), Nguyên bản (Raw).
   - Checkboxes: Làm sạch tên file và Nhúng ảnh bìa/metadata.
   - Badge định dạng và trạng thái tên sạch trong danh sách batch.
5. **Kiểm thử nghiệm thu:**
   - `uv run pytest tests/test_*.py`: 124 passed (100%).
   - `npm --prefix frontend run build`: Build production hoàn tất sạch sẽ.
