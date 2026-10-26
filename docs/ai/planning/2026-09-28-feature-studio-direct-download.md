---
phase: planning
title: Implementation Plan
description: Danh sách task và trạng thái của workspace Tải nhanh (Quick Download)
---

# Implementation Plan: Tải nhanh (Quick Download)

Cập nhật: **2026-10-26**. Kế hoạch ban đầu ("Step 05 Direct" trong Studio, `Header.tsx`, `DirectDownloadView.tsx`) đã được thay bằng mode độc lập `quick_download`. Các task dưới đây ghi theo phương án đã triển khai.

## Đợt 1 — triển khai ban đầu (2026-09-28 → 2026-10-10)

- [x] **Task 1: Phân tích URL** ([downloader.py](../../../src/auralytica/downloader.py)) — `parse_youtube_url`, `resolve_direct_urls`, endpoint `POST /api/download/direct/resolve`.
- [x] **Task 2: Tạo batch và chạy worker** — `create_direct_batch`, endpoint `POST /api/download/direct`.
- [x] **Task 3: Ưu tiên metadata người dùng sửa** khi ghi tag và đặt tên file.
- [x] **Task 4: Index vào Player** — `player.cache_single_track` sau mỗi item hoàn tất.
- [x] **Task 5: API client và types** — `resolveDirectUrls`, `submitDirectDownload`.
- [x] **Task 6: Mode switcher** — `AppMode` thêm `quick_download`, route `/quick-download`.
- [x] **Task 7: `QuickDownloadView`** — nhập link, sửa Title/Artist, tuỳ chọn tải, theo dõi batch.

## Đợt 2 — hoàn thiện (2026-10-26)

- [x] **Task 8: Tách metadata Tải nhanh khỏi `videos`** — schema v7: `download_batches.kind`, bảng `direct_download_items`, migration từ `batch_is_direct:*`. Tạo batch không còn ghi đè title/kênh/nhóm của video Takeout.
- [x] **Task 9: Khoá nhất quán** — `storage.review_locked` chỉ tính batch Takeout; `create_direct_batch` và `create_batch` trả 409 khi worker đang bận thay vì tạo batch kẹt `queued` hoặc "reuse" nhầm batch Tải nhanh. Workflow trả thêm `download_busy`.
- [x] **Task 10: Skip không lan sang Takeout** — `skip_item`/`skip_failed` chỉ ghi `download_selections` với batch Takeout.
- [x] **Task 11: Báo video không tải được** — resolve trả `unavailable` (lỗi yt-dlp, mục private/deleted trong playlist) và `truncated` (tối đa 1.000 video). UI hiện khối `#direct-resolve-report`.
- [x] **Task 12: Validate request** — `video_id` 11 ký tự, `format` Literal, `concurrency` 1–8, giới hạn số dòng/video.
- [x] **Task 13: UI** — khoá nút tải khi `download_busy`; nhãn "Tải nhanh" trong danh sách lượt của trang Download; trang Download không cho bắt đầu khi đang có lượt Tải nhanh.
- [x] **Task 14: Test** — 9 test backend mới (cô lập Takeout, khoá, skip, resolve, migration v6→v7); viết lại test Playwright chạy qua `download_server.py` (không gọi YouTube, không ghi vào `~/Music`).

## Ngoài phạm vi nhánh này

- `tests/browser/test_ui.py` (10 test Takeout) vẫn viết cho giao diện vanilla JS trước khi chuyển sang React, nên đã hỏng từ 2026-09-20. Cần viết lại riêng.
- Giao diện converter (`/api/converter/*` đã có, chưa có view).
- Hàng đợi nhiều batch: worker vẫn chỉ chạy một batch tại một thời điểm.
