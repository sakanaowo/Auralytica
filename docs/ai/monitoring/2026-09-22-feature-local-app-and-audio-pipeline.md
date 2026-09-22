---
phase: monitoring
title: Monitoring & Operations — In-Stream Audio Pipeline & Metadata Embedding
description: Giám sát vận hành cho luồng tải in-stream, xử lý lỗi transcoding và nhật ký tải bài hát.
---

# Monitoring & Operations — In-Stream Audio Pipeline & Metadata Embedding

Cập nhật: **2026-09-22**. Tính năng: `local-app-and-audio-pipeline`.

---

## 1. Health & Error Observation
- **Batch Errors:** Lưu tại setting `batch_error:{batch_id}` trong SQLite.
- **Item Errors:** Phân loại mã lỗi chi tiết trong bảng `download_items` (`unavailable`, `bot_blocked`, `rate_limited`, `filesystem`...).
- **Transcode Failures:** Nếu FFmpeg gặp lỗi trong quá trình post-processing, lỗi được ghi vào `error_message` của item đó và cho phép người dùng bấm thử lại.

## 2. Recovery & Retry
- Sử dụng các endpoint:
  - `POST /api/downloads/{batch_id}/retry-failed`
  - `POST /api/downloads/{batch_id}/items/{video_id}/retry`
