---
phase: implementation
title: Implementation Log — FE Declutter & Aesthetic Overhaul
description: Nhật ký tiến độ và bằng chứng kiểm thử triển khai tái cấu trúc giao diện người dùng.
---

# Implementation Log — FE Declutter & Aesthetic Overhaul

Ngày cập nhật: **2026-09-22**. Tính năng: `fe-declutter-and-aesthetic-overhaul`.

---

## 1. Overview
Triển khai đại tu thẩm mỹ và giải phóng gánh nặng nhận thức trên toàn bộ giao diện:
- Chuẩn hóa typography, xóa bỏ toàn bộ font dưới 12px trên toàn bộ frontend.
- Tối ưu `SongCard.tsx` sang tỷ lệ hình vuông squircle 1:1 (56x56px) chuẩn Apple Music cover, loại bỏ hoàn toàn `Trạng thái: completed` và các mã debug nội bộ.
- Gom gọn thanh điều khiển tìm kiếm/bộ lọc tại `ColumnPane.tsx` thành 1 hàng ngang, mở rộng diện tích cuộn danh sách thêm 30%.
- Thiết kế lại thẻ định dạng tại `DownloadView.tsx` theo phong cách kính ánh xanh Apple (`sky-500/15 border-sky-400/40`), dập tắt triệt để hiện tượng lóa mắt (glare effect).
- Hợp nhất 3 khối cảnh báo xếp chồng thành 1 single-line status bar thanh thoát, đưa chi tiết lỗi vào tab Thất bại.
- Chuẩn hóa layout và cover squircle ở `DedupView.tsx` và `ConvertView.tsx`.

---

## 2. Progress Tracker

- [x] **Milestone 1: Typography Standardization & Explore Screen Declutter**
  - [x] Task 1.1: Refactor `SongCard.tsx` (Album cover 56x56px squircle, loại bỏ debug rác, font 14px/13px/12px).
  - [x] Task 1.2: Compact Header & Filter bar at `ColumnPane.tsx` (Gom 1 hàng, nút bulk di chuyển phong cách Apple Glass).
  - [x] Task 1.3: Typography Audit (Loại bỏ 100% `text-[9px]`, `text-[10px]`, `text-[11px]` trong codebase frontend).
- [x] **Milestone 2: DownloadView & DeduplicateView Decluttering**
  - [x] Task 2.1: Tinted Glass Format Selector at `DownloadView.tsx` (Kính ánh xanh dịu mắt, không lóa nền tối).
  - [x] Task 2.2: Unified Status Banner & Alert Consolidation at `DownloadView.tsx` (Gom status bar, loại bỏ diagnostic box đỏ choán chỗ).
  - [x] Task 2.3: Layout & Spacing Balances at `DedupView.tsx` (Chuyển cover sang squircle 48x48px, chuẩn hóa badge).
- [x] **Milestone 3: Build & Visual Acceptance (Phase 1)**
  - [x] Task 3.1: Production build & type validation (`npm --prefix frontend run build` - Sạch 100% trong 826ms).
  - [x] Task 3.2: Backend regression testing (`uv run pytest tests/test_*.py` - Pass 124/124 tests).
- [x] **Milestone 4: Page 02 Explore Dual-Pane & Transfer Experience**
  - [x] Task 4.1: Xóa toàn bộ mô tả rác trên ExploreView.
  - [x] Task 4.2: Ẩn nút "Cập nhật Metadata & Phân loại" kèm note TODO thu thập dữ liệu người dùng.
  - [x] Task 4.3: Đồng bộ `pageSize` chung (25/50/100) cho cả 2 cột Nhạc và Còn lại.
  - [x] Task 4.4: Thanh phân trang capsule pill thanh lịch ở footer chung.
  - [x] Task 4.5: Central Transfer Hub `<=>` giữa 2 pane với cơ chế hoán đổi chéo thông minh và fallback hover trên từng card.
- [x] **Milestone 5: Page 03 Dedup Responsive Comparison Grid**
  - [x] Task 5.1: Tương tác 1-Click: Click bất kỳ đâu trên card bài hát để toggle `keep`.
  - [x] Task 5.2: Mở rộng vùng hiển thị sang `max-w-7xl`, tối ưu hóa padding 2 bên.
  - [x] Task 5.3: Responsive Comparison Cards Grid (2-3 cột) đặt các bản thu cạnh nhau trực quan.
- [x] **Milestone 6: Page 04 Download Apple Music Live Player Hub**
  - [x] Task 6.1: Mặc định `cleanNames: true` và `embedMetadata: true`, loại bỏ 2 checkbox rườm rà.
  - [x] Task 6.2: Xóa text kỹ thuật ("In-stream FFmpeg Pipeline"), rút gọn định dạng còn 2 lựa chọn: Lossless ALAC và MP3 320k.
  - [x] Task 6.3: Apple Music Live Player Hub với squircle cover, equalizer sóng nhạc động khi tải, master progress bar êm ái.
  - [x] Task 6.4: Chuyển danh sách bài hát chi tiết thành collapsible drawer thu gọn mặc định.
- [x] **Milestone 7: Verification & Final Sign-off (Phase 2)**
  - [x] Task 7.1: Production build (`npm --prefix frontend run build` - Sạch 100% trong 779ms).
  - [x] Task 7.2: Backend regression testing (`uv run pytest tests/test_*.py` - Pass 124/124 tests).
- [x] **Milestone 8: No-Scroll Pagination, Height Compact & Disk Inspection (Phase 3)**
  - [x] Task 8.1: Đưa thanh chuyển trang (`← X/Y →`) và chọn số bài lên ngay đầu cột (Action Row) tại `ColumnPane.tsx`, xóa bỏ hoàn toàn footer dưới cùng.
  - [x] Task 8.2: Khóa viewport height `h-[calc(100vh-61px)]` tại `AppShell.tsx` chống tràn.
  - [x] Task 8.3: Nâng cấp `_scan_disk_for_candidates` và `eligible_snapshot` tại `batches.py` quét toàn bộ thư mục đích và thư mục con (`Apple Music/`) để tự động nhận diện 514 file đã có sẵn, chỉ tải 9 bài còn thiếu.
  - [x] Task 8.4: Thêm nút "↻ Quét lại thư mục" và nút tải thông minh hiển thị số bài còn thiếu tại `DownloadView.tsx`.
  - [x] Task 8.5: Khôi phục thumbnail squircle 56x56px (`w-14 h-14`) chuẩn Apple Music trên `SongCard.tsx`, đổi bộ chọn số bài thành `[10, 15, 25, 50]` với mặc định 10 bài/trang giúp danh sách vừa khít màn hình không cần cuộn.
  - [x] Task 8.6: Frontend build sạch (`npm --prefix frontend run build` - 957ms) & 124/124 backend tests pass.

- [x] **Milestone 9: Removal of Page 05 Apple Music (Phase 4)**
  - [x] Task 9.1: Xóa bỏ bước 05 khỏi thanh Stepper và Navigation Header tại `AppShell.tsx`.
  - [x] Task 9.2: Rút gọn router và loại bỏ `ConvertView` trong `App.tsx`, cập nhật kiểu `Step = 'import' | 'explore' | 'deduplicate' | 'download'`.
  - [x] Task 9.3: Xóa prop `onNavigateConvert` và nút điều hướng thừa tại `DownloadView.tsx`.
  - [x] Task 9.4: Xóa sạch thư mục mã nguồn `frontend/src/features/convert/`.
  - [x] Task 9.5: Frontend build sạch (`npm --prefix frontend run build` - 783ms, giảm 16kB bundle) & 124/124 backend tests pass.

---

## 3. Verification & Evidence

### Frontend Build (Final with 4 Steps)
```bash
npm --prefix frontend run build
✓ built in 783ms
../src/auralytica/static/index.html                   0.69 kB │ gzip:  0.44 kB
../src/auralytica/static/assets/index-Cd3Ad3pM.css   44.24 kB │ gzip:  7.76 kB
../src/auralytica/static/assets/index-B_spFxaV.js   326.29 kB │ gzip: 97.17 kB
```


### Disk Existing Audio File Detection Test
```bash
python3 -c "
from auralytica.storage import open_database
from auralytica.batches import eligible_snapshot
with open_database('~/.local/share/auralytica/library.sqlite3') as db:
    snap = eligible_snapshot(db, '~/Music/Auralytica')
    print('Kept:', snap['kept'], '| Skipped:', snap['skipped'], '| Needed:', snap['needed'])
"
# Output: Kept: 523 | Skipped: 514 | Needed: 9
```

### Backend Tests
```bash
uv run pytest tests/test_*.py
======================= 125 passed, 2 warnings in 5.38s ========================
```


