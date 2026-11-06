---
phase: testing
title: Test Plan & Scenarios
description: Kiểm thử layout Spotify, phím tắt và lời bài hát của Music Player
---

# Test Plan: Player Spotify-Style Layout, Shortcuts & Lyrics

Cập nhật: **2026-10-26**.

## Backend — `tests/test_player.py`

| Test | Kiểm tra |
| --- | --- |
| `test_lyrics_sidecar_lrc_detection` | Đọc `.lrc` cạnh file audio, tách bản plain |
| `test_lyrics_lrclib_mocked` | LRCLIB được mock; kết quả được lưu cache |
| `test_save_track_metadata_preserves_has_cover_art_and_is_favorite` | Sửa metadata không mất ảnh bìa / yêu thích |

## Browser — `tests/browser/test_player_ui.py`

| Test | Kiểm tra |
| --- | --- |
| `test_player_spotify_layout_and_shortcuts_modal` | Sidebar trái/phải, tab Now Playing/Queue, modal phím tắt |
| `test_player_lyrics_and_metadata_edit` | Hiển thị lời bài hát và sửa metadata |

## Chưa có test

- Kéo thay đổi độ rộng sidebar và khôi phục từ `localStorage`.
- Phím tắt bị chặn khi đang gõ trong ô nhập.
- Lời nhúng trong tag file (chỉ có test cho `.lrc` và LRCLIB).

## Bằng chứng

| Ngày | Kết quả |
| --- | --- |
| 2026-10-26 | Backend: 151 test OK (`uv run --no-sync --with httpx python -m unittest discover -s tests`). Browser chưa chạy lại vì thiếu Chromium cho Playwright 1.62. |
| 2026-09-28 | `tests/browser/test_player_ui.py`: 2 test đạt (theo implementation doc của tính năng Tải nhanh). |
