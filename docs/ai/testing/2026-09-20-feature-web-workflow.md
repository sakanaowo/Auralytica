---
phase: testing
title: Web workflow — Kịch bản nghiệm thu
description: Tài liệu testing cho luồng web bốn bước, đã nghiệm thu WFT09
---

# Web workflow — Kịch bản nghiệm thu

Trạng thái: **WFT02–WFT09 đã kiểm thử và nghiệm thu**. Báo cáo cuối: [WFT09_FINAL_REVIEW.md](WFT09_FINAL_REVIEW.md).

## Test Coverage Goals

Phủ mọi WA01–WA12 và các nhánh có nguy cơ mất lựa chọn/file. Báo cáo coverage đo được, không coi tỷ lệ coverage là bằng chứng accuracy matching. Fixtures tổng hợp không chứa lịch sử cá nhân.

## Unit Tests

- [x] **WFT05** — Unicode NFKC/hoa-thường/dấu câu/phụ tố có kết quả ổn định và giữ title gốc (WA04).
- [x] **WFT05** — Shoujo A / 少女A với alias đã xác nhận thành ứng viên; thiếu evidence không tự coi là chắc chắn (WA04).
- [x] **WFT05** — Tên phổ biến/nghệ sĩ khác, cover/live/remix/slowed, title trống/metadata thiếu không bị tự loại (WA05).
- [x] **WFT07** — Tập tải = tập nhạc được giữ sau dedup; filter/page/checkbox tạm không làm mất ID (WA06–WA07).

## Integration Tests

- [x] **WFT03/WFT06** — Import thất bại giữ DB cũ; reimport giữ override và lựa chọn đúng ID (WA09, WA11).
- [x] **WFT04** — Metadata còn hợp lệ cùng ID qua import, recurrence theo nguồn mới; preview cũ bị từ chối (WA08–WA09).
- [x] **WFT05/WFT06** — Quyết định dedup không đổi nhãn music/rest, không xóa file; nhóm thay đổi đánh dấu review phù hợp (WA06, WA09).
- [x] **WFT04/WFT07** — Transaction/audit rollback và khóa khi batch queued/running; batch cũ giữ snapshot (WA08, WA10).
- [x] **WFT07** — Skip file hợp lệ, file mất/hỏng cần tải lại, lỗi một item không chặn batch (WA07, WA10).
- [x] **WFT05/WFT08** — Migration bảo toàn dữ liệu, startup local/Host/Origin/escape title và alias (WA11).

## End-to-End Tests

- [x] **WFT08/WFT09** — Hoàn tất Import → Explore → Deduplicate → Download bằng browser, không CLI/CSV (WA01).
- [x] **WFT02** — Bốn URL, refresh/back/forward/direct URL, loading/empty/error và điều kiện đầu vào đúng (WA02).
- [x] **WFT03** — Explore mặc định nhóm Nhạc, chỉ số đối chiếu fixture và nguồn nhãn phân biệt; mở Còn lại để sửa (WA03).
- [x] **WFT05/WFT06** — So nhóm đa ngôn ngữ, chọn một/nhiều/tất cả, từ chối ghép, hoàn tác, reload giữ lựa chọn (WA04–WA06).
- [x] **WFT06** — Bỏ qua dedup vẫn tải tất cả bản giữ mặc định (WA06).
- [x] **WFT07** — Đổi trang/lọc rồi tải: snapshot đầy đủ, count loại dedup khác count skip file (WA07).
- [x] **WFT04** — Enrichment/preview/apply/status/lỗi/resume thao tác trên web; nhóm cập nhật đúng (WA08).
- [x] **WFT06/WFT07** — Dừng/tiếp tục/retry và restart server giữ batch, file thành công và lựa chọn (WA09–WA10).

## Performance Testing

- [x] **WFT03/WFT05/WFT09** — Fixture ≥7.500 video; đo thời gian nhập/list/filter/group, trang hợp lệ và không render toàn bộ; ghi máy/browser (WA12).
- [x] **WFT04/WFT05** — Metadata/matching job không giữ UI chờ đồng bộ không có progress (WA02, WA12).

## Matching Quality & Reporting

- [x] **WFT05/WFT09** — Bộ nhãn độc lập có cùng bài/cùng bản thu, cùng bài/khác bản, khác bài/tên tương tự, tên đa ngôn ngữ và metadata thiếu (WA04–WA05).
- [x] **WFT09** — Báo precision/recall của gợi ý khi dữ liệu đủ, không báo trên nhãn proxy hay coi Còn lại là non_music đã xác nhận.

Log lệnh/exit code và artifact sau khi thực sự chạy. Browser fixtures không chứng minh tải mọi video thật; smoke tải phải báo riêng phạm vi.


## Kịch bản bổ sung sau design review

- [x] **WFT05** — Hai bài khác nhau cùng alias/title: không ép chung song key; artist conflict được thể hiện (WA04–WA05).
- [x] **WFT05** — Liên kết A–B và B–C không có bằng chứng A–C: không ghép bắc cầu mù (WA05).
- [x] **WFT06** — Nhóm mới có video mới: selection cũ chỉ theo ID đã chọn, video mới vẫn keep (WA06, WA09).
- [x] **WFT06** — Hai tab sửa selection trên cùng revision: một thành công, tab cũ nhận 409 và không mất dữ liệu (WA06, WA08).
- [x] **WFT07** — Counts music/excluded/kept/skip/queued khớp nhau; đổi output/file giữa preview và start được xử lý (WA07).
- [x] **WFT04/WFT05** — Job đang chạy thì import/nhãn đổi: metadata giữ frozen selection; preview cũ marked stale và không ghi selection (WA08–WA09).
- [x] **WFT08** — Launcher mở loopback/browser; cổng đã bị process khác chiếm không bị kill/tái sử dụng mù (WA01, WA11).

## Workspace baseline — 2026-09-20

Worktree `feature-web-workflow`: `uv sync --locked --no-default-groups --group test --group browser` đạt; `.venv/bin/python -m unittest discover -s tests -q` **90 tests OK, exit 0**. Đây là xác minh code được chép đủ, chưa nghiệm thu bất kỳ checkbox mới nào. Chưa chạy research/browser tại bước setup.


## WFT02 — bằng chứng 2026-09-20

Tại `.worktrees/feature-web-workflow`, database/thư mục tải fixture riêng:

| Lệnh | Kết quả |
| --- | --- |
| `.venv/bin/python -m unittest discover -s tests -q` | Exit 0, **92 tests OK** |
| `.venv/bin/python -m unittest discover -s tests/browser -v` | Exit 0, **7 tests OK**, 20,576 giây |
| `.venv/bin/python -m unittest discover -s tests/browser -p test_ui.py -k workflow -v` | Exit 0, test mở rộng retry/network scope đạt |
| `node --check src/auralytica/static/app.js` và `node --check src/auralytica/static/workflow.js` | Exit 0 |
| `npx ai-devkit@latest lint --feature web-workflow` | Exit 0, docs/branch/worktree đạt |

TDD red: hai API test fail do endpoint/redirect thiếu; Chromium workflow fail do URL còn `/`. Green kiểm tra bốn trang, root theo import, snapshot counts/locks, revision ổn định, chưa có dedup không báo ready; query giữ trang/lọc khi reload/Back/Forward; retry lỗi workflow và list; Deduplicate không gọi API videos/downloads; không lỗi script và không tràn 390px. Regression tải có ca music=0 vẫn resume batch cũ.

Artifacts: `artifacts/browser-runs/wft02-explore.png`, `artifacts/browser-runs/t10-download.png`, `artifacts/acceptance-runs/t11-browser.json`. Fixture 6.400 video/6.402 lượt xem: import + thao tác 1,701 giây, luồng restart/retry/reimport/file thiếu 7,043 giây; snapshot 255 bản; 254 skip + 1 file thay thế. Đây là fixture hồi quy, **chưa thay yêu cầu ≥7.500 của WA12**, chưa đo matching hoặc mạng YouTube thật. Ảnh thumbnail được chặn trong browser tests.


## WFT03 — bằng chứng 2026-09-20

- TDD red: summary trả 404; browser thấy Còn lại vẫn mở. Green: fixture độc lập gồm 2 video nhạc/4 lượt/2 ngày UTC/1 timestamp lỗi/1 nhãn thủ công; kiểm tra repeat/day bins, title signals, metadata và top channel. Đổi import chỉ còn 1 lượt/1 video vẫn giữ override; chuyển hết sang Rest cho summary rỗng đúng.
- `.venv/bin/python -m unittest discover -s tests -q`: **93 tests OK, exit 0** (2,349s). Bao gồm Host/Origin, rollback import lỗi, source selection và reimport.
- `.venv/bin/python -m unittest discover -s tests/browser -v`: **8 tests OK, exit 0** (22,495s). Kiểm tra Nhạc mặc định; không gọi Rest trước khi mở; summary không đổi theo filter; đổi nhãn cập nhật summary; filter kênh/page size/trang/open-state giữ qua reload; an toàn title, source picker, import lỗi; luồng tải hồi quy đạt.
- `node --check` cho `app.js`, `workflow.js`, `explore.js`: exit 0. `git diff --check`: exit 0. Lint feature: exit 0.
- Benchmark `artifacts/acceptance-runs/wft03-7500.json`: Linux, Chromium 151.0.7922.34, fixture 7.500 video; import/filter/move **1,559s**, summary **16,8ms**, music page **37,2ms**, rest filter **46,2ms**, page errors `[]`. Render 50 hàng mỗi bảng khi mở, không render 7.500 hàng. Đây là một lượt đo local, không là SLA hoặc đo mạng thật.
- Screenshot `artifacts/browser-runs/wft03-explore.png` được kiểm tra ở 390px, không tràn chiều ngang.

Các bằng chứng WFT03 ban đầu chỉ nghiệm thu Explore. WFT04–WFT06 bên dưới bổ sung metadata freshness, selection và dedup; vẫn không dùng fixture quy tắc để tuyên bố recall/precision thực tế.

## WFT04–WFT06 — bằng chứng 2026-09-20

- TDD red: metadata web thiếu `run_metadata_inline`; endpoint summary/preview trả 404; dedup module/schema và API selection trả 404; browser thiếu metadata và manual alias controls; nhóm lớn thiếu `member_count`. Mỗi ca đã được chạy đỏ trước code tương ứng.
- `.venv/bin/python -m unittest discover -s tests -q`: **109 tests OK, exit 0**, 4,139 giây. Phủ migration schema 1→4, metadata scope/cache freshness/stop/resume/recovery, preview stale 409/audit rollback/batch lock, alias mơ hồ và không nối bắc cầu, dedup stale, selection atomic/revision/reimport/default keep/rejection và phân trang nhóm lớn.
- `.venv/bin/python -m unittest discover -s tests/browser -v`: **10 tests OK, exit 0**, 25,954 giây. Phủ metadata → preview → apply không CLI; Shoujo A / 少女A → lựa chọn → reject/undo → reload; regression import/explore/download/restart/reimport và layout hẹp.
- `node --check` cho `app.js`, `workflow.js`, `explore.js`, `metadata.js`, `dedup.js`: exit 0. `git diff --check`: exit 0.
- Fixture exact-title 7.500 video/3.750 nhóm: dedup **0,134 giây** trong lượt cuối; list chỉ trả 20 nhóm và tối đa 50 thành viên/trang. Đây là benchmark tổng hợp local, không phải precision/recall thực tế.
- Đã kiểm tra trực quan `artifacts/browser-runs/wft03-explore.png` và `wft06-dedup.png` ở 390px: không tràn ngang; title gốc, alias evidence, selection và metadata controls đọc được.

## WFT07 — bằng chứng 2026-09-20

- TDD red: `batches.eligible_snapshot` chưa tồn tại; API start chưa nhận preview token. Green kiểm tra explicit exclude, token stale, output/file đổi, snapshot bất biến và không tạo batch khi conflict.
- `.venv/bin/python -m unittest discover -s tests -q`: **113 tests OK, exit 0**, lượt cuối 4,445 giây. Test mới phủ counts music/excluded/kept/skipped/queued/needed, selection revision, file state/output binding, HTTP 409 và ID chính xác trong `download_items`.
- Chromium Shoujo A / 少女A xác nhận 2 Nhạc, 1 excluded, 1 kept và batch chỉ chứa ID được giữ. Regression tải hiện có tiếp tục phủ filter/page tạm, file skip/mất, một item lỗi, stop/resume/retry, restart server và giữ 255-ID snapshot cũ.
- Lượt full browser đầu phát hiện metadata poll cũ ghi đè thông báo apply; chuyển thông báo sang `preview-summary`. Chạy lại toàn suite: `.venv/bin/python -m unittest discover -s tests/browser -v` → **10 tests OK, exit 0**, 25,660 giây.
- Đã xem `artifacts/browser-runs/wft07-download.png` ở 390px: năm count và batch một video đọc được, không tràn ngang. Audio là fixture tổng hợp; WFT07 không chạy lại smoke mạng/audio thật.
- `node --check` cho năm module JS, `git diff --check` và `npx ai-devkit@latest lint --feature web-workflow`: exit 0.

Checkbox WFT03/WFT05/WFT09 và matching quality WFT05/WFT09 vẫn mở vì benchmark/navigation đã đạt nhưng báo cáo chất lượng độc lập và nghiệm thu cuối chưa làm.

## WFT08 — bằng chứng 2026-09-20

- TDD red: help còn liệt kê 13 subcommand, không đối số chỉ in help, chưa có `launch`, port ownership, health identity hoặc desktop entry. Green: parser chỉ còn port/database/no-browser; command cũ trả exit 2.
- Launcher unit/integration kiểm tra loopback, browser chỉ mở sau health, reuse đúng cùng database, từ chối database khác/process lạ mà không kill. `/api/health` không lộ đường dẫn database.
- Browser acceptance 6.400 video đã chuyển status/list/reimport sang HTTP/UI; full suite **10 tests OK, exit 0**, 26,606 giây. Không test browser nào gọi subcommand nghiệp vụ.
- Core/API **113 tests OK, exit 0**, 4,268 giây. Các test metadata/audit/preview/download cũ chuyển sang service/API; backend vẫn được kiểm tra độc lập.
- `uv build --wheel --out-dir /tmp/auralytica-wft08-dist` thành công. Wheel cài không editable bằng `pip --no-deps`; `auralytica --help` exit 0 và chỉ hiện ba tùy chọn launcher.
- README, metadata/preview docs và design MVP được cập nhật hoặc đánh dấu lịch sử; UI upload không còn hướng người dùng tới CLI đã gỡ. Desktop entry có `Exec=auralytica`, `Terminal=false`.

## WFT09 — bằng chứng 2026-09-20

- Full core/API **116 tests OK**; Chromium **10 tests OK**; research **7 tests OK**; research-browser **2 tests OK**. Node syntax, compileall, diff check, AI DevKit lint và wheel build đều exit 0.
- Database backup fixture giữ manual label, completed download và selection/revision; binary mô phỏng schema v3 từ chối v4 mà không ghi. Migration lỗi vẫn rollback.
- Lượt Chromium cuối với 7.500 video: import/filter/move 1,596 giây; summary 16,0 ms; music page 49,7 ms; rest search 36,8 ms; page errors rỗng. Dedup 7.500/3.750 nhóm mất 0,137 giây.
- Bộ nhãn độc lập 16 video/5 cặp đúng cho precision=0,80 và recall=0,80 trên fixture tổng hợp. Không suy ra accuracy production; mọi bản vẫn keep mặc định.
- Security review sửa việc lưu exception thô từ yt-dlp; error log không giữ URL/token. Host/Origin/body/input/render/network scope/recovery không có finding chặn.

Chi tiết và giới hạn: [WFT09_FINAL_REVIEW.md](WFT09_FINAL_REVIEW.md).
