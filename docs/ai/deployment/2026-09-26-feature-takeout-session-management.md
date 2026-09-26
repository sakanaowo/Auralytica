---
phase: deployment
title: Deployment Strategy — Takeout Session Management
description: Hướng dẫn đóng gói và triển khai tính năng quản lý phiên Takeout cho ứng dụng local Auralytica.
---

# Deployment Strategy — Takeout Session Management

Ngày cập nhật: **2026-09-26**. Tính năng: `takeout-session-management`.

---

## 1. Môi trường triển khai

Auralytica là ứng dụng desktop local-first (Python FastAPI + React Vite SPA).
- **Local Application**: Chạy trực tiếp trên máy người dùng tại cổng local (`http://127.0.0.1:8765`).
- **Database**: Tệp SQLite cục bộ (`~/.local/share/auralytica/library.sqlite3` hoặc `--database <path>`).
- **Static Assets**: Frontend React được đóng gói thành tĩnh (`src/auralytica/static/`).

---

## 2. Quy trình Build & Đóng gói

1. **Frontend Production Build**:
   ```bash
   npm --prefix frontend run build
   ```
   Lệnh này tự động biên dịch TypeScript và đóng gói Vite vào thư mục `src/auralytica/static/`.

2. **Backend Validation**:
   ```bash
   uv run pytest tests/test_*.py
   uv run pytest tests/browser/test_session_management_ui.py
   ```

3. **Packaging**:
   Khi đóng gói gói bánh xe Python (`uv build`), các tệp trong `src/auralytica/static/` được đóng gói trực tiếp cùng package.

---

## 3. Khả năng tương thích ngược & Rollback

- **Cơ sở dữ liệu**: Không thay đổi schema DDL mới. Các bảng `imports`, `watch_events`, và `settings` đã có sẵn từ các phiên bản trước.
- **Rollback**: Có thể checkout commit trước mà không làm hỏng dữ liệu SQLite hiện có.
