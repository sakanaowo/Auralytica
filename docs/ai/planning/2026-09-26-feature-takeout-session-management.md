---
phase: planning
title: Project Planning & Task Breakdown — Takeout Session Management
description: Phân rã công việc chi tiết thành các Milestone và Tasks khả thi cho tính năng quản lý phiên Takeout đa phiên.
---

# Project Planning & Task Breakdown — Takeout Session Management

Ngày tạo: **2026-09-26**. Tính năng: `takeout-session-management`. Nhánh: `feature-takeout-session-management`.

---

## 1. Milestones Overview

- [x] **Milestone 1: Backend Core Engine & REST Endpoints** — Xây dựng các hàm quản lý phiên trong `importer.py`, endpoints `/api/imports` trong `web.py`, và unit test backend suite.
- [x] **Milestone 2: Frontend Data Models & API Integration** — Định nghĩa TypeScript interfaces trong `types.ts`, bổ sung các hàm gọi API trong `client.ts`.
- [x] **Milestone 3: UI Redesign & Safety Controls (`ImportView.tsx`)** — Thẻ Phiên hiện tại (`Active Session Card`), danh sách phiên lưu trữ kèm nút Kích hoạt & Xóa, cơ chế khóa bảo vệ khi có batch tải đang chạy, và khu vực nạp phiên mới.
- [x] **Milestone 4: End-to-End Verification & Regression Testing** — Kiểm thử toàn diện unit test, build frontend, xác minh Playwright trên trình duyệt thực tế, và linting docs.

---

## 2. Detailed Task Breakdown

### Milestone 1: Backend Core Engine & REST Endpoints

- [x] **Task 1.1: Core Session Functions (`src/auralytica/importer.py`)**
  - *Mô tả:* Xây dựng các hàm:
    - `get_import_sessions(db)`: Truy vấn bảng `imports`, trích xuất thống kê, tính số lượng video Nhạc/Còn lại, và xác định cờ `is_active`.
    - `activate_import_session(db, import_id)`: Kiểm tra an toàn (`assert_review_unlocked(db)`), cập nhật `active_import` trong `settings`.
    - `delete_import_session(db, import_id)`: Chặn xóa phiên active, kiểm tra batch lock, xóa an toàn các bản ghi `watch_events` và `imports`.
  - *Kiểm chứng:* Unit test kiểm tra logic hàm độc lập.
- [x] **Task 1.2: REST Endpoints (`src/auralytica/web.py`)**
  - *Mô tả:* Bổ sung các routes:
    - `GET /api/imports`: Trả về danh sách phiên và `active_import`.
    - `POST /api/imports/{import_id}/activate`: Kích hoạt phiên.
    - `DELETE /api/imports/{import_id}`: Xóa phiên không active.
  - *Kiểm chứng:* FastAPI TestClient gửi requests và xác nhận status code / headers / body.
- [x] **Task 1.3: Backend Test Suite (`tests/test_importer_sessions.py`)**
  - *Mô tả:* Viết test suite bao quát 100% các kịch bản: liệt kê phiên, kích hoạt phiên, chặn chuyển khi batch busy (409), chặn xóa phiên active (400), xóa phiên thành công, và bảo toàn phân loại video khi chuyển đổi qua lại giữa các phiên.
  - *Kiểm chứng:* `uv run pytest tests/test_importer_sessions.py`.

### Milestone 2: Frontend Data Models & API Integration

- [x] **Task 2.1: TypeScript Models (`frontend/src/api/types.ts`)**
  - *Mô tả:* Bổ sung các kiểu dữ liệu `ImportSession`, `ImportSessionStatistics`, `ImportSessionsResponse`.
  - *Kiểm chứng:* TypeScript compiler không báo lỗi type.
- [x] **Task 2.2: API Client Methods (`frontend/src/api/client.ts`)**
  - *Mô tả:* Bổ sung các method `getImports()`, `activateImport(id)`, `deleteImport(id)`.
  - *Kiểm chứng:* Gọi API trong frontend nhận đúng kiểu dữ liệu.

### Milestone 3: UI Redesign & Safety Controls (`ImportView.tsx`)

- [x] **Task 3.1: Active Session Display**
  - *Mô tả:* Thẻ hiển thị phiên đang hoạt động với viền xanh emerald, badge `Đang hoạt động`, số lượng video phân loại, và nút bấm điều hướng nhanh sang bước Explore.
  - *Kiểm chứng:* Kiểm tra hiển thị thông tin khớp với CSDL.
- [x] **Task 3.2: Saved Sessions List**
  - *Mô tả:* Bảng danh sách các phiên còn lại, nút bấm "Kích hoạt phiên này" chuyển đổi phiên tức thì, và nút "Xóa" kèm popup xác nhận.
  - *Kiểm chứng:* Bấm nút chuyển phiên làm mới toàn bộ trang và header.
- [x] **Task 3.3: In-Progress Safety & Batch Lock Controls**
  - *Mô tả:* Khi `batchLocked === true`, disable các nút kích hoạt và xóa phiên, hiển thị tooltip giải thích lý do bảo vệ đợt tải.
  - *Kiểm chứng:* Kiểm tra trạng thái disable khi batch tải đang chạy.
- [x] **Task 3.4: New Import Collapsible Dropzone**
  - *Mô tả:* Khu vực kéo thả folder Takeout mới độc lập, tự động nạp phiên mới và kích hoạt ngay sau khi import thành công.
  - *Kiểm chứng:* Thử nạp file Takeout mới tạo phiên mới mà không làm mất phiên cũ.

### Milestone 4: End-to-End Verification & Regression Testing

- [x] **Task 4.1: Regression Testing**
  - *Mô tả:* Chạy toàn bộ test suite backend `uv run pytest tests/test_*.py`.
  - *Kiểm chứng:* 100% passed không regression.
- [x] **Task 4.2: Frontend Production Build**
  - *Mô tả:* `npm --prefix frontend run build` kiểm tra type check và đóng gói bundle.
  - *Kiểm chứng:* Build exit 0 không warning/error.
- [x] **Task 4.3: Real Browser E2E Verification**
  - *Mô tả:* Chạy Playwright tự động kiểm thử thao tác nạp trang, xem danh sách phiên, chuyển phiên và bảo toàn trạng thái.
  - *Kiểm chứng:* Log kết quả Playwright test.
- [x] **Task 4.4: AI DevKit Docs Lint**
  - *Mô tả:* `npx ai-devkit lint --feature takeout-session-management`.
  - *Kiểm chứng:* 16/16 checks passed.
