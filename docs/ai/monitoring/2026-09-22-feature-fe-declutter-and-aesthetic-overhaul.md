---
phase: monitoring
title: "Monitoring & Observability: FE Declutter and Aesthetic Overhaul"
description: Giám sát hiệu năng giao diện, chỉ số hiển thị mượt mà (60fps), dung lượng bundle và tỷ lệ lỗi giao diện
---

# Monitoring & Observability: FE Declutter and Aesthetic Overhaul

## Key Metrics

Hệ thống Auralytica là ứng dụng desktop/local webapp cho xử lý thư viện nhạc lớn (500 - 2,000+ bài hát). Do đó, việc giám sát tập trung vào hiệu năng render DOM, độ phản hồi cuộn trang và tỷ lệ lỗi frontend.

### Performance & UX Metrics

- **List Rendering & Scroll Latency**: Duy trì 60 FPS khi cuộn danh sách hơn 500 bài hát trong `ExploreView` / `ColumnPane`.
- **Card DOM Complexity**: Tối giản số lượng node DOM trên mỗi `SongCard` (giảm từ 18 node xuống còn 8 node do loại bỏ các badge và text rác).
- **First Contentful Paint (FCP) & LCP**: Tốc độ hiển thị thẻ bài hát sau khi API `/api/scan` hoặc `/api/library` phản hồi < 100ms.
- **Image Thumbnail Memory footprint**: Đảm bảo thumbnail 56x56 render không gây leak bộ nhớ trình duyệt qua Virtualization.

### Error & Health Metrics

- **Image Fallback Trigger Rate**: Tỷ lệ ảnh cover bị lỗi load (chuyển sang icon nốt nhạc squircle mặc định).
- **Frontend Error Boundary Hits**: Tỷ lệ crash React component trên các view chính (`ExploreView`, `DownloadView`, `DeduplicateView`).
- **Download WebSocket Message Latency**: Độ trễ cập nhật trạng thái download từ backend tới Single-line status bar.

## Logging Strategy

- **Browser Console Logging**:
  - Tắt toàn bộ debug log rác trong production build (`console.debug` / `console.log` chi tiết regex).
  - Giữ lại `console.warn` và `console.error` cho các lỗi API hoặc kết nối WebSocket.
- **WebSocket Event Tracking**:
  - Ghi nhận trạng thái kết nối `connected` / `disconnected` / `reconnecting` với UI indicator nhỏ nhắn ở góc footer (thay vì banner to choán chỗ).

## Alerts & Regression Checks

### Automated Build Checks
- **Tailwind Sub-12px Font Lint**: Chặn các class `text-[9px]`, `text-[10px]`, `text-[11px]` trong build pipeline.
- **Bundle Size Alert**: Cảnh báo nếu bundle frontend tăng thêm > 50KB không có lý do.
- **TypeScript Strict Check**: 0 lỗi type trong quá trình build `tsc --noEmit`.

### Runtime Warnings
- **DOM Node Count Warning**: Cảnh báo nếu số lượng thẻ DOM của danh sách vượt ngưỡng virtualization tối ưu.

## Health Verification

- Kiểm tra trực quan:
  1. Thẻ bài hát hiển thị sạch sẽ, không có chữ `< 12px`.
  2. Format Selector trong DownloadView hiển thị ánh xanh thanh lịch (không chói mắt).
  3. Status bar DownloadView gom gọn, thông tin lỗi nằm trọn trong tab Thất bại.
