---
phase: deployment
title: Deployment Guide — FE Declutter & Aesthetic Overhaul
description: Quy trình build static bundle frontend và tích hợp vào FastAPI web server.
---

# Deployment Guide — FE Declutter & Aesthetic Overhaul

Ngày cập nhật: **2026-09-22**. Tính năng: `fe-declutter-and-aesthetic-overhaul`.

---

## 1. Build Process
1. Build frontend production:
   ```bash
   npm --prefix frontend run build
   ```
2. Bundle được xuất trực tiếp vào `src/auralytica/static/` gồm `index.html` và thư mục `assets/` (JS & CSS).
3. FastAPI server phục vụ trực tiếp các file tĩnh này từ `src/auralytica/static/`.

---

## 2. Verification Steps
- Chạy lệnh khởi động app local:
  ```bash
  uv run auralytica
  ```
- Truy cập `http://127.0.0.1:8765/` kiểm tra giao diện đã tải bundle mới.
