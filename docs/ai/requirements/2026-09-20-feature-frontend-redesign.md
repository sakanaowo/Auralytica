---
phase: requirements
title: Requirements — Tái thiết kế Frontend Auralytica
description: Yêu cầu chi tiết cho việc thiết kế lại Frontend theo phong cách Apple Pro Liquid Glass, Dual-Pane Explore và kiến trúc React SPA
---

# Requirements — Tái thiết kế Frontend Auralytica

Cập nhật: **2026-09-20**. Tính năng: `frontend-redesign`.

## Problem Statement

- **Hiện trạng:** Giao diện hiện tại trong `src/auralytica/static/` sử dụng Vanilla JS thao tác DOM trực tiếp, gom toàn bộ 4 bước vào một file `index.html` và chuyển đổi hiển thị bằng thuộc tính `hidden`.
- **Trải nghiệm duyệt nhạc (Explore) bị nghẽn:** Explore là màn hình trọng tâm mà người dùng dành nhiều thời gian nhất để duyệt và nhặt bài. Tuy nhiên, bảng "Còn lại" bị thu gọn bên dưới hoặc hiển thị đơn điệu, không thể so sánh và chuyển đổi bài nhanh chóng.
- **Thẩm mỹ và tương tác:** Giao diện cũ mang phong cách bảng quản trị (admin table) thô sơ, checkbox nhỏ khó bấm, thiếu điểm nhấn thị giác bằng hình ảnh thumbnail, chưa mang lại trải nghiệm của một ứng dụng âm nhạc cao cấp. Người dùng yêu cầu phong cách **macOS Liquid Glass / Apple Pro Apps** gọn gàng ("neat"), chuyên nghiệp, nói không với các icon trang trí lòe loẹt hay emoji kiểu "tủ lạnh dán sticker".

## Goals & Objectives

### Primary Goals
1. **Kiến trúc Hiện đại:** Xây dựng lại Frontend bằng **React 19 + Vite + Tailwind CSS + TanStack Query**, đóng gói tĩnh trực tiếp vào `src/auralytica/static/` để FastAPI phục vụ nguyên bản.
2. **Ngôn ngữ Thiết kế Apple Pro Liquid Glass:**
   - Gam màu xám/đen trung tính (Neutral Dark Zinc palette: `#09090b`, `#18181b`, `#27272a`).
   - Kính mờ chiều sâu (`backdrop-blur-xl bg-zinc-900/40 border border-zinc-800/80`).
   - **Tối giản icon tuyệt đối:** Điều khiển bằng Text rõ nghĩa (`Chuyển`, `Chọn tất cả`, `Lấy metadata`), chỉ dùng ký tự mũi tên tối giản (`←`, `→`).
3. **Explore Dual-Pane Split View:**
   - Màn Explore chia đôi 50/50: Cột trái là **Nhạc đã nhận diện**, cột phải là **Còn lại**.
   - Cả hai cột đều có thanh tìm kiếm tức thì, bộ lọc lý do/sắp xếp, phân trang và thanh tác vụ chọn độc lập.
4. **Thẻ Bài Hát (Song Card) & 1-Click Select:**
   - Ảnh thumbnail 16:9 sắc nét, bo góc tinh gọn.
   - Bấm vào bất kỳ đâu trên thẻ để chọn (Selected state viền sáng và nền nổi bật tinh tế).
   - Nút chuyển nhanh 1-chạm xuất hiện khi hover.
5. **Giữ nguyên 100% hợp đồng Backend:**
   - Không thay đổi schema SQLite hay các endpoint REST API hiện có.
   - Hỗ trợ đầy đủ xử lý khóa batch (`batch_locked`), concurrency revision (`RevisionConflict`), 63 MiB upload limit.

### Non-Goals
- Không thêm các icon, emoji trang trí thừa thãi.
- Không chia thêm panel preview thứ 3 bên phải màn Explore (giữ trọn 100% không gian cho 2 cột duyệt bài).
- Không thay đổi logic phân loại hoặc tải audio của Backend.

## User Stories & Use Cases

- **US01 - Điều hướng Workflow:** Là người dùng, tôi muốn thấy thanh điều hướng 4 bước (`01 Import · 02 Explore · 03 Deduplicate · 04 Download`) rõ ràng, biết được bước nào đã sẵn sàng và bước nào bị tạm khóa khi đang tải nhạc.
- **US02 - Nhập Takeout (Import):** Là người dùng, tôi muốn kéo thả folder Takeout vào vùng nhận diện lớn, có thông báo tiến độ và dialog chọn profile lịch sử nếu folder chứa nhiều tài khoản.
- **US03 - Duyệt & Chọn bài song song (Explore Dual-Pane):** Là người dùng, tôi muốn nhìn thấy danh sách Nhạc và Còn lại song song trên cùng màn hình, bấm trực tiếp vào thẻ bài hát để chọn nhiều bài rồi bấm chuyển một lượt sang cột đối diện, hoặc bấm nút chuyển nhanh trên từng bài.
- **US04 - Tìm kiếm & Lọc độc lập:** Là người dùng, tôi muốn tìm kiếm tên bài/kênh trên từng cột mà không ảnh hưởng cột còn lại, URL đồng bộ trạng thái lọc để khi F5 không bị mất trang.
- **US05 - Quản lý Metadata & Xem trước phân loại:** Là người dùng, tôi muốn mở modal/drawer lấy metadata YouTube Music và xem bảng so sánh thay đổi trước khi áp dụng vào thư viện.
- **US06 - Đối soát bài trùng (Deduplicate):** Là người dùng, tôi muốn xem các nhóm bài nghi cùng bài, đối chiếu các bản thu (gốc, cover, live, remix) và bấm giữ hoặc loại bản thu cần tải.
- **US07 - Trình quản lý tải (Download):** Là người dùng, tôi muốn theo dõi tiến độ tải audio theo thời gian thực, xem số bài đã tải/đã có/lỗi, và có các nút Tạm dừng/Tiếp tục/Thử lại bài lỗi.

## Success Criteria

1. **Giao diện đáp ứng thẩm mỹ:** Chuẩn Apple Pro Liquid Glass, không có icon rườm rà, bố cục ngăn nắp, tương phản chữ sắc nét.
2. **Thao tác mượt mà:** Chuyển bài giữa 2 cột có phản hồi tức thì qua optimistic state; tìm kiếm debounce nhanh chóng.
3. **Tương thích Backend:** Build output của Vite được đặt tại `src/auralytica/static/`, server FastAPI khởi chạy và phục vụ toàn bộ web app bình thường.
4. **Kiểm thử đạt 100%:** Toàn bộ 116 bài test unit/integration của backend tiếp tục chạy `OK`.

## Constraints & Assumptions

- Môi trường chạy trên Linux, hỗ trợ Node.js 24.x và Python 3.11+.
- Giao diện tối ưu hóa cho màn hình Desktop/Laptop (từ 1024px đến 2560px), hỗ trợ chế độ xem xếp chồng (stacked) trên mobile nếu màn hình hẹp hơn 768px.
