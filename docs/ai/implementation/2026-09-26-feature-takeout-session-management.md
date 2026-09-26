---
phase: implementation
title: Implementation Guide — Takeout Session Management
description: Tài liệu chi tiết các thay đổi mã nguồn, kiến trúc đa phiên, bảo toàn dữ liệu dở dang và tích hợp an toàn.
---

# Implementation Guide — Takeout Session Management

Ngày cập nhật: **2026-09-26**. Tính năng: `takeout-session-management`.

---

## 1. Kiến trúc & Cấu trúc mã nguồn

Tính năng quản lý phiên Takeout được triển khai xuyên suốt hai lớp:

### 1.1 Backend Engine (`src/auralytica/`)
- [`importer.py`](file:///home/sakana/Code/Auralytica/src/auralytica/importer.py):
  - `get_import_sessions(db)`: Quét bảng `imports`, tổng hợp thống kê, đếm số video `music` vs `rest` riêng biệt cho từng phiên, và đánh dấu phiên `is_active`.
  - `activate_import_session(db, import_id)`: Kiểm tra tồn tại, kích hoạt phiên qua `set_setting(db, 'active_import', str(import_id))` với điều kiện `assert_review_unlocked(db)` an toàn.
  - `delete_import_session(db, import_id)`: Kiểm tra `assert_review_unlocked(db)`, cấm xóa phiên active (HTTP 400), xóa cascade có thứ tự phụ thuộc khóa ngoại từ `classification_previews`, `dedup_members`, `dedup_groups`, `dedup_runs`, `metadata_cache`, `metadata_items`, `audit_events`, `audit_runs`, `watch_events` đến `imports`.
- [`web.py`](file:///home/sakana/Code/Auralytica/src/auralytica/web.py):
  - `GET /api/imports`: Trả về danh sách phiên (`items`, `sessions`, `active_import`, `batch_locked`).
  - `POST /api/imports/{import_id}/activate`: Kích hoạt phiên.
  - `DELETE /api/imports/{import_id}`: Xóa phiên không active.

### 1.2 Frontend SPA (`frontend/src/`)
- [`api/types.ts`](file:///home/sakana/Code/Auralytica/frontend/src/api/types.ts):
  - Định nghĩa `ImportSession`, `ImportSessionCounts`, `ImportSessionStatistics`, và `ImportSessionsResponse`.
- [`api/client.ts`](file:///home/sakana/Code/Auralytica/frontend/src/api/client.ts):
  - Bổ sung `api.getImports()`, `api.activateImport(id)`, `api.deleteImport(id)`.
- [`features/import/ImportView.tsx`](file:///home/sakana/Code/Auralytica/frontend/src/features/import/ImportView.tsx):
  - **Active Session Card**: Thẻ xanh emerald hiển thị phiên đang hoạt động, badge `Đang hoạt động`, nguồn Takeout, thống kê tổng video, video Nhạc, video Còn lại, và nút `Tiếp tục xem dữ liệu →`.
  - **Saved Sessions List**: Danh sách các phiên còn lại kèm nút `Kích hoạt phiên này` và icon `Xóa`.
  - **In-progress Safety**: Khi có đợt tải chạy ngầm (`batch_locked === true`), toàn bộ nút chuyển/xóa phiên bị disable kèm banner cảnh báo bảo vệ tiến trình tải.
  - **New Import Dropzone**: Khu vực kéo thả / chọn folder Takeout độc lập (nút `+ Nạp phiên mới` có thể đóng/mở khi đã có phiên).

---

## 2. Bảo toàn tiến trình dở dang (In-Progress State Preservation)

Quy tắc bảo toàn dữ liệu được cam kết:
1. **Phân loại thủ công (`user_group`), nhãn kênh (`channel_decisions`), và danh sách giữ trùng (`dedup_members`)** được lưu cố định trong SQLite.
2. Các bước sau (`Explore`, `Deduplicate`, `Download`) truy vấn dữ liệu lọc theo `WHERE import_id = active_import`.
3. Khi người dùng chuyển đổi qua lại giữa các phiên, dữ liệu của từng phiên được giữ nguyên 100%, không bị reset hay đè lẫn nhau.
4. Nạp một folder Takeout mới chỉ tạo một dòng `imports` mới và chèn các `watch_events` tương ứng với `import_id` mới.

---

## 3. Kiểm thử & Đảm bảo chất lượng

1. **Unit Test Backend**: [`tests/test_importer_sessions.py`](file:///home/sakana/Code/Auralytica/tests/test_importer_sessions.py) kiểm thử 6 kịch bản trọng yếu (empty vs populated, activate, block on batch busy, reject active session deletion, cascade deletion, và review preservation). Toàn bộ 140/140 unit test của backend đạt kết quả Passed.
2. **Browser Acceptance Test**: [`tests/browser/test_session_management_ui.py`](file:///home/sakana/Code/Auralytica/tests/browser/test_session_management_ui.py) sử dụng Playwright kiểm thử thực tế trên Chromium luồng trọn vẹn: Nạp phiên #1 → duyệt dữ liệu → nạp phiên #2 → chuyển về phiên #1 → xóa phiên #2 với popup xác nhận → chụp screenshot thành công.
