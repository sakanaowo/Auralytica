---
phase: planning
title: Web workflow — Kế hoạch triển khai
description: Task triển khai bốn trang, dependencies, bằng chứng và điều kiện nghiệm thu
---

# Web workflow — Kế hoạch triển khai

Cập nhật **2026-09-20**. [Requirements](../requirements/2026-09-20-feature-web-workflow.md) và [design](../design/2026-09-20-feature-web-workflow.md) là đầu vào. **WFT01–WFT09 đã hoàn tất**; ứng dụng web-only đã qua nghiệm thu cuối trong phạm vi Linux/Takeout JSON.

## Workspace và baseline

- Active workdir: `/home/sakana/Code/Auralytica/.worktrees/feature-web-workflow`.
- Branch: `feature-web-workflow`, tạo từ HEAD `a1e7ef5`, sau đó chép **43 file modified/untracked** từ workspace gốc và kiểm tra SHA-256. Nhánh mới vẫn có các thay đổi chưa commit, không phải checkout sạch của HEAD cũ.
- Workspace gốc `feature/music-feature-engineering` được giữ nguyên; không commit/stash/reset. Thêm `/.worktrees/` vào ignore để tránh đưa workspace con vào Git.
- Không chép Takeout, audio, live DB, artifacts hoặc `.venv` cũ. Manifest ở workspace gốc: `artifacts/workspace-setup/web-workflow-copy.json`. Các link artifacts nghiên cứu cũ chỉ tồn tại ở workspace gốc.
- Bootstrap: `uv sync --locked --no-default-groups --group test --group browser`; tạo `.venv` riêng và build editable package trong worktree. Không cần frontend build với HTML/CSS/JS hiện có.
- `npx ai-devkit@latest lint --feature web-workflow`: **exit 0**, đủ docs + branch + worktree.
- `.venv/bin/python -m unittest discover -s tests -q`: **90 tests OK, exit 0** tại worktree. Chưa chạy browser/research ở lượt chuẩn bị; 90 test là baseline, không chứng minh feature mới đã xong.
- Task CLI probe trước đó trả `unknown command 'task'`; bảng dưới đây là nguồn tiến độ, chưa có task ID.

## Milestones và task

| Task | Trạng thái | Kết quả | Phụ thuộc | AC |
| --- | --- | --- | --- | --- |
| WFT01 | **done** | Review requirements/design, workspace bảo toàn code, baseline | — | Chuẩn bị WA01–WA12 |
| WFT02 | **done** | Navigation bốn URL và workflow state | WFT01 | WA02, WA11, WA12 |
| WFT03 | **done** | Import/Explore với nhạc làm trung tâm và thống kê | WFT02 | WA01, WA03, WA09, WA11, WA12 |
| WFT04 | **done** | Metadata + preview/apply trên web, tái dùng evidence qua import | WFT03 | WA01, WA08, WA09, WA11 |
| WFT05 | **done** | Model/migration, alias và nhóm dedup có evidence | WFT03 | WA04, WA05, WA09, WA11, WA12 |
| WFT06 | **done** | UI dedup, lựa chọn tải bền và kiểm soát revision | WFT05 | WA04, WA05, WA06, WA08, WA09 |
| WFT07 | **done** | Download snapshot sau dedup, skip/retry và counts | WFT06 | WA07, WA10, WA11 |
| WFT08 | **done** | Web parity, launcher, loại CLI nghiệp vụ | WFT04, WFT07 | WA01, WA11 |
| WFT09 | **done** | Nghiệm thu tổng thể, migration/quy mô, review | WFT02–WFT08 | WA01–WA12 |

Thứ tự mặc định: **WFT02 → WFT03 → WFT04 → WFT05 → WFT06 → WFT07 → WFT08 → WFT09**. WFT05 độc lập về kỹ thuật với WFT04 sau WFT03, nhưng chưa cần làm song song. Không thêm model audio hoặc matching dịch vụ ngoài.

### M1 — Bốn trang và Explore (WFT02–WFT03)

**WFT02**

- [x] Test red: bốn URL, root redirect theo có/không import, refresh/direct URL và workflow state.
- [x] Shell điều hướng và module từng trang; giữ chức năng hiện có, không hiển thị dedup chưa có như đã sẵn sàng.
- [x] Endpoint workflow: active import, counts, batch lock và trạng thái bước. Dùng state từ server, không suy từ localStorage.
- [x] Back/Forward, query string cho trang/lọc, empty/loading/error/retry; direct Download vẫn xem batch cũ khi nhóm nhạc trống.
- [x] Kiểm chứng API + Chromium: không mất thao tác khi chuyển trang, HTML/JS không lỗi, màn hình hẹp.

**WFT03**

- [x] Chuyển import picker/drop/source dialog vào Import; kết quả thành công tới Explore; lỗi giữ thư viện trước đó.
- [x] Explore mặc định Nhạc; Còn lại là mục phụ, giữ move/manual override và lọc/sort/page.
- [x] Summary server-side: lượt/ngày xem, kênh, title signals, metadata coverage; ghi phạm vi và tách manual/automatic.
- [x] Kiểm thử fixture có expected counts độc lập, không coi rest là ground truth và không suy duration thành thời gian nghe.
- [x] Đối chiếu reimport/source selection/Host-Origin và render title an toàn; đo list/filter trên ≥7.500 video.

### M2 — Evidence và nhóm cùng bài (WFT04–WFT05)

**WFT04**

- [x] Test tái hiện metadata đã áp dụng bị bỏ vì history hash; sửa phạm vi evidence video ID/provider/parser/freshness, tính recurrence theo active import.
- [x] Job/status/start/stop/resume metadata với snapshot ID và phạm vi được hiển thị trước khi chạy; không tự lấy toàn bộ lịch sử.
- [x] Preview lưu server-side, apply từ preview ID, hash/revision và transaction; không đưa upload CSV/path CLI vào UI.
- [x] Job recovery sau restart; input đổi thì stale, lỗi/missing không thành non_music; giữ user_group.
- [x] Test đa tab/snapshot cũ/batch lock/audit rollback; E2E metadata fixture → preview → apply không cần terminal.

**WFT05**

- [x] Migration kế tiếp cho alias, dedup run/group/member/evidence, selection và rejected fingerprint; kiểm tra unique/FK/rollback/version tương lai và giữ dữ liệu cũ.
- [x] Normalizer NFKC/casefold/whitespace/allowlist phụ tố; giữ raw title và marker phiên bản; không xóa mọi nội dung ngoặc.
- [x] Alias có song key/scope/provenance; cùng normalized alias có thể thuộc nhiều bài, không unique toàn cục.
- [x] Group theo key/anchor với evidence cho mỗi member, không connected-component fuzzy mù; conflict/thiếu artist không tự loại.
- [x] Dedup job immutable input/version, phân trang nhóm/member và stale detection; default keep cho ID mới.
- [x] Bộ fixture Shoujo A/少女A có alias, tên phổ biến khác nghệ sĩ, cùng bài khác bản, dữ liệu thiếu; đo quy mô không all-pairs.

### M3 — Chọn bản và tải (WFT06–WFT07)

**WFT06**

- [x] API selection expected_revision; validate tất cả ID trước atomic update, audit và khóa khi batch queued/running.
- [x] Trang nhóm và so sánh bản: title/kênh/link/ảnh, version/evidence; chọn một/nhiều/tất cả, từ chối nhóm, hoàn tác.
- [x] Ghép/alias thủ công là thao tác xác nhận riêng; không suy alias từ việc loại một bản.
- [x] Selection theo ID tồn tại qua reload/reimport; nhóm thay đổi đánh dấu review, không kéo video mới vào exclude cũ.
- [x] Test hai tab 409, bỏ qua dedup, không đổi music/rest hay xóa file; browser có nhóm/member nhiều trang.

**WFT07**

- [x] Một hàm eligible dùng chung preview/batch: nhạc trong active import trừ explicit exclusion; tuyệt đối độc lập filter/page.
- [x] Preview counts music/excluded/kept/skip/queued, token revision gắn output; kiểm tra lại file và token khi start.
- [x] Giữ create idempotent/batch đã có nhưng UI nói rõ đang xem snapshot cũ; sửa selection không thay batch cũ.
- [x] Stop/resume/retry lỗi từng video, file mất/sửa, thư mục không ghi được, restart và worker lock.
- [x] E2E nhiều trang/chọn nhiều bản/trùng file; không tự tải bản khác thay video đã chọn.

### M4 — Web-only và nghiệm thu (WFT08–WFT09)

**WFT08**

- [x] Lập bảng parity mọi thao tác user-facing; chỉ gỡ CLI nghiệp vụ sau WFT04/WFT07 và luồng web có test.
- [x] Launcher local không đối số + desktop entry, mở browser; port conflict không kill/tái dùng process không xác minh.
- [x] Giữ backend/worker nội bộ; hướng dẫn cài ban đầu khác với thao tác nghiệp vụ, không yêu cầu CSV/terminal giữa bốn bước.
- [x] Test help/entrypoint thay đổi và web startup, không để tài liệu hoặc UI dẫn tới lệnh đã gỡ.

**WFT09**

- [x] Chạy toàn bộ unit/integration/browser phù hợp với code cuối; mọi WA có evidence/lệnh/exit code/artifact.
- [x] Kiểm tra migration trên bản sao, giữ manual/download/selection; rollback không chạy code cũ ghi schema mới.
- [x] Benchmark ≥7.500 video và matching review có nhãn độc lập; không tự tuyên bố accuracy từ fixture.
- [x] Review bảo mật, input validation, telemetry/network scope và failure recovery; báo giới hạn còn lại.
- [x] Cập nhật dashboard/README, kiểm tra diff/branch; commit/push chỉ theo phạm vi được người dùng yêu cầu.

## Test mapping và quy tắc tiến độ

Mỗi checkbox của [testing](../testing/2026-09-20-feature-web-workflow.md) được gắn WFT tương ứng. Unit tests viết trước code thay đổi hành vi; TDD red/green và bằng chứng ghi trong implementation/testing khi hoàn thành từng task. Không dựng test chỉ sao chép logic implementation.

WFT01 **done** chỉ đánh dấu công tác chuẩn bị; schema migration thực thi thuộc WFT05, không được coi là đã tồn tại. WFT03–WFT09 chỉ chuyển done sau các checkbox và checks liên quan thực sự đạt. Nghiên cứu/ảnh/API fixture không thay kiểm chứng browser toàn luồng.

## Rủi ro và điều phối

- Hai workspace cùng tồn tại: code mới chỉ sửa ở worktree feature; workspace gốc giữ baseline. Không sync ngược code tự động hoặc chạy app thử trên live DB.
- Dùng DB fixture/backup riêng cho kiểm thử. Không sao chép toàn bộ artifacts chỉ để worktree có link local.
- Alias/phiên âm không bảo đảm nhận mọi tên đa ngôn ngữ; UI phải cho thấy coverage thiếu, không báo “không có trùng” như chân lý.
- Selection/revision và snapshot tải là nơi dễ mất quyết định; ưu tiên test rollback, đa tab và batch lock.
- Metadata freshness không được làm mất manual labels. Matching job/nhóm reject không được ghi lựa chọn tải thay người dùng.

**Trạng thái cuối:** WFT09 đạt. Không có task implementation bắt buộc còn lại; commit/push chưa thực hiện vì người dùng chưa yêu cầu trong lượt này.


### Đối chiếu WFT03 — 2026-09-20

WFT03 done: summary active music (watch events/ngày UTC/nguồn nhãn/tín hiệu title/coverage metadata), bộ lọc kênh, page size 25/50/100, trạng thái Còn lại trong URL. Kết quả nhập hiển thị tại Explore; input/source picker/error rollback giữ từ WFT02. 93 core/API + 8 Chromium tests đạt; fixture 7.500 import/filter/move 1,559s; summary 16,8ms; music list 37,2ms; rest filter 46,2ms. Metadata coverage chỉ đếm dữ liệu đã lưu, không coi cache là chứng nhận nhạc hoặc kiểm tra freshness (WFT04). Không có blocker/scope mới; task CLI vẫn không khả dụng theo probe trước, docs là nguồn tiến độ.

### Đối chiếu WFT07 — 2026-09-20

Không phát sinh task ngoài scope. Preview và create batch dùng cùng eligible set; start web bắt buộc token, còn service nội bộ vẫn tạo snapshot trực tiếp cho worker/test. Snapshot batch, worker và schema hiện có không đổi. 113 core/API tests đạt; browser E2E selection → download và test metadata sau sửa race đạt. WFT08 không cần migration mới cho WFT07.

### Đối chiếu WFT08 — 2026-09-20

Không có blocker hoặc migration mới. [Bảng parity](../implementation/WEB_PARITY.md) xác nhận mọi nghiệp vụ user-facing có web và test trước khi xóa parser/handler CLI. Backend/worker được giữ. Launcher mới xác minh app/API/database identity trước khi tái dùng cổng; process lạ không bị kill. Desktop entry và hướng dẫn cài Linux đã có. 113 core/API + 10 Chromium tests đạt; wheel build và help từ wheel cài không editable đạt. WFT09 là task duy nhất còn lại.

### Đối chiếu WFT09 — 2026-09-20

[Nghiệm thu cuối](../testing/WFT09_FINAL_REVIEW.md) đạt: 116 core/API, 10 Chromium, 7 research và 2 research-browser tests; wheel/lint/static checks đạt. Migration copy giữ manual/download/selection và code schema cũ từ chối schema mới. Benchmark 7.500 và bộ nhãn độc lập đã báo phạm vi/giới hạn. Security review sửa log lỗi yt-dlp để không lưu URL/token. Không có blocker hoặc scope mới.
