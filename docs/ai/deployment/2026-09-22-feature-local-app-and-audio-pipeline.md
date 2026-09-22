---
phase: deployment
title: Deployment Strategy — In-Stream Audio Pipeline & Metadata Embedding
description: Hướng dẫn đóng gói và triển khai bản cập nhật luồng tải in-stream và nhúng metadata bài hát.
---

# Deployment Strategy — In-Stream Audio Pipeline & Metadata Embedding

Cập nhật: **2026-09-22**. Tính năng: `local-app-and-audio-pipeline`.

---

## 1. Local Build & Packaging
- **Frontend SPA:**
  ```bash
  cd frontend
  npm run build
  ```
  Vite sẽ biên dịch toàn bộ bundle và đặt vào `src/auralytica/static/`.
- **Python Wheel:**
  Hệ thống chạy trên `uv` và Python 3.11+, không cần phụ thuộc bên ngoài ngoài FFmpeg.

## 2. Verification Steps
1. Khởi động server: `uv run auralytica`
2. Truy cập `http://localhost:8765/download`
3. Kiểm tra các định dạng tải hiển thị: M4A ALAC, M4A AAC, MP3, Nguyên bản.
