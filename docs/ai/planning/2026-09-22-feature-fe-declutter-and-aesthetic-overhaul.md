---
phase: planning
title: Project Planning — FE Declutter & Aesthetic Overhaul
description: Kế hoạch triển khai chi tiết từng task để loại bỏ hoàn toàn quá tải nhận thức trên giao diện người dùng.
---

# Project Planning — FE Declutter & Aesthetic Overhaul

Ngày lập: **2026-09-22**. Tính năng: `fe-declutter-and-aesthetic-overhaul`.

---

## 1. Milestones (Giai đoạn 1: Nền tảng Typography & Thanh lọc dữ liệu)

- [x] **Milestone 1:** Chuẩn hóa Typography & Tinh giản Thẻ bài hát (`SongCard.tsx` & `ColumnPane.tsx`)
- [x] **Milestone 2:** Thanh lọc Màn hình Tải (`DownloadView.tsx`) & So sánh trùng lặp (`DedupView.tsx`)
- [x] **Milestone 3:** Kiểm thử, Build Production & Nghiệm thu thị giác

---

## 2. Milestones (Giai đoạn 2: Nâng cấp Trải nghiệm Tối giản & Layout Cảm xúc)

- [x] **Milestone 4 (Page 02 — Explore & Dual-Pane):**
  - [x] **Task 4.1:** Xóa bỏ văn bản mô tả thừa trên ExploreView.
  - [x] **Task 4.2:** Ẩn nút "Cập nhật Metadata & Phân loại" khỏi màn hình chính, note `// TODO: Collect user correction & implicit labeling data for future AI fine-tuning`.
  - [x] **Task 4.3:** Đồng bộ `pageSize` chung (25/50/100) cho cả 2 cột Nhạc và Còn lại.
  - [x] **Task 4.4:** Thiết kế thanh phân trang dạng capsule pill thanh lịch ở footer chung.
  - [x] **Task 4.5:** Theo yêu cầu tinh giản, loại bỏ hoàn toàn thanh dock và nút chuyển đổi trung tâm `<=>`; gom toàn bộ thao tác chuyển sang Action Row của từng cột (`Chuyển sang Còn lại (X)` / `Thêm vào Nhạc (X)`) và nút chuyển nhanh trực tiếp trên từng thẻ bài hát. Tích hợp bộ chọn `pageSize` vào footer của từng pane.

- [x] **Milestone 5 (Page 03 — Deduplicate Comparison Cards):**
  - [x] **Task 5.1:** Hỗ trợ tương tác 1-Click: Click bất kỳ đâu trên thẻ bài hát để toggle `keep`, không bắt buộc bấm checkbox.
  - [x] **Task 5.2:** Mở rộng không gian hiển thị (`max-w-7xl` / adaptive full-width) xóa bỏ khoảng đen thừa 2 bên.
  - [x] **Task 5.3:** Triển khai **Phương án 1 (Responsive Comparison Cards)**: Dàn các bản thu của từng nhóm theo hàng ngang cạnh nhau (grid 2-3 cột) để so sánh trực diện.

- [x] **Milestone 6 (Page 04 — Download Apple Music Live Player Hub):**
  - [x] **Task 6.1:** Bỏ 2 checkbox "Làm sạch tên file" và "Nhúng thumbnail" -> mặc định luôn kích hoạt `true`.
  - [x] **Task 6.2:** Xóa các text kỹ thuật ("In-stream FFmpeg Pipeline", mô tả dài dòng), chỉ giữ đúng 2 thẻ định dạng: **Lossless (ALAC)** và **MP3 (320k)**.
  - [x] **Task 6.3:** Thiết kế **Apple Music Live Player Hub**: Hero card hiển thị bài hát đang tải với hiệu ứng sống động, thanh tiến độ tổng quan lớn êm dịu, chip cảnh báo lỗi nhỏ gọn.
  - [x] **Task 6.4:** Chuyển danh sách bài hát chi tiết thành collapsible drawer/accordion mờ ảo phía dưới (mặc định thu gọn, chỉ mở khi người dùng muốn soi chi tiết).

- [x] **Milestone 7 (Build, Test & Final Sign-off):**
  - [x] **Task 7.1:** `npm --prefix frontend run build` kiểm tra sạch 100% build (✓ built in 779ms).
  - [x] **Task 7.2:** `uv run pytest tests/test_*.py` kiểm tra 124 unit tests (124 passed in 5.31s).
  - [x] **Task 7.3:** Nghiệm thu trải nghiệm thực tế.

---

## 3. Milestones (Giai đoạn 3: No-Scroll Pagination, Height Compact & Smart Disk Inspection)

- [x] **Milestone 8 (UX Ergonomics & Intelligent Existing File Detection):**
  - [x] **Task 8.1:** Đưa thanh chuyển trang (`← X/Y →`) và chọn số bài lên ngay đầu cột (Action Row) tại `ColumnPane.tsx`, xóa bỏ hoàn toàn footer dưới cùng để người dùng không cần cuộn trang.
  - [x] **Task 8.2:** Khóa viewport height `h-[calc(100vh-61px)]` tại `AppShell.tsx` chống tràn / cắt search bar.
  - [x] **Task 8.3:** Nâng cấp `_scan_disk_for_candidates` và `eligible_snapshot` tại `batches.py` quét toàn bộ thư mục đích và thư mục con (`Apple Music/`) để tự động nhận diện 514+ file đã có sẵn, chỉ tải 9 bài còn thiếu.
  - [x] **Task 8.4:** Thêm nút "↻ Quét lại thư mục" và nút tải thông minh hiển thị số bài còn thiếu tại `DownloadView.tsx`.
  - [x] **Task 8.5:** Khôi phục thumbnail squircle 56x56px (`w-14 h-14`) chuẩn Apple Music trên `SongCard.tsx`, đổi bộ chọn số bài thành `[10, 15, 25, 50]` với mặc định 10 bài/trang giúp danh sách vừa khít màn hình không cần cuộn.
  - [x] **Task 8.6:** Kiểm thử toàn diện: Frontend build sạch (957ms) & 124/124 backend tests pass.

- [x] **Milestone 9 (Removal of Page 05 Apple Music):**
  - [x] **Task 9.1:** Xóa bỏ bước 05 khỏi thanh Stepper và Navigation Header tại `AppShell.tsx`.
  - [x] **Task 9.2:** Rút gọn router và loại bỏ `ConvertView` trong `App.tsx`, cập nhật kiểu `Step = 'import' | 'explore' | 'deduplicate' | 'download'`.
  - [x] **Task 9.3:** Xóa prop `onNavigateConvert` và nút điều hướng thừa tại `DownloadView.tsx`.
  - [x] **Task 9.4:** Xóa sạch thư mục mã nguồn `frontend/src/features/convert/`.
  - [x] **Task 9.5:** Kiểm thử và build production: `npm --prefix frontend run build` sạch (783ms, giảm 16kB bundle) & 124 backend tests pass.




