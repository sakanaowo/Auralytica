---
phase: requirements
title: Requirements Document — Takeout Session Management
description: Quản lý danh sách phiên Takeout, chuyển đổi linh hoạt giữa các phiên và nạp phiên mới an toàn với cơ chế bảo toàn tiến độ đang thực hiện.
---

# Requirements Document — Takeout Session Management

Ngày tạo: **2026-09-26**. Tính năng: `takeout-session-management`. Nhánh: `feature-takeout-session-management`.

---

## 1. Problem Statement

1. **Thiếu khả năng hiển thị và quản lý phiên trong giao diện:**
   - Dữ liệu trong CSDL SQLite (`imports` và `watch_events`) lưu trữ các phiên import theo từng bản ghi `import_id`. Tuy nhiên, trang `01 Import` (`ImportView.tsx`) hiện chỉ là một khung kéo thả file trống, không hiển thị danh sách các phiên đã từng nhập.
2. **Kẹt ở một phiên duy nhất (`active_import`):**
   - Ứng dụng chỉ duy trì một khóa `active_import` trong bảng `settings`. Người dùng không thể biết máy đang có bao nhiêu phiên, không thể xem lại phiên cũ hoặc chuyển đổi qua lại giữa các file lịch sử khác nhau.
3. **Nhu cầu làm mới và bảo toàn phiên dở dang:**
   - Người dùng cần có khả năng "làm mới phiên" (bắt đầu một phiên nạp Takeout mới độc lập) mà không làm mất hoặc ghi đè tiến độ của phiên đang làm dở (các nhãn phân loại nhạc, quyết định kênh, lựa chọn deduplicate, đợt tải audio).
   - Hệ thống phải bảo vệ nghiêm ngặt: không cho phép chuyển phiên hoặc xóa phiên khi đang có tiến trình tải audio đang chạy (`batch_locked`).

---

## 2. Goals & Non-Goals

### Goals
- **G1 (Hiển thị danh sách phiên):** Hiển thị danh sách toàn bộ các phiên Takeout đã nhập tại trang `01 Import` với các thông tin: ID, Tên nguồn file, Ngày giờ tạo, Số lượng video độc nhất, Số lượt xem, Số bài Nhạc/Còn lại, và Badge trạng thái `Đang hoạt động (Active)`.
- **G2 (Chuyển đổi phiên tức thì):** Cho phép người dùng bấm "Kích hoạt" một phiên bất kỳ để chuyển toàn bộ các bước Explore, Deduplicate, Download sang dữ liệu của phiên đó.
- **G3 (Làm mới & Tạo phiên mới độc lập):** Cho phép người dùng mở khung nạp folder Takeout mới để tạo một phiên hoàn toàn mới mà không làm ảnh hưởng đến các phiên trước.
- **G4 (Bảo toàn 100% tiến độ đang làm dở):**
  - Mọi phân loại video (`user_group`), luật kênh (`channel_decisions`), lựa chọn deduplicate (`download_selections`), tiến độ làm giàu metadata được gắn bền vững với SQLite. Khi chuyển sang phiên khác và quay lại, toàn bộ dữ liệu vẫn ở nguyên vị trí đã dừng lại.
  - Khóa tính năng chuyển phiên và xóa phiên khi phiên hiện tại đang có batch tải audio ở trạng thái `queued` hoặc `running`.
- **G5 (Xóa phiên cũ):** Cho phép xóa các phiên cũ không còn dùng (chỉ áp dụng cho các phiên không Active và không có batch tải dở dang).

### Non-Goals
- Gộp (merge) nhiều file Takeout khác nhau vào chung 1 phiên (mỗi phiên là 1 snapshot độc lập).
- Thay đổi cấu trúc 4 bước của Takeout Studio (`import` → `explore` → `deduplicate` → `download`).

---

## 3. User Stories

- **US1:** Là người dùng, tôi muốn xem danh sách các phiên Takeout đã nhập trước đó kèm ngày giờ và số lượng video để nắm rõ lịch sử dữ liệu của mình.
- **US2:** Là người dùng, tôi muốn bấm chọn kích hoạt một phiên bất kỳ để quay lại xem, lọc bài hoặc tải nhạc của phiên đó.
- **US3:** Là người dùng, tôi muốn nhập một folder Takeout mới để bắt đầu một phiên làm việc mới độc lập mà không bị ghi đè phiên cũ.
- **US4:** Là người dùng, nếu tôi đang tải nhạc dở dang ở phiên hiện tại, hệ thống phải ngăn tôi chuyển phiên hoặc xóa phiên và cảnh báo tôi tạm dừng hoặc chờ tải xong.
- **US5:** Là người dùng, tôi muốn có thể xóa các phiên cũ không cần thiết để dọn dẹp cơ sở dữ liệu.

---

## 4. Success Criteria

- [ ] API `GET /api/imports` trả về danh sách đầy đủ các phiên import trong CSDL kèm thống kê và trạng thái `is_active` (< 20ms).
- [ ] API `POST /api/imports/{id}/activate` đổi `active_import` an toàn và làm mới cache hiển thị.
- [ ] API `DELETE /api/imports/{id}` xóa thành công phiên lưu trữ không active và xóa các bản ghi `watch_events` liên quan.
- [ ] Ngăn chặn chuyển/xóa phiên với mã lỗi HTTP 409 khi đang có batch tải đang chạy (`assert_review_unlocked`).
- [ ] Trang `01 Import` hiển thị rõ 2 khu vực: Phiên hiện tại & Danh sách các phiên, cùng nút mở khung Nạp phiên mới.
- [ ] Chuyển qua lại giữa các phiên giữ nguyên 100% quyết định phân loại, lựa chọn bài trùng và đợt tải của từng phiên.
- [ ] 100% unit tests và build frontend Vite TypeScript pass không lỗi.

---

## 5. Constraints & Edge Cases

- **Khóa Batch (`assert_review_unlocked`):** Không được thay đổi phiên khi bất kỳ batch tải nào của phiên hiện tại đang ở trạng thái `queued` hoặc `running`.
- **Xóa phiên an toàn:** Tuyệt đối không cho phép xóa phiên đang `Active` hoặc phiên có batch tải liên kết. Phải yêu cầu người dùng kích hoạt phiên khác trước khi xóa.
- **Bảo toàn dữ liệu `videos` chung:** Bảng `videos` lưu trữ thông tin video chung; khi xóa một phiên, chỉ xóa liên kết sự kiện xem `watch_events` của phiên đó, không xóa video nếu video đó còn nằm trong các phiên khác hoặc trong thư viện player.
