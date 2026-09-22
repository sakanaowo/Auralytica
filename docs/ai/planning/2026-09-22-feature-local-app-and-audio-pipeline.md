---
phase: planning
title: Implementation Plan — In-Stream Audio Pipeline & Metadata Embedding
description: Kế hoạch triển khai chi tiết từng task cho việc tích hợp bộ chuyển đổi Apple Music và làm sạch tên ngay trong bước tải.
---

# Implementation Plan — In-Stream Audio Pipeline & Metadata Embedding

Cập nhật: **2026-09-22**. Tính năng: `local-app-and-audio-pipeline`.

---

## 1. Milestones & Task Breakdown

### Milestone 1: Backend In-Stream Downloader Pipeline (Tải + Transcode + Embed Metadata + Clean Name)
- [x] **Task 1.1:** Nâng cấp `_ytdlp.py` hỗ trợ tải thumbnail ảnh bìa (`writethumbnail`) và xuất `thumbnail_path` trong JSON emit result.
- [x] **Task 1.2:** Cập nhật `downloader.py`:
  - Bổ sung hàm post-processing in-stream bằng FFmpeg: chuyển đổi sang `m4a_alac`, `m4a_aac`, `mp3` và nhúng tags (`title`, `artist`, `album`) + Cover Art.
  - Cập nhật hàm `_publish`: áp dụng `clean_title` loại bỏ `[video_id]` và hậu tố rác của YouTube; tự động giải quyết trùng tên bằng số thứ tự `(1)`, `(2)`.
  - Cập nhật kiểm tra `_valid_file` và `_completed_file` để nhận diện cả file `.m4a` / `.mp3` theo định dạng của batch.
- [x] **Task 1.3:** Cập nhật `download_controls.py` và `web.py`:
  - Mở rộng model `DownloadRequest` để nhận `format`, `clean_names`, `embed_metadata`.
  - Lưu cấu hình format vào batch/settings để worker sử dụng khi chạy.
- [x] **Task 1.4:** Bổ sung unit tests trong `tests/test_downloader.py` và `tests/test_download_controls.py` cho in-stream conversion và clean naming. Đảm bảo 124/124 tests pass.

### Milestone 2: Frontend DownloadView Integration
- [x] **Task 2.1:** Cập nhật `frontend/src/api/types.ts` và `frontend/src/api/client.ts` để gửi các tham số `format`, `clean_names`, `embed_metadata` trong API `startDownload`.
- [x] **Task 2.2:** Cập nhật `frontend/src/features/download/DownloadView.tsx`:
  - Thêm khối cấu hình định dạng tải (Format Cards: M4A ALAC, M4A AAC, MP3, Nguyên bản).
  - Thêm các checkbox làm sạch tên và nhúng metadata.
  - Bảo tồn nút chuyển sang bước 05 (Apple Music) và giữ nguyên trang `ConvertView.tsx`.
- [x] **Task 2.3:** Build production frontend bằng Vite và kiểm tra giao diện Liquid Glass.

---

## 2. Dependencies & Ordering
- Task 1.1 ➔ Task 1.2 ➔ Task 1.3 ➔ Task 1.4 (Hoàn thiện lõi Backend trước).
- Task 2.1 ➔ Task 2.2 ➔ Task 2.3 (Cập nhật Frontend đồng bộ với API).
- Nghiệm thu toàn diện: Chạy 100% backend test + test tải thực nghiệm.
