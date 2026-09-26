---
phase: testing
title: Test Plan & Scenarios — Takeout Session Management
description: Kế hoạch kiểm thử toàn diện các kịch bản quản lý phiên, chuyển đổi phiên an toàn và bảo toàn tiến độ dở dang.
---

# Test Plan & Scenarios — Takeout Session Management

Ngày tạo: **2026-09-26**. Tính năng: `takeout-session-management`. Nhánh: `feature-takeout-session-management`.

---

## 1. Test Scenarios

### Backend Unit & Integration Tests (`tests/test_importer_sessions.py`)
- [x] **Scenario 1:** `GET /api/imports` trả về danh sách tất cả các phiên import, kèm thống kê (`statistics`) và đúng cờ `is_active` của phiên đang chọn.
- [x] **Scenario 2:** `POST /api/imports/{id}/activate` kích hoạt thành công phiên khác, cập nhật `active_import` trong `settings` và cập nhật danh sách phiên.
- [x] **Scenario 3:** `POST /api/imports/{id}/activate` bị từ chối với mã lỗi 409 khi đang có batch tải audio ở trạng thái `queued` hoặc `running` (`assert_review_unlocked`).
- [x] **Scenario 4:** `DELETE /api/imports/{id}` từ chối xóa phiên đang hoạt động (`is_active == True`) với mã lỗi 400 Bad Request.
- [x] **Scenario 5:** `DELETE /api/imports/{id}` xóa thành công phiên lưu trữ không hoạt động, xóa toàn bộ các bản ghi `watch_events` liên quan đến `import_id` đó nhưng bảo toàn các bản ghi trong bảng `videos`.
- [x] **Scenario 6:** Bảo toàn 100% tiến độ: Sửa phân loại video trong Phiên A, chuyển sang Phiên B, quay lại Phiên A thì các phân loại video và trạng thái review vẫn nguyên vẹn.

### Frontend Component & UI Verification
- [x] **Scenario 7:** Trang `01 Import` (`ImportView.tsx`) tải và hiển thị danh sách các phiên hiện có trong CSDL.
- [x] **Scenario 8:** Thẻ Phiên hiện tại (`Active Session Card`) hiển thị nổi bật với badge `Đang hoạt động`, số lượng bài hát và nút sang bước Explore.
- [x] **Scenario 9:** Bấm "Kích hoạt" trên một phiên khác đổi badge Active ngay lập tức và đồng bộ lại thanh header và quy trình.
- [x] **Scenario 10:** Khi `batch_locked = True`, các nút kích hoạt phiên và nút xóa bị vô hiệu hóa kèm cảnh báo rõ ràng.
- [x] **Scenario 11:** Khung kéo thả Takeout mới hoạt động bình thường, sau khi nạp xong danh sách phiên tự động cập nhật thêm phiên mới.

---

## 2. Test Execution Commands

```bash
# Backend unit tests
uv run pytest tests/test_importer_sessions.py tests/test_importer.py

# Full test suite regression check
uv run pytest tests/test_*.py

# Frontend build check
npm --prefix frontend run build

# AI DevKit docs lint check
npx ai-devkit lint --feature takeout-session-management
```

---

## 3. Test Results & Verification Evidence

- **Unit & Integration Tests**: 140/140 passed (`uv run pytest tests/test_*.py`).
- **Browser Acceptance Tests**: 1/1 passed (`uv run pytest tests/browser/test_session_management_ui.py` in 1.45s).
- **Frontend Production Build**: `npm --prefix frontend run build` exit code 0.
- **Documentation Linter**: `npx ai-devkit lint --feature takeout-session-management` 16/16 checks passed.
- **Visual Evidence**: `artifacts/browser-runs/session-management-verified.png`.

