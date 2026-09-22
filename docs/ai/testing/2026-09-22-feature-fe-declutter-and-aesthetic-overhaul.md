---
phase: testing
title: Testing Strategy — FE Declutter & Aesthetic Overhaul
description: Kịch bản kiểm thử thị giác, đo lường độ phân giải và chất lượng UX sau khi tái cấu trúc giao diện.
---

# Testing Strategy — FE Declutter & Aesthetic Overhaul

Ngày cập nhật: **2026-09-22**. Tính năng: `fe-declutter-and-aesthetic-overhaul`.

---

## 1. Test Coverage Goals

- **Độ tương thích TypeScript & Build:** 100% component build sạch không lỗi kiểu dữ liệu với Vite + React 19.
- **Tiêu chuẩn Typography:** Không tồn tại bất kỳ class font dưới 12px (`text-[9px]`, `text-[10px]`, `text-[11px]`) trong toàn bộ mã nguồn frontend.
- **Kiểm thử Hồi quy & Ổn định:** Toàn bộ 125 backend unit tests tiếp tục pass (bao gồm bài test quét phát hiện file đã tải trong thư mục con `Apple Music/`).

---

## 2. Test Scenarios

### 2.1. Explore View & SongCard
- [x] `T-FE-SONG-01`: Thẻ bài hát hiển thị thumbnail vuông 56x56px, không bị méo tỷ lệ.
- [x] `T-FE-SONG-02`: Tên bài hát hiển thị cỡ chữ 14px (`text-sm font-medium`), ca sĩ 13px (`text-xs`), lượt nghe `text-xs`.
- [x] `T-FE-SONG-03`: Tuyệt đối không còn xuất hiện dòng `Trạng thái: completed` hoặc các mã debug `Flabs` trên thẻ bài hát.
- [x] `T-FE-EXPLORE-01`: Thanh tìm kiếm và bộ lọc trên `ColumnPane` nằm trên 1 hàng ngang duy nhất, chiều cao không vượt quá 52px.
- [x] `T-FE-EXPLORE-02`: Phân trang capsule pill đồng bộ chung `pageSize` cho cả 2 cột Nhạc & Còn lại.
- [x] `T-FE-EXPLORE-03`: Central Transfer Hub `<=>` hoán đổi chéo chính xác giữa 2 nhóm, kèm fallback quick-move.

### 2.2. Download View
- [x] `T-FE-DL-FORMAT-01`: Rút gọn chỉ còn 2 tùy chọn định dạng chính (ALAC Lossless & MP3 320k), không còn văn bản kỹ thuật thừa.
- [x] `T-FE-DL-PRESET-01`: Checkbox làm sạch tên và nhúng thumbnail được mặc định kích hoạt ngầm, không gây rối mắt.
- [x] `T-FE-DL-HUB-01`: Live Player Hub với hero squircle 1:1, equalizer sóng nhạc động khi tải và master progress bar.
- [x] `T-FE-DL-DRAWER-01`: Bảng 500 bài thu gọn mặc định dạng drawer mờ ảo, mở xem mượt mà theo nhu cầu.

### 2.3. Deduplicate View
- [x] `T-FE-DEDUP-01`: Container mở rộng `max-w-7xl`, loại bỏ hoàn toàn khoảng đen thừa 2 bên.
- [x] `T-FE-DEDUP-02`: Responsive Comparison Cards Grid (2-3 cột) đặt các bản thu cạnh nhau trực quan.
- [x] `T-FE-DEDUP-03`: Tương tác 1-Click: Click bất kỳ đâu trên thẻ bài hát để toggle `keep`.

---

## 3. Manual & Visual Quality Checklist
- [x] Giao diện nhìn êm mắt trong phòng tối, không có các đốm sáng chói (No glare spots).
- [x] Tốc độ cuộn trang danh sách 50 bài mượt mà, không giật lag.
- [x] Kích thước chữ dễ đọc ở cự ly làm việc thông thường mà không cần zoom trình duyệt (100% >= 12px).
- [x] Không còn tình trạng quá tải nhận thức (Cognitive Overload Elimination).

