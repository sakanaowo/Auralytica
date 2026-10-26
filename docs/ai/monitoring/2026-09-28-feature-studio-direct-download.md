---
phase: monitoring
title: Monitoring & Observability — Tải nhanh (Quick Download)
description: Theo dõi trạng thái, lỗi và các điểm cần chú ý của workspace Tải nhanh trong ứng dụng local Auralytica.
---

# Monitoring & Observability — Tải nhanh (Quick Download)

Ngày cập nhật: **2026-10-26**. Tính năng: `studio-direct-download`.

Ứng dụng không có telemetry. Mọi trạng thái nằm trong SQLite local và hiển thị trên UI.

## 1. Trạng thái batch

- `GET /api/downloads/{batch_id}` trả trạng thái batch (`queued`, `running`, `paused`, `completed`, `partial`) và đếm item theo trạng thái. `QuickDownloadView` poll endpoint này.
- Batch đang theo dõi được nhớ trong `localStorage` (`auralytica_direct_batch_id`), nên mở lại trang vẫn thấy tiến độ.
- Worker chạy nền độc lập với tab. Đóng tab hoặc dừng server không dừng worker.
- `GET /api/workflow`: `download_busy=true` khi có batch bất kỳ chiếm worker; `batch_locked` chỉ bật với batch Takeout. Batch Tải nhanh không khoá Import/Explore/Dedup.
- Chỉ một batch chạy tại một thời điểm. Tạo lượt mới khi worker bận trả HTTP 409 với số lượt đang chạy.

## 2. Lỗi

| Nơi | Biểu hiện | Xử lý |
| --- | --- | --- |
| Resolve | Dòng không nhận dạng được hoặc playlist lỗi → `invalid_urls` | Sửa link rồi phân tích lại |
| Resolve | Video private/xoá/giới hạn, lỗi mạng → `unavailable` kèm `code` | Hiện trong khối báo cáo; lỗi mạng thì phân tích lại |
| Resolve | Quá 1.000 video → `truncated=true` | Chia playlist thành nhiều lượt |
| Submit | Worker đang bận → HTTP 409 | Đợi lượt đang chạy xong hoặc tạm dừng |
| Submit | ID sai, danh sách rỗng/quá lớn, format lạ → HTTP 422 | — |
| Tải | `download_items.error_code` / `error_message` (tối đa 1.500 ký tự), ví dụ `transcode_error`, `invalid_output`, `filesystem` | Retry hoặc skip từng item / toàn bộ item lỗi |
| Tải | Lỗi filesystem là lỗi fatal: dừng batch, item còn lại giữ `queued` | Kiểm tra quyền/dung lượng rồi Resume |
| Index Player | Lỗi `cache_single_track` bị bỏ qua | Quét lại thư viện trong Player |

## 3. Kiểm tra nhanh

```bash
sqlite3 ~/.local/share/auralytica/library.sqlite3 \
  "SELECT id, kind, status FROM download_batches ORDER BY id DESC LIMIT 10;"
sqlite3 ~/.local/share/auralytica/library.sqlite3 \
  "SELECT status, COUNT(*) FROM download_items WHERE batch_id=<id> GROUP BY status;"
```
