---
phase: planning
title: Project Planning & Task Breakdown — Frontend Redesign
description: Kế hoạch triển khai chi tiết từng task cho việc tái thiết kế Frontend Auralytica
---

# Project Planning & Task Breakdown — Frontend Redesign

Cập nhật: **2026-09-20**. Tính năng: `frontend-redesign`.

## Milestones

- [ ] **Milestone 1 (FE-01): Khởi tạo Scaffold & App Shell**
  - Dựng project Vite + React 19 + TypeScript + Tailwind CSS trong `frontend/`.
  - Cấu hình output build vào `src/auralytica/static/`.
  - Viết API Client, types cho toàn bộ endpoint backend và App Shell (thanh điều hướng text 4 bước).
- [ ] **Milestone 2 (FE-02): Màn Explore Dual-Pane & Tương tác 1-Click Select**
  - Dựng `SongCard` với ảnh thumbnail 16:9 sắc nét, typography tối giản, bấm cả thẻ để chọn.
  - Dựng `ColumnPane` cho cả 2 bên (Nhạc và Còn lại) kèm tìm kiếm, bộ lọc, phân trang và chuyển bài tức thì.
  - Dựng `MetadataSheet` modal để chạy metadata và xem trước phân loại mà không chiếm diện tích màn hình.
- [ ] **Milestone 3 (FE-03): Màn Import & Deduplicate**
  - Dựng `ImportView`: Vùng kéo thả folder Takeout, đọc file và dialog chọn nguồn lịch sử.
  - Dựng `DedupView`: Danh sách nhóm bài nghi trùng, đối chiếu bản thu, gạt keep/exclude và ghép alias thủ công.
- [ ] **Milestone 4 (FE-04): Màn Download & Hoàn thiện Thẩm mỹ Apple Pro**
  - Dựng `DownloadView`: Dashboard tải audio, progress bar, danh sách bài tải real-time và nút Pause/Resume/Retry.
  - Chuẩn hóa toàn bộ hiệu ứng Liquid Glass trung tính, kiểm tra responsive trên mọi độ phân giải.
- [ ] **Milestone 5 (FE-05): Đóng gói, Kiểm thử & Nghiệm thu**
  - Build static bundle hoàn chỉnh.
  - Chạy toàn bộ 116 unit tests của backend để đảm bảo không có regression.
  - Kiểm tra trải nghiệm thực tế với server FastAPI đang chạy.

## Task Breakdown

### Phase 1: Foundation (Milestone 1)
- [ ] **Task 1.1:** Khởi tạo thư mục `frontend/`, cấu hình Vite, React 19, TypeScript, Tailwind CSS v4.
- [ ] **Task 1.2:** Cấu hình `vite.config.ts` để build ra `src/auralytica/static/` (giữ tương thích file phục vụ của FastAPI).
- [ ] **Task 1.3:** Xây dựng `api/client.ts` và `api/types.ts` bám sát toàn bộ API backend trong `src/auralytica/web.py`.
- [ ] **Task 1.4:** Dựng `AppShell.tsx`: Header text-driven, Stepper 4 bước (`01 Import · 02 Explore · 03 Deduplicate · 04 Download`), status badge.

### Phase 2: Explore Dual-Pane (Milestone 2)
- [ ] **Task 2.1:** Dựng `SongCard.tsx`: Thumbnail 16:9, typography 2 dòng, cơ chế 1-click select và nút chuyển nhanh khi hover.
- [ ] **Task 2.2:** Dựng `ColumnPane.tsx`: Search bar phẳng, filter dropdown, thanh chọn bài và nút chuyển hàng loạt.
- [ ] **Task 2.3:** Dựng `ExploreView.tsx`: Bố cục chia đôi 50/50, kết nối React Query và xử lý optimistic move.
- [ ] **Task 2.4:** Dựng `MetadataSheet.tsx`: Hộp thoại kính mờ chạy tiến trình metadata và xem trước bảng phân loại.

### Phase 3: Import & Deduplicate (Milestone 3)
- [ ] **Task 3.1:** Dựng `ImportView.tsx`: Xử lý kéo thả folder Takeout qua File System Access / webkitGetAsEntry và dialog chọn nguồn.
- [ ] **Task 3.2:** Dựng `DedupView.tsx`: Thẻ nhóm trùng, so sánh phiên bản, lưu revision selection và form xác nhận alias thủ công.

### Phase 4: Download & Polish (Milestone 4)
- [ ] **Task 4.1:** Dựng `DownloadView.tsx`: Hiển thị số file cần tải, chọn thư mục lưu, bảng danh sách lượt tải và nút điều khiển.
- [ ] **Task 4.2:** Tinh chỉnh CSS Liquid Glass (Neutral Dark Zinc, viền 1px tinh xảo, scrollbar mờ).

### Phase 5: Testing & Acceptance (Milestone 5)
- [ ] **Task 5.1:** Chạy `npm run build` và kiểm tra cấu trúc file tạo ra trong `src/auralytica/static/`.
- [ ] **Task 5.2:** Chạy test suite Python `python -m unittest discover -s tests -v`.
- [ ] **Task 5.3:** Cập nhật tài liệu `PROJECT_DASHBOARD.md` và nghiệm thu hoàn thành.

## Dependencies

- Node.js ≥ 20 (Hiện tại: v24.19.0).
- Python 3.11+ với SQLite3.
- Fast-forward tương thích với `master`.

## Risks & Mitigation

- **Rủi ro:** Kích thước bundle static có thể lớn nếu cài quá nhiều thư viện.
  - *Giải pháp:* Giữ dependencies tối thiểu (React, React-DOM, TanStack Query, Tailwind), không cài icon pack cồng kềnh.
- **Rủi ro:** Xung đột routing giữa client SPA và server FastAPI khi F5 ở `/explore`, `/deduplicate`, `/download`.
  - *Giải pháp:* Backend FastAPI đã có sẵn route phục vụ `index.html` cho cả 4 đường dẫn này ([`web.py#L213-L218`](file:///home/sakana/Code/Auralytica/src/auralytica/web.py#L213-L218)).
