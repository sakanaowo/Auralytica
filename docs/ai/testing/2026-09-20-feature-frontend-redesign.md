---
phase: testing
title: Testing Strategy — Frontend Redesign
description: Kế hoạch và kịch bản kiểm chứng cho giao diện mới của Auralytica
---

# Testing Strategy — Frontend Redesign

Cập nhật: **2026-09-20**. Tính năng: `frontend-redesign`.

## Test Coverage Goals

- **Kiểm thử Hồi quy Backend:** 100% trong số 116 bài test unit/integration của Python tiếp tục chạy `OK`.
- **Kiểm thử Build tĩnh:** `npm run build` tạo ra đúng bundle trong `src/auralytica/static/` không phát sinh cảnh báo hay lỗi cú pháp.
- **Kiểm thử Luồng Nghiệp vụ Trực tiếp:**
  - Import Takeout folder thành công.
  - Explore Dual-pane: Chọn thẻ 1-chạm, chuyển nhóm hai chiều (Nhạc ⇄ Còn lại).
  - Deduplicate: Hiển thị nhóm trùng, toggle keep/exclude lưu đúng revision.
  - Download: Nhận diện số file cần tải và khởi chạy batch download.

## Test Scenarios

### 1. Build & Tích hợp Server
- [ ] `T-BUILD-01`: Lệnh `npm run build` trong `frontend/` sinh ra `index.html` và thư mục `assets/` bên trong `src/auralytica/static/`.
- [ ] `T-SRV-01`: Khởi chạy server `python -m auralytica --no-browser` thành công, truy cập `http://127.0.0.1:8765/` trả về mã 303/200 và hiển thị giao diện React mới.
- [ ] `T-PY-01`: Chạy `python -m unittest discover -s tests -v` đạt 116/116 tests.

### 2. Dual-Pane Explore
- [ ] `T-EXP-01`: Truy cập `/explore` khi đã có dữ liệu hiển thị cả 2 cột: Cột Nhạc (trái) và Cột Còn lại (phải).
- [ ] `T-EXP-02`: Bấm trực tiếp vào thẻ bài hát kích hoạt trạng thái chọn (Selected highlight), kiểm tra số đếm trên nút `Chuyển đã chọn (N)`.
- [ ] `T-EXP-03`: Bấm nút `Chuyển đã chọn (N)` di chuyển thành công các bài sang cột đối diện, số tổng nhóm cập nhật tức thì.
- [ ] `T-EXP-04`: Tìm kiếm theo tên bài trên cột Nhạc lọc đúng kết quả mà không làm ảnh hưởng cột Còn lại.
- [ ] `T-EXP-05`: Bấm nút `Cập nhật metadata` mở modal kính mờ, xem tiến trình và đóng modal mà không ảnh hưởng danh sách đang duyệt.

### 3. Deduplicate & Download
- [ ] `T-DEDUP-01`: Truy cập `/deduplicate` hiển thị danh sách nhóm bài nghi trùng, kiểm tra checkbox keep/exclude.
- [ ] `T-DL-01`: Truy cập `/download` hiển thị tổng số file cần tải, nút `Tải toàn bộ` hoạt động khi có bài cần tải.

## Manual & UI Verification
- [ ] Kiểm tra giao diện không có bất kỳ emoji hoặc icon trang trí dư thừa ("no sticker").
- [ ] Kiểm tra độ tương phản chữ và hiệu ứng kính mờ (Liquid Glass) trên nền tối.
