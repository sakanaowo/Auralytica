---
phase: deployment
title: Deployment Strategy — Tải nhanh (Quick Download)
description: Build, đóng gói và rollback cho workspace Tải nhanh của ứng dụng local Auralytica.
---

# Deployment Strategy — Tải nhanh (Quick Download)

Ngày cập nhật: **2026-10-26**. Tính năng: `studio-direct-download`.

## 1. Môi trường

Giống các tính năng khác: ứng dụng local tại `http://127.0.0.1:8765`, SQLite tại `~/.local/share/auralytica/library.sqlite3` (hoặc `--database`), frontend tĩnh trong `src/auralytica/static/`.

Phụ thuộc runtime của tính năng:

- `yt-dlp[default]` để phân tích link và tải audio; cần Node.js trong `PATH` cho YouTube.
- `ffmpeg` trong `PATH` để chuyển sang ALAC / AAC / MP3 và nhúng ảnh bìa. Định dạng `raw` không cần ffmpeg.
- `mutagen` để đọc tag khi index vào Player.

## 2. Build và kiểm tra

```bash
npm --prefix frontend ci
npm --prefix frontend run build      # tsc -b && vite build → src/auralytica/static/
uv sync --locked --no-default-groups --group test --group browser
uv run --no-sync python -m unittest discover -s tests -v
uv run --no-sync python -m unittest discover -s tests/browser -v
```

Bundle build (`src/auralytica/static/assets/index-*.js|css`) đang được commit. Sau mỗi thay đổi frontend cần build lại và commit cả bundle mới, nếu không bản cài bằng `uv tool install .` sẽ chạy UI cũ.

## 3. Cài đặt

```bash
uv tool install --reinstall .
auralytica
```

## 4. Database và rollback

- Nhánh này nâng schema lên **v7**: thêm cột `download_batches.kind` và bảng `direct_download_items`. Migration chạy tự động khi mở database và chuyển các batch Tải nhanh cũ (đánh dấu bằng `settings.batch_is_direct:{id}`) sang `kind='direct'`.
- **Rollback về commit trước không mở được database đã lên v7**: bản cũ báo `Database schema 7 is newer than supported 6` và dừng. Trước khi cài bản mới, sao lưu database:

  ```bash
  cp ~/.local/share/auralytica/library.sqlite3 ~/.local/share/auralytica/library.sqlite3.v6.bak
  ```

  Muốn quay lại bản cũ thì dừng worker, khôi phục file `.v6.bak`. Các lượt tải tạo sau khi nâng cấp sẽ không có trong bản sao lưu.
- Database ở v6 có thể đã bị Tải nhanh ghi đè title/kênh và đặt `user_group='music'` cho video trùng với lịch sử Takeout. Migration không hoàn tác được những thay đổi đó, vì không còn dữ liệu gốc. Import lại phiên Takeout sẽ khôi phục title/kênh; còn nhóm Nhạc/Còn lại thì cần sửa tay trong Explore.
