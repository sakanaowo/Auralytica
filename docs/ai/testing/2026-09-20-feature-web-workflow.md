---
phase: testing
title: Web workflow — Kịch bản nghiệm thu
description: Tài liệu testing cho luồng web bốn bước, chưa nghiệm thu
---

# Web workflow — Kịch bản nghiệm thu

Trạng thái: **kế hoạch kiểm thử, chưa chạy cho feature mới**. Không dùng 90 test nền tảng cũ để đánh dấu các mục dưới đây đạt.

## Test Coverage Goals

Phủ mọi WA01–WA12 và các nhánh có nguy cơ mất lựa chọn/file. Báo cáo coverage đo được, không coi tỷ lệ coverage là bằng chứng accuracy matching. Fixtures tổng hợp không chứa lịch sử cá nhân.

## Unit Tests

- [ ] **WFT05** — Unicode NFKC/hoa-thường/dấu câu/phụ tố có kết quả ổn định và giữ title gốc (WA04).
- [ ] **WFT05** — Shoujo A / 少女A với alias đã xác nhận thành ứng viên; thiếu evidence không tự coi là chắc chắn (WA04).
- [ ] **WFT05** — Tên phổ biến/nghệ sĩ khác, cover/live/remix/slowed, title trống/metadata thiếu không bị tự loại (WA05).
- [ ] **WFT07** — Tập tải = tập nhạc được giữ sau dedup; filter/page/checkbox tạm không làm mất ID (WA06–WA07).

## Integration Tests

- [ ] **WFT03/WFT06** — Import thất bại giữ DB cũ; reimport giữ override và lựa chọn đúng ID (WA09, WA11).
- [ ] **WFT04** — Metadata còn hợp lệ cùng ID qua import, recurrence theo nguồn mới; preview cũ bị từ chối (WA08–WA09).
- [ ] **WFT05/WFT06** — Quyết định dedup không đổi nhãn music/rest, không xóa file; nhóm thay đổi đánh dấu review phù hợp (WA06, WA09).
- [ ] **WFT04/WFT07** — Transaction/audit rollback và khóa khi batch queued/running; batch cũ giữ snapshot (WA08, WA10).
- [ ] **WFT07** — Skip file hợp lệ, file mất/hỏng cần tải lại, lỗi một item không chặn batch (WA07, WA10).
- [ ] **WFT05/WFT08** — Migration bảo toàn dữ liệu, startup local/Host/Origin/escape title và alias (WA11).

## End-to-End Tests

- [ ] **WFT08/WFT09** — Hoàn tất Import → Explore → Deduplicate → Download bằng browser, không CLI/CSV (WA01).
- [ ] **WFT02** — Bốn URL, refresh/back/forward/direct URL, loading/empty/error và điều kiện đầu vào đúng (WA02).
- [ ] **WFT03** — Explore mặc định nhóm Nhạc, chỉ số đối chiếu fixture và nguồn nhãn phân biệt; mở Còn lại để sửa (WA03).
- [ ] **WFT05/WFT06** — So nhóm đa ngôn ngữ, chọn một/nhiều/tất cả, từ chối ghép, hoàn tác, reload giữ lựa chọn (WA04–WA06).
- [ ] **WFT06** — Bỏ qua dedup vẫn tải tất cả bản giữ mặc định (WA06).
- [ ] **WFT07** — Đổi trang/lọc rồi tải: snapshot đầy đủ, count loại dedup khác count skip file (WA07).
- [ ] **WFT04** — Enrichment/preview/apply/status/lỗi/resume thao tác trên web; nhóm cập nhật đúng (WA08).
- [ ] **WFT06/WFT07** — Dừng/tiếp tục/retry và restart server giữ batch, file thành công và lựa chọn (WA09–WA10).

## Performance Testing

- [ ] **WFT03/WFT05/WFT09** — Fixture ≥7.500 video; đo thời gian nhập/list/filter/group, trang hợp lệ và không render toàn bộ; ghi máy/browser (WA12).
- [ ] **WFT04/WFT05** — Metadata/matching job không giữ UI chờ đồng bộ không có progress (WA02, WA12).

## Matching Quality & Reporting

- [ ] **WFT05/WFT09** — Bộ nhãn độc lập có cùng bài/cùng bản thu, cùng bài/khác bản, khác bài/tên tương tự, tên đa ngôn ngữ và metadata thiếu (WA04–WA05).
- [ ] **WFT09** — Báo precision/recall của gợi ý khi dữ liệu đủ, không báo trên nhãn proxy hay coi Còn lại là non_music đã xác nhận.

Log lệnh/exit code và artifact sau khi thực sự chạy. Browser fixtures không chứng minh tải mọi video thật; smoke tải phải báo riêng phạm vi.


## Kịch bản bổ sung sau design review

- [ ] **WFT05** — Hai bài khác nhau cùng alias/title: không ép chung song key; artist conflict được thể hiện (WA04–WA05).
- [ ] **WFT05** — Liên kết A–B và B–C không có bằng chứng A–C: không ghép bắc cầu mù (WA05).
- [ ] **WFT06** — Nhóm mới có video mới: selection cũ chỉ theo ID đã chọn, video mới vẫn keep (WA06, WA09).
- [ ] **WFT06** — Hai tab sửa selection trên cùng revision: một thành công, tab cũ nhận 409 và không mất dữ liệu (WA06, WA08).
- [ ] **WFT07** — Counts music/excluded/kept/skip/queued khớp nhau; đổi output/file giữa preview và start được xử lý (WA07).
- [ ] **WFT04/WFT05** — Job đang chạy thì import/nhãn đổi: kết quả cũ marked stale, không ghi selection (WA08–WA09).
- [ ] **WFT08** — Launcher mở loopback/browser; cổng đã bị process khác chiếm không bị kill/tái sử dụng mù (WA01, WA11).

## Workspace baseline — 2026-09-20

Worktree `feature-web-workflow`: `uv sync --locked --no-default-groups --group test --group browser` đạt; `.venv/bin/python -m unittest discover -s tests -q` **90 tests OK, exit 0**. Đây là xác minh code được chép đủ, chưa nghiệm thu bất kỳ checkbox mới nào. Chưa chạy research/browser tại bước setup.
