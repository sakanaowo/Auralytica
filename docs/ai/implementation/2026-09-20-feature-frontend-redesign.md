---
phase: implementation
title: Implementation Guide — Frontend Redesign
description: Hướng dẫn kỹ thuật và chi tiết triển khai giao diện mới React SPA cho Auralytica
---

# Implementation Guide — Frontend Redesign

Cập nhật: **2026-09-20**. Tính năng: `frontend-redesign`.

## Development Setup

Frontend nằm hoàn toàn trong thư mục `frontend/`, tách biệt khỏi mã nguồn Python:
- **Cài đặt dependencies:**
  ```sh
  cd frontend
  npm install
  ```
- **Chạy môi trường phát triển (Dev server kèm hot-reload):**
  ```sh
  cd frontend
  npm run dev
  ```
  *(Dev server chạy tại `http://localhost:5173` và tự động proxy các request `/api` sang backend `http://127.0.0.1:8765`)*.
- **Đóng gói production ra thư mục static của backend:**
  ```sh
  cd frontend
  npm run build
  ```
  *(Lệnh này tự động biên dịch TypeScript và đóng gói tĩnh vào `src/auralytica/static/`)*.

## Code Structure

```text
frontend/
├── package.json
├── tsconfig.json
├── vite.config.ts           # Cấu hình build output ra ../src/auralytica/static
├── public/                  # Asset tương thích (app.js, style.css)
├── src/
│   ├── index.css            # Tailwind CSS v4 + Liquid Glass tokens
│   ├── main.tsx             # Entrypoint gắn React vào #root và cấp QueryClientProvider
│   ├── App.tsx              # Component điều phối routing 4 bước
│   ├── api/
│   │   ├── types.ts         # Types cho toàn bộ Request / Response backend
│   │   └── client.ts        # Typed API client wrapper
│   ├── components/
│   │   ├── AppShell.tsx     # Header text-driven, 4-step stepper, status badge
│   │   ├── SongCard.tsx     # Thẻ bài hát 16:9 thumbnail, 1-click select, quick action
│   │   └── ColumnPane.tsx   # Cột duyệt bài (dùng cho cả Nhạc và Còn lại)
│   └── features/
│       ├── import/
│       │   └── ImportView.tsx    # Kéo thả folder Takeout và dialog chọn nguồn
│       ├── explore/
│       │   ├── ExploreView.tsx   # Dual-pane container 50/50
│       │   └── MetadataModal.tsx # Modal lấy metadata và xem trước phân loại
│       ├── dedup/
│       │   └── DedupView.tsx     # Đối soát bài nghi trùng, gạt keep/exclude
│       └── download/
│           └── DownloadView.tsx  # Download manager, progress bar và batch controls
```

## Key Implementation Patterns

### 1. Thẻ bài hát & 1-Click Select (`SongCard.tsx`)
- Thay vì bắt người dùng phải căn bấm vào checkbox nhỏ, toàn bộ diện tích thẻ có thể click để toggle chọn (`onToggle(id)`).
- Trạng thái được chọn thể hiện qua class `glass-card-selected` với viền sáng tinh tế và nền `zinc-850`.
- Nút chuyển nhanh 1-chạm (`Chuyển →` hoặc `← Thêm`) xuất hiện khi hover ở mép phải, cho phép chuyển ngay lập tức mà không cần bấm chọn trước.
- Thumbnail sử dụng tỷ lệ 16:9 (`w-24 h-14`), bo góc `rounded-lg`, tự động fallback sang khung xám trung tính nếu ảnh lỗi.

### 2. Dual-Pane Split View (`ExploreView.tsx` & `ColumnPane.tsx`)
- Màn hình Explore chia đôi 50/50 giữa `Nhạc đã nhận diện` và `Còn lại`.
- Mỗi cột sở hữu độc lập:
  - Input tìm kiếm (tên bài, tên kênh).
  - Dropdown lọc lý do phân loại phù hợp với từng nhóm.
  - Sắp xếp (xem nhiều nhất, tiêu đề, kênh).
  - Thanh chọn cả trang và nút chuyển hàng loạt.
  - Danh sách cuộn riêng biệt và phân trang (25 / 50 / 100 bài/trang).
- Bộ lọc được đồng bộ hai chiều với `URLSearchParams`, đảm bảo F5 hoặc Back/Forward trên trình duyệt không làm mất kết quả lọc.

### 3. Modal Metadata & Phân loại không chiếm diện tích (`MetadataModal.tsx`)
- Panel lấy metadata và xem trước thay đổi được đưa vào Modal kính mờ nổi (`MetadataModal`).
- Khi cần lấy metadata từ YouTube Music hoặc xem trước đề xuất phân loại, người dùng bấm nút trên Header để mở modal. Sau khi xem/áp dụng xong, đóng lại để tiếp tục duyệt 2 cột mà không bị choán màn hình.

### 4. Triết lý No-Sticker & Apple Pro Aesthetics
- Loại bỏ toàn bộ emoji trang trí (`♫`, `⚡`, `✓`,...) và các icon màu mè.
- Toàn bộ giao diện sử dụng bảng màu Neutral Zinc (`#09090b` đến `#f4f4f5`) của Tailwind CSS, viền kính mờ sắc sảo 1px (`border-white/[0.08]`), tương phản chữ sắc nét và độ hoàn thiện cao.

## Verification & Status

- **Build:** `npm run build` hoàn tất trong ~700ms, tạo file tĩnh hợp lệ trong `src/auralytica/static/`.
- **Backend Compatibility:** Chạy toàn bộ 116 bài test backend bằng `python -m unittest discover -s tests -v` đạt `116/116 OK`.
