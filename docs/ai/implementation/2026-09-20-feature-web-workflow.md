---
phase: implementation
title: Web workflow — Implementation status
description: Tài liệu implementation cho luồng web bốn bước, chưa nghiệm thu
---

# Web workflow — Implementation status

Đã triển khai và nghiệm thu WFT02–WFT09: bốn trang web, Explore music-first, metadata, dedup/selection, tải đúng tập được giữ và launcher local web-only. [Review cuối](../testing/WFT09_FINAL_REVIEW.md) không còn finding chặn.


## WFT01 — workspace và baseline đã xong

Ngày 2026-09-20, worktree `.worktrees/feature-web-workflow`, branch `feature-web-workflow`. Đã chép/đối chiếu hash 43 file modified/untracked từ workspace gốc, không commit/stash/reset. Môi trường riêng cài theo lockfile; 90 test core/API đạt và lint feature đạt. Không copy live DB/Takeout/audio. File code hiện có là nền tảng, chưa đổi cho bốn trang. Task tiếp theo WFT02 — navigation/routes/workflow state.

## WFT02 — done (2026-09-20)

Đã thêm bốn route `/import`, `/explore`, `/deduplicate`, `/download`, root redirect theo active import và GET `/api/workflow`. State đọc cùng SQLite snapshot; revision chỉ là fingerprint trạng thái hiển thị, không dùng làm token ghi selection. Không đổi schema hoặc classifier.

Shell dùng HTML chung, `workflow.js` điều phối route/query/state; `app.js` giữ handler nhập/duyệt/tải. Chỉ Explore tải danh sách/ảnh, chỉ Download poll batch và preview. Link trang native và history state giữ lọc/phân trang khi reload/Back/Forward. Không khởi động job metadata/audio khi điều hướng. Deduplicate báo rõ chưa có matching và cho đi tiếp với mọi bản; selection/dedup còn thuộc WFT05–WFT07.

TDD: 2 API tests mới thất bại do thiếu redirect/endpoint (404), browser test mới thất bại do root còn `/`. Sau implementation: 10 tests `test_web.py` và 1 Chromium workflow test đạt. Regression hoàn tất: 92 core/API + 7 Chromium tests đạt; workflow test bổ sung lỗi danh sách/retry và xác minh Deduplicate không gọi API danh sách/tải cũng đạt. Hai file JavaScript qua `node --check`.


### Kết quả và giới hạn

- Thay đổi: `web.py`, `static/index.html`, `static/app.js`, `static/workflow.js`, `static/style.css`, `tests/test_web.py`, `tests/browser/test_ui.py`.
- Giữ lựa chọn trên server, root quyết định theo active import, workflow phản ánh khóa batch. Import thành công sang Explore; lỗi không đổi lịch sử. Download vẫn hiện snapshot cũ khi không còn nhạc.
- Browser regression đã cập nhật thao tác qua trang riêng, vẫn kiểm tra số snapshot độc lập bộ lọc/checkbox, stop/resume/retry/restart/reimport/file thiếu. Không dùng live DB, không tải audio thật.
- Đã xem screenshot `artifacts/browser-runs/wft02-explore.png` ở 390px: navigation 2×2, bảng xếp dọc, không tràn chiều ngang. Màn hình desktop 1440px được chạy trong regression.
- Shell chung chỉ khởi động truy vấn theo trang; chưa tách toàn bộ handler hiện có thành module riêng từng nghiệp vụ. Việc tái cấu trúc sâu tiếp tục theo WFT03/WFT04, không đổi contract backend cũ.
- WFT02 không chứng minh nghiệm thu WA01–WA12 toàn feature. Matching đa ngôn ngữ, selection, analytics và gỡ CLI chưa được cung cấp. Chưa commit/push; app gốc đang chạy không tự đổi sang worktree.


## WFT03 — done (2026-09-20)

Đã thêm summary server-side chỉ cho nhóm Nhạc của active import; phân biệt lượt/ngày UTC, timestamp thiếu, nhãn user/automatic, tín hiệu title và metadata cache/evidence. Bảng mặc định chỉ tải Nhạc, Còn lại mở khi cần; channel filter và page size 25/50/100 lưu trên URL. Summary toàn nhóm không phụ thuộc lọc bảng. Không sửa classifier hoặc tự fetch metadata. Test red endpoint 404 và Rest chưa thu gọn; test API + browser mới đã green. Regression đạt: 93 core/API + 8 Chromium tests. Fixture 7.500 video và screenshot 390px đã kiểm chứng.


WFT03 thay đổi `explore.py`, `web.py`, `review.py`, `static/explore.js`, shell/app/workflow/CSS và tests. API summary đọc cùng SQLite snapshot, chỉ nhóm music của active import; dùng timestamp UTC đã chuẩn hóa. Missing timestamp được đếm riêng, không chế tạo ngày hoặc thời lượng nghe. Thống kê cache và applied evidence có thể giao nhau; `available` là hợp hai tập, `missing` là phần bù trong Nhạc. Không gọi network metadata; TTL/refresh thuộc WFT04. Tái dùng MUSIC/TALK regex chỉ để mô tả, không đổi classifier. Kênh thiếu được đặt thành nhóm chưa biết; top 20 theo số video, tie-break ổn định; chỉ trả 30 ngày có xem gần nhất nhưng tổng ngày tính toàn nguồn.

Còn lại đóng mặc định, không query/render ảnh trước khi mở; đóng panel bỏ selection tạm và bỏ qua response cũ. URL giữ trạng thái mở, kênh, page size, trang và filter. Summary giữ scope toàn nhóm dù người dùng lọc bảng; cập nhật sau chuyển nhóm. Page size hợp lệ 25/50/100, đổi filter về trang 1. Tên kênh được lọc chính xác hoặc dùng channel key/URL hiện có. Nội dung nguồn render qua textContent.

Đã đọc screenshot `artifacts/browser-runs/wft03-explore.png`: ở 390px summary và bảng nằm trong viewport, Còn lại thu gọn, không tràn ngang. Test thumbnail được chặn, audio dùng fixture tổng hợp. Có một lần script cập nhật test gây IndentationError ở helper lồng nhau; đã sửa và chạy lại toàn bộ browser suite đạt. Chưa commit/push, chưa chuyển live app sang worktree.

## WFT04 — done (2026-09-20)

Metadata có scope music/rest/all và giới hạn 1–1000 trước khi chạy; cache, tiến độ, lỗi và audit events hiển thị trên Explore. Collector chạy nền mặc định, có stop/resume và giữ snapshot video ID. Preview được tạo/lưu trên server; apply chỉ nhận preview ID, kiểm tra state hash trong cùng transaction và trả 409 khi stale hoặc batch khóa. Không có upload CSV/path trong web.

Evidence đã áp dụng gắn video/provider/observation/fetched_at, không còn bị bỏ chỉ vì source hash Takeout đổi. Classification vẫn tính watch_count/watch_days từ active import; override thủ công luôn thắng. Missing/error metadata không đổi nhóm. Migration schema 3 chỉ thêm `classification_previews`, giữ dữ liệu cũ. API tests và Chromium fixture đã kiểm chứng metadata → preview → apply → reload/reimport không cần CLI. WFT05 bắt đầu từ schema 4 và dedup local.

## WFT05–WFT06 — done (2026-09-20)

Schema 4 bổ sung alias, immutable dedup run/group/member evidence, selection theo video ID và rejected fingerprint. Normalizer dùng NFKC/casefold, chuẩn hóa dấu/khoảng trắng và chỉ bỏ suffix allowlist; raw title cùng marker cover/live/remix/slowed/instrumental vẫn được lưu và hiển thị. Nhóm dùng exact normalized key hoặc song key từ alias xác nhận. Alias trùng nhiều song key được xem là mơ hồ và không chọn ngẫu nhiên; không có fuzzy, dịch tự động hoặc nối bắc cầu.

Deduplicate có URL trực tiếp, quét lại, phân trang 20 nhóm và 50 thành viên, ảnh/link/title/kênh/evidence, form xác nhận alias theo video ID, checkbox giữ từng bản, giữ toàn nhóm, từ chối nhóm và hoàn tác. Selection mặc định keep; exclude không sửa user_group/auto_group, lịch sử hoặc file. Selection và rejection dùng global expected revision, validate toàn bộ ID trước transaction, audit và trả 409 cho tab cũ/batch lock. Reimport giữ lựa chọn ID cũ; ID mới mặc định keep; input hash làm run cũ hiện stale.

Dedup chạy local tuyến tính theo map key. Fixture tổng hợp 7.500 video/3.750 cặp mất khoảng 0,14 giây trong lượt kiểm chứng và API chỉ trả page hiện tại; vì vậy baseline chạy đồng bộ có thông báo loading thay vì thêm worker. Đây là design deviation nhỏ so với job progress tổng quát; nếu matching sau này thêm fuzzy/model và chậm đáng kể, cần chuyển cùng contract run sang worker. WFT07 còn phải dùng selection trong preview/batch download; hiện Download vẫn tải toàn bộ Nhạc.

Verification cuối: 109 core/API tests và 10 Chromium tests đạt; JavaScript syntax, diff whitespace và feature lint đạt. Hai ảnh 390px đã được kiểm tra trực quan. Không có blocker hoặc task mới trong WFT04–WFT06. Task tracing CLI vẫn không tồn tại theo probe trước nên planning/implementation/testing/dashboard là nguồn tiến độ. Không commit/push và không sửa live DB.

## WFT07 — done (2026-09-20)

`eligible_snapshot` là nguồn duy nhất cho preview và tạo batch: lấy toàn bộ Nhạc của active import, trừ đúng các ID có `download_selections.keep=0`, không đọc filter/page/checkbox tạm. Preview trả riêng music/excluded/kept/skipped/queued; `needed` là alias tương thích cho UI. Token SHA-256 gắn active import, selection revision, tập ID/keep, output đã resolve và trạng thái file hợp lệ; start web bắt buộc gửi token. Token cũ trả 409 trước khi tạo batch. File được kiểm tra lại ngay trước khi ghi item, nên file biến mất chuyển sang queued.

Batch mới chỉ chứa ID được giữ. Batch đã tạo vẫn là snapshot bất biến khi selection/nhãn đổi sau lúc dừng; resume/retry không thay ID. Việc tạo lặp khi có batch queued/running vẫn trả batch đó. UI giải thích tải mọi bản được giữ kể cả ngoài trang/lọc, hiển thị năm số đếm và nói rõ lượt cũ giữ danh sách đã chốt.

TDD red xác nhận thiếu eligible function và API chưa nhận token. Sau implementation, 113 core/API và 10 Chromium tests đạt. Chromium kiểm tra Shoujo A / 少女A: exclude một ID, preview 2/1/1 và batch chỉ có ID còn lại; regression hiện có tiếp tục phủ filter không ảnh hưởng snapshot, skip file, file mất, lỗi item, stop/resume/retry, restart và worker lock. Screenshot mobile `artifacts/browser-runs/wft07-download.png` đã kiểm tra, không tràn ngang. Một race UI cũ được phát hiện: metadata poll ghi đè thông báo apply; thông báo đã chuyển sang `preview-summary` và full browser suite xanh lại.

## WFT08 — done (2026-09-20)

[Bảng web parity](WEB_PARITY.md) đối chiếu toàn bộ nghiệp vụ cũ với bốn trang và evidence. Entrypoint được rút còn launcher kỹ thuật `auralytica [--port/--database/--no-browser]`; backend/worker vẫn là module nội bộ. Launcher không đối số mở browser sau khi health xác nhận server sẵn sàng. Instance có sẵn chỉ được tái dùng khi app/API/database identity trùng; cổng lạ hoặc database khác bị từ chối, không kill process.

Thêm `/api/health` chỉ trả app, API version và SHA-256 rút gọn của đường dẫn database, không lộ path. Desktop entry Linux chạy `auralytica` với `Terminal=false`. README đã chuyển sang web-only; tài liệu MVP cũ được đánh dấu lịch sử. Core/API tests cũ gọi CLI nghiệp vụ đã chuyển sang service hoặc HTTP, và browser acceptance restart/reimport/status/list hiện không gọi CLI.

TDD bắt đầu với bảy lỗi/fail đúng hành vi thiếu. Kết quả cuối: 113 core/API + 10 Chromium tests đạt; integration subprocess chạy launcher thật, reuse cùng database và từ chối database khác trên cùng cổng. Wheel build thành công, cài không editable và help mới chạy được. Không xóa importer/metadata/dedup/downloader/audit/worker; chỉ xóa bề mặt lệnh nghiệp vụ và cập nhật caller/test/tài liệu. Không có design deviation hoặc task mới; giới hạn upload 63 MiB và cài desktop entry thủ công được ghi rõ.

## WFT09 — Nghiệm thu và hardening

Thêm fixture chất lượng dedup độc lập và test migration trên database copy có manual label, completed download và selection revision. Kết quả fixture matching là precision/recall 0,80/0,80 trong phạm vi 16 video tổng hợp; báo cáo không suy ra accuracy production. Review network/log phát hiện yt-dlp child có thể chuyển exception thô vào SQLite; test đỏ tái hiện nguy cơ URL/token rồi implementation đổi sang error code và thông báo an toàn. Full suite cuối đạt 116 core/API + 10 Chromium cùng các suite research; chi tiết ở [WFT09 final review](../testing/WFT09_FINAL_REVIEW.md).
