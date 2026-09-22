---
phase: requirements
title: Requirements — FE Declutter & Aesthetic Overhaul (Anti-Cognitive Overload)
description: Yêu cầu tinh giản giao diện toàn diện, giải phóng quá tải nhận thức, chuẩn hóa typography và áp dụng triết lý thiết kế Apple Music.
---

# Requirements — FE Declutter & Aesthetic Overhaul (Anti-Cognitive Overload)

Ngày khởi tạo: **2026-09-22**. Tính năng: `fe-declutter-and-aesthetic-overhaul`.

---

## 1. Problem Statement

### Vấn đề cốt lõi:
Người dùng và các Persona (FE Engineer, User, UI/UX Designer, Apple Designer) đều xác nhận giao diện hiện tại đang bị **Cognitive Overload (Quá tải nhận thức) trầm trọng** trên tất cả các màn hình:
1. **Font chữ bị thu nhỏ cực đoan (`text-[9px]`, `text-[10px]`, `text-[11px]`) nhưng nhồi nhét quá nhiều dữ liệu phụ**:
   - Thẻ bài hát ở bước Explore nhồi nhét 5 tầng thông tin kỹ thuật: thumbnail méo, 2 dòng tên bài, kênh, lượt nghe, lý do phân loại (`Flabs:0 · Kênh Topic · Đã chuyển tay`), và dòng chữ thừa `Trạng thái tải: completed`.
   - Bước Deduplicate chứa các đoạn text dài giải thích thuật toán regex khiến người dùng rối trí.
   - Bước Download hiển thị cùng lúc 3 khối banner cảnh báo (Thông tin batch, Gợi ý Apple Music, Hộp đỏ chẩn đoán lỗi) chiếm 50% màn hình.
2. **Thất bại về Phân tầng thị giác (Visual Hierarchy)**:
   - Thẻ chọn định dạng (M4A ALAC, AAC, MP3) khi được chọn bị đảo màu sang **trắng tinh (`bg-zinc-100 text-zinc-900`)**, tạo thành mảng sáng chói lóa (Glare effect) trên nền tối, lấn át nút hành động chính.
   - Không có khoảng thở (Breathing room), hội chứng "Hộp lồng trong Hộp" (Container Fatigue) với quá nhiều đường viền trắng (`border-white/10`).

---

## 2. Goals & Objectives

### Mục tiêu chính (Primary Goals):
1. **Quy tắc "Cấm font dưới 12px"**: Chuẩn hóa toàn bộ typography hệ thống. Font nhỏ nhất cho text nội dung là `12px` (`text-xs`), tên bài hát `14px` (`text-sm font-medium`), tiêu đề `16px - 20px`.
2. **Thanh lọc Thẻ bài hát (SongCard Minimalism)**: Một thẻ bài hát chỉ hiển thị 3 thông tin thiết yếu:
   - Ảnh bìa vuông chuẩn tỷ lệ 1:1 (`56x56px`), bo góc squircle (`rounded-xl`).
   - Tên bài hát sạch sẽ (14px, đậm vừa, đã lọc bớt rác YouTube).
   - Tên ca sĩ / Kênh (13px, xám nhạt).
   - *Loại bỏ vĩnh viễn*: `Trạng thái tải: completed`, các mã kỹ thuật `Flabs`, `Topic`.
3. **Thu gọn Bảng điều khiển Tải (Download Dashboard)**:
   - Thay thế 3 banner xếp chồng bằng **1 thanh tiến trình thanh thoát duy nhất**: `● Đã tải 520 / 523 bài (99.4%) · [Thử lại 3 bài lỗi]`.
   - Đưa chi tiết lỗi vào tab con "Thất bại (3)", áp dụng nguyên lý Tiết lộ lũy tiến (Progressive Disclosure).
   - Thiết kế lại Thẻ định dạng theo phong cách **Liquid Glass Pill Selector**: Phát sáng viền xanh Apple nhẹ nhàng (`border-sky-400/50 bg-sky-500/10 text-white`), không đảo màu trắng xóa.
4. **Tối ưu Bước 02 (Explore) & 03 (Deduplicate)**:
   - Gom hàng search và filter thành 1 hàng compact duy nhất để tăng không gian cuộn.
   - Tinh giản text giải thích thuật toán ở Deduplicate, tập trung vào so sánh bản thu.

### Non-Goals (Ngoài phạm vi):
- Không thay đổi logic backend, SQLite database schema hoặc các API REST hiện có.
- Không xóa bỏ trang 05 Apple Music (giữ nguyên để người dùng xử lý kho 493 file cũ).

---

## 3. User Stories & Use Cases

- **US-01 (Duyệt nhạc nhanh & không mỏi mắt):** Là người sưu tầm nhạc, tôi muốn lướt qua danh sách bài hát ở bước Explore một cách nhẹ nhàng, mắt nhận diện ngay ảnh bìa và tên bài hát mà không bị phân tâm bởi các thông số debug kỹ thuật.
- **US-02 (Tải nhạc tự tin & êm mắt):** Là người dùng trong phòng tối, tôi muốn chọn định dạng M4A ALAC mà không bị một mảng trắng chói lòa chiếu vào mắt, và không bị hoảng sợ bởi các hộp cảnh báo đỏ rực khi tỷ lệ tải thành công đã đạt trên 99%.
- **US-03 (So sánh bản trùng rõ ràng):** Là người yêu nhạc, tôi muốn ở bước Deduplicate thấy rõ sự khác biệt giữa 2 bài hát trùng nhau một cách ngắn gọn thay vì đọc các đoạn văn giải thích thuật toán.

---

## 4. Success Criteria

1. **Typography**: 100% text nội dung đọc có kích thước $\ge 12\text{px}$. Không còn class `text-[9px]`, `text-[10px]`, `text-[11px]`.
2. **Decluttering Metric**: Giảm ít nhất 50% số lượng từ chữ thừa trên mỗi thẻ bài hát ở Explore.
3. **Visual Balance**: Màn hình Download không có quá 1 banner cảnh báo tại cùng một thời điểm. Thẻ format active chuyển sang phong cách kính ánh xanh (`sky-500`), tương phản êm dịu.
4. **Build & Quality**: `npm run build` thành công, 0 warning TypeScript, giao diện responsive mượt mà từ màn hình 1280px đến 2K/4K.

---

## 5. Constraints & Assumptions

- Tiếp tục sử dụng Tailwind CSS v4 và React 19 có sẵn trong dự án.
- Tông màu chủ đạo: Dark Obsidian / Deep Glass (`#000000` / `#09090b` với viền mờ `white/5` - `white/10`).
