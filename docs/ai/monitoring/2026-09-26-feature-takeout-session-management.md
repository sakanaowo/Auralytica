---
phase: monitoring
title: Monitoring & Observability — Takeout Session Management
description: Cơ chế giám sát, xử lý lỗi và tính toàn vẹn phiên Takeout cho ứng dụng local Auralytica.
---

# Monitoring & Observability — Takeout Session Management

Ngày cập nhật: **2026-09-26**. Tính năng: `takeout-session-management`.

---

## 1. Giám sát trạng thái phiên & Khóa an toàn

- **Khóa tác vụ chạy ngầm (`batch_locked`)**:
  - API `GET /api/imports` tự động kiểm tra `SELECT COUNT(*) FROM download_batches WHERE status IN ('queued', 'running')`.
  - Nếu `batch_locked === true`, UI hiển thị banner cảnh báo màu hổ phách và vô hiệu hóa chuyển/xóa phiên.
- **Tính toàn vẹn khóa ngoại (Foreign Key Cascades)**:
  - Hàm `delete_import_session` xóa tuần tự theo thứ tự phụ thuộc bảng để tránh lỗi khóa ngoại trong SQLite (`PRAGMA foreign_keys = ON`).

---

## 2. Ghi nhận lỗi & Thông báo cho người dùng

- **HTTP 409 Conflict**: Trả về khi người dùng kích hoạt hoặc xóa phiên trong khi có batch tải đang chạy. Frontend hiển thị thông báo lỗi rõ ràng.
- **HTTP 400 Bad Request**: Trả về khi người dùng cố gắng xóa phiên đang Active.
- **HTTP 404 Not Found**: Trả về khi ID phiên không tồn tại trong CSDL.
- **Audit Trails**: Các sự kiện phân loại, chuyển nhóm bài hát và deduplication vẫn được ghi nhận vào `audit_events` và `audit_runs`.
