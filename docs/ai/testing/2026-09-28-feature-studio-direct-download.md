---
phase: testing
title: Test Plan & Scenarios
description: Kịch bản kiểm thử và bằng chứng cho workspace Tải nhanh (Quick Download)
---

# Test Plan: Tải nhanh (Quick Download)

Cập nhật: **2026-10-26**.

## Backend — `tests/test_direct_download.py`

| Test | Kiểm tra |
| --- | --- |
| `test_parse_youtube_url_variations` | Watch (kèm `si`/`t`), `youtu.be`, shorts, embed, playlist, ID trần, chuỗi không hợp lệ |
| `test_resolve_direct_urls_videos_and_playlist` | yt-dlp mock; video lẻ + playlist, bỏ trùng, URL lỗi vào `invalid_urls` |
| `test_create_direct_batch_creates_batch_and_items` | `kind='direct'`, items, tag vào `direct_download_items`, `videos.user_group` để trống |
| `test_create_direct_batch_mp3_format_normalization_and_custom_metadata` | `mp3_320` → `mp3`; tag đã sửa được lưu |
| `test_direct_download_api_endpoints` | Resolve (mock yt-dlp) và submit qua `TestClient` |
| `test_cache_single_track_populates_player_track_cache` | File hoàn tất vào `player_track_cache` |
| `DirectDownloadResolveTests.test_unreachable_videos_and_playlist_placeholders_are_reported_not_queued` | Video private và mục `[Private video]`/`[Deleted video]` vào `unavailable`, không vào `videos` |
| `DirectDownloadResolveTests.test_resolve_caps_video_count` | Cắt ở `MAX_DIRECT_VIDEOS`, `truncated=true` |
| `DirectDownloadIsolationTests.test_existing_takeout_video_is_not_rewritten` | Title/kênh/nhóm của video Takeout giữ nguyên; danh sách item hiện title đã sửa |
| `DirectDownloadIsolationTests.test_direct_batch_does_not_lock_review_but_occupies_worker` | Không khoá review; `create_batch` và lượt Tải nhanh thứ hai đều bị từ chối |
| `DirectDownloadIsolationTests.test_takeout_batch_still_locks_review` | Batch Takeout vẫn khoá review và chặn Tải nhanh |
| `DirectDownloadIsolationTests.test_skipping_failed_direct_items_keeps_takeout_selection` | Skip không ghi `download_selections` |
| `DirectDownloadIsolationTests.test_run_batch_tags_and_names_files_from_edited_metadata` | Worker đặt tên `Artist - Title` theo tag đã sửa, không theo yt-dlp |
| `DirectDownloadIsolationTests.test_workflow_reports_busy_without_review_lock` | `batch_locked=false`, `download_busy=true`; submit trả 409 khi bận, 422 khi ID sai |
| `DirectDownloadMigrationTests.test_v6_direct_batches_get_kind_and_backfilled_tags` | Migration v6→v7 |

## Browser — `tests/browser/test_direct_download_ui.py`

`test_resolve_edit_download_and_open_player` chạy qua `tests/browser/download_server.py`: HTTP, database và worker thật, adapter giả tạo audio bằng ffmpeg. Test không gọi YouTube và không ghi vào `~/Music`.

1. Mở Tải nhanh khi chưa import Takeout.
2. Phân tích (resolve được mock), kiểm tra khối báo cáo video không tải được / link sai.
3. Sửa title, chọn MP3, kiểm tra tên file dự kiến.
4. Bắt đầu tải; khi worker còn giữ item, nút tải bị khoá ("Đang có lượt tải chạy").
5. Thả worker; file `Rick Astley - Never Gonna Give You Up (Remastered).mp3` có trên đĩa.
6. `/api/workflow` vẫn `batch_locked=false`; mở Player từ khối theo dõi.

Test bị skip nếu máy không có `ffmpeg`.

## Bằng chứng (2026-10-26)

| Lệnh | Kết quả |
| --- | --- |
| `uv run --no-sync python -m unittest discover -s tests` | **160 test OK** |
| `uv run --no-sync python -m unittest tests.browser.test_direct_download_ui tests.browser.test_player_ui tests.browser.test_session_management_ui` | **4 test OK** |
| `uv run --no-sync python -m unittest tests.browser.test_ui` | 10 lỗi, có từ trước nhánh này: file vẫn dùng selector của UI vanilla JS cũ (`#music-total`, `#rest-toggle`…) |
| `npm --prefix frontend run build` | Đạt, không lỗi TypeScript |

Cài môi trường test:

```sh
uv sync --locked --no-default-groups --group test --group browser
uv run --no-sync playwright install chromium
```
