---
phase: testing
title: Auralytica — Kịch bản nghiệm thu MVP
description: Kết quả S01–S12, nghiệm thu AC01–AC08 và kiểm chứng môi trường sạch
---

# Auralytica — Kế hoạch kiểm chứng

> Đây là lịch sử kiểm thử MVP. WFT08 đã gỡ CLI nghiệp vụ; xem [testing web workflow](2026-09-20-feature-web-workflow.md) cho contract và lệnh kiểm chứng hiện hành.

Cập nhật: **2026-09-10**. **S01–S12 đạt**, gồm [quickstart môi trường sạch](QUICKSTART.md); [AC01–AC08 đạt trong phạm vi Linux/JSON](ACCEPTANCE.md). Các kịch bản liên kết [kế hoạch triển khai](../planning/README.md), [Requirements](../requirements/README.md) và [Thiết kế](../design/README.md).

## FE02 — kiểm chứng collector/cache/audit, 2026-09-11

**82 test core/API + 6 test Chromium đạt**, exit 0; wheel build đạt. Không diễn giải kiểm thử chức năng thành accuracy phân loại.

| Lệnh / bằng chứng | Kết quả |
| --- | --- |
| `.venv/bin/python -m unittest discover -s tests -v` | 82 tests OK. [Log local](../../../artifacts/testing-runs/fe02-core.log) |
| `.venv/bin/python -m unittest discover -s tests/browser -v` | 6 tests OK; luồng 6.400 video/import/review/download/restart/reimport dùng audio fixture, không phát sinh page error |
| `uv build --wheel --out-dir /tmp/auralytica-fe02-dist` | Exit 0; wheel chứa metadata.py/audit.py và dependency ytmusicapi==1.12.2 |
| Smoke collector trên bản sao DB, đúng 18 ID đã duyệt | Lượt một 18 network calls; lượt hai 0 calls/18 cache hits; video rows giữ nguyên. [Summary](../../../artifacts/metadata-smoke/fe02-20260911T081317Z/summary.json) |

TDD: migration fail `1 != 2` trước thay code; test audit decision fail vì chưa có event; collector thiếu service; CLI metadata bị parser từ chối. Sau triển khai các ca tương ứng đạt.

Kiểm chứng bổ sung cho S02/S04/S05: migration lỗi rollback cả version/tables, giữ review/download; audit lỗi rollback sửa nhóm; cache TTL/refresh/provider version, exact ID, type lạ/malformed, missing/UNPLAYABLE không thành non-music; retry giới hạn và attempt liên tục sau resume; snapshot không đổi khi active import đổi; khóa tiến trình thật/kill recovery; CLI status/export có dependency cache và không ghi đè file. Rules-v1 không đổi quyết định; các test baseline vẫn đạt.

Khoảng trống còn lại: chưa đánh giá precision/recall hoặc music-primary của player UGC; chưa có UI metadata/reason mới; chưa nghiệm thu throttling quy mô lớn, retention audit hoặc môi trường OS mới. FE03/FE04 theo [planning](../planning/README.md). Cảnh báo Starlette TestClient/httpx vẫn xuất hiện như trước, không làm test fail.

## Test Coverage Goals

### FE03 — nghiên cứu offline, 2026-09-13

Notebook 05 chạy đủ **4 cell code (8 cell tổng cộng)**; `.venv/bin/python -m unittest discover -s tests/research -v` → **5 tests OK**, exit 0. Bộ nghiên cứu dùng pandas/group notebook, chạy tách core/API. Kiểm tra phép tính candidate, guard podcast/gameplay/Shorts, category Gaming, missing/error/mismatch, UNPLAYABLE, nhãn thiếu lớp và CSV sai ID/snapshot/label. Đây là synthetic logic checks, không thay kiểm chứng video thật.

[Báo cáo FE03](../../references/residual-evaluation.md) ghi 70 mẫu discovery, 5 nhãn music/65 chưa resolve, không có precision/recall hoặc ngưỡng đã chốt. Mẫu mới không trùng holdout; notebook không gọi mạng hoặc sửa app DB. Không chạy lại suite runtime/browser vì lượt này chỉ thêm công cụ nghiên cứu offline và tài liệu.

Kiểm chứng hành vi import, hai danh sách và tải audio, đặc biệt persistence, snapshot và khôi phục. Mỗi Sxx có task Txx chịu trách nhiệm. Không dùng lint tài liệu hoặc kết quả notebook làm bằng chứng ứng dụng hoạt động.

| Kịch bản | Task | AC | Hành vi phải chứng minh |
| --- | --- | --- | --- |
| S01 | T01 | AC07, AC08 | Đúng Python có sqlite3, transaction hoạt động; CLI help chạy trong môi trường cài mới, không cần notebook hoặc API key. |
| S02 | T02 | AC02, AC06, AC07 | Schema/migration, uniqueness, rollback, mở lại DB giữ review và trạng thái tải. |
| S03 | T03 | AC01, AC02 | JSON Unicode, video lặp giữ event count; quảng cáo/URL không phải video/thiếu dữ liệu được thống kê; thiếu nguồn/HTML/nhiều nguồn được xử lý; nhập lại idempotent, nhập lỗi giữ dữ liệu cũ. |
| S04 | T04 | AC03 | Topic/library chỉ trên ID lịch sử; bằng chứng Shorts/podcast/giải trí và ca không rõ; VEVO/repeat/category/hashtag không quyết định một mình; manual override thắng gợi ý và nhãn kênh. |
| S05 | T05 | AC03, AC04, AC07 | Mỗi video thuộc đúng một nhóm; chuyển hai chiều từng/hàng loạt, tổng và lọc đúng, reload giữ kết quả, lỗi transaction không chuyển dở, file audio không bị xóa. |
| S06 | T06 | AC01, AC07, AC08 | CLI/web chung DB, folder upload chỉ gửi dữ liệu cần thiết về localhost; validation, Host/Origin và escape dữ liệu; lỗi import không phá thư viện. |
| S07 | T07 | AC04 | Hai bảng có ảnh/link/lý do/lượt xem; kéo thả/chọn folder; nút chuyển, tick trang hiện tại và xóa tick khi đổi lọc/page; placeholder ảnh lỗi, empty/error state, reload. |
| S08 | T08 | AC02, AC05, AC06, AC07 | Batch lấy mọi music kể cả ẩn, không lấy rest; file hợp lệ được skip; double-click và hai tiến trình chỉ có một worker; mutation bị khóa; snapshot không đổi khi resume. |
| S09 | T09 | AC05, AC06 | Audio đúng video, giữ codec; lỗi một video vẫn tiếp tục; dừng/mạng/restart, file mất/đổi kích thước, tên trùng, permission/disk full; partial không completed. |
| S10 | T10 | AC04, AC05, AC06, AC07 | Nút tải cả nhóm không phụ thuộc tick/filter/page, đếm đúng và vô hiệu hóa khi không còn việc; polling/per-file errors, stop/resume dùng được cả CLI/web. |
| S11 | T11 | AC01, AC02, AC03, AC04, AC05, AC06, AC07, AC08 | E2E import → sửa hai nhóm → tải batch → khởi động lại; ~6.400 video, metadata/ảnh thiếu; đối chiếu mọi AC với bằng chứng. |
| S12 | T12 | AC01, AC06, AC07, AC08 | Quickstart trên môi trường sạch dẫn đến thao tác được; hướng dẫn khôi phục và giới hạn đúng thực tế. |

## Unit Tests

Khi triển khai: parser/chuẩn hóa ID và event count (S03), bảng ca gợi ý và override (S04), trạng thái batch/đánh giá file (S08–S09). Dùng dữ liệu biết trước kết quả; không viết test chỉ lặp lại implementation.

## Integration Tests

SQLite thật trong thư mục tạm cho S02–S06; request API và CLI dùng chung DB. Dùng nhiều tiến trình cho khóa worker S08, adapter downloader giả lập để tạo lỗi có kiểm soát cho S09–S10. Không chỉ mock khóa rồi tuyên bố tránh được race.

## End-to-End Tests

S07/S10/S11 chạy browser với folder fixture, chuyển hai chiều, đổi trang/lọc rồi tải. Backend giả lập tải cho toàn bộ fixture; smoke tải thật một mẫu nhỏ để xác minh ID, codec và phát audio. Test giả lập không chứng minh yt-dlp tải được video thật.

## Test Data

Fixture tổng hợp gồm Topic, library match ngoài/trong lịch sử, tiêu đề ngắn/Unicode, podcast xem lặp, nhạc category Entertainment, dấu hiệu Shorts chưa chắc, metadata thiếu, video lặp và bản ghi lỗi. Có expected counts độc lập. Sinh tập ~6.400 video để đo UI.

Export cá nhân, audio và log chứa dữ liệu thật giữ trong artifacts local, không commit. Smoke mạng ghi video ID/kết quả ở log local; báo cáo chia sẻ chỉ giữ số liệu và trạng thái cần thiết.

## Test Reporting & Coverage

**S01 — đạt ngày 2026-09-08:** `tests/test_cli.py` và `tests/test_runtime.py`, dùng unittest chuẩn Python. Ba test CLI đã fail với code in lời chào (exit 1), sau implementation cả 4 test đạt (exit 0). SQLite probe kiểm tra runtime thật, không phải regression test cho một lỗi đã tái hiện.

| Lệnh đã chạy | Kết quả |
| --- | --- |
| `.venv/bin/python -m unittest discover -s tests -v` | 4 test, OK, exit 0 |
| `UV_PROJECT_ENVIRONMENT=/tmp/auralytica-t01-clean uv sync --locked --no-default-groups` | Tạo môi trường mới, chỉ cài auralytica 0.1.0, exit 0 |
| `/tmp/auralytica-t01-clean/bin/python -m unittest discover -s tests -v` | 4 test, OK, exit 0 |
| `/tmp/auralytica-t01-clean/bin/auralytica --help` | Help đúng ứng dụng, exit 0 |

Interpreter kiểm chứng: Python 3.11.16, SQLite 3.53.1. Commit Unicode, rollback và mở lại database đạt. Kiểm tra installed distributions chỉ có auralytica; không cần notebook, API key hoặc test dependency bên ngoài. Chưa kiểm chứng Python version/OS khác; chưa có CLI/web chia sẻ dữ liệu hay tải audio nên AC07–AC08 vẫn chưa đánh dấu đạt.

Từng task tiếp theo ghi lệnh thực tế, exit code, số pass/fail và hạn chế. Báo cáo S11 ánh xạ AC01–AC08 tới bằng chứng; chỉ cập nhật checkbox requirements sau khi có đủ kiểm chứng.

Coverage hỗ trợ tìm nhánh lỗi còn thiếu; không thay thế kiểm chứng browser, nhiều tiến trình và audio thật. Không đặt tỷ lệ coverage chưa có cơ sở.

### S02 — đạt ngày 2026-09-08

`tests/test_storage.py` có 10 test dùng database thật trong thư mục tạm. Chín test ban đầu lỗi vì chưa có `open_database` (exit 1); sau implementation và thêm kiểm tra migration lỗi, toàn suite **14 test OK, exit 0** với `.venv/bin/python -m unittest discover -s tests -v`.

Đã kiểm chứng: schema v0 trống → v1; mở lại v1 giữ dữ liệu; từ chối version tương lai; migration xung đột rollback toàn bộ DDL và giữ dữ liệu cũ; khóa ngoại, uniqueness, nhóm/trạng thái hợp lệ; sự kiện xem lặp; manual override/reset; settings upsert; review/nhãn kênh/kết quả tải tồn tại sau reopen; transaction rollback và từ chối nesting.

Chưa có migration v1 → v2 vì chưa có schema v2; chưa kiểm chứng khóa worker nhiều tiến trình (T08), parser export (T03) hoặc file tải thật (T09). Kết quả completed trong test là dữ liệu giả lập, không phải audio đã tải.

## Manual Testing

Kéo thả và chọn folder trên browser Linux; kiểm tra keyboard focus, tên nút và checkbox rõ ràng, hai bảng dễ đọc; ảnh lỗi và tên dài/Unicode. Xác nhận nút tải toàn bộ không bị giới hạn bởi bộ lọc. Phát audio smoke, thử dừng/khởi động lại và đọc thông báo lỗi.

## Performance Testing

S11 ghi thời gian import, thời gian phản hồi lọc/chuyển/trang và độ đáp ứng UI với ~6.400 video; ghi máy/browser và kích thước dataset. Không suy diễn thời gian tải toàn bộ từ fixture giả lập, chưa cam kết ngưỡng hiệu năng khi chưa đo.

## Bug Tracking

Lỗi gắn Sxx/Txx/AC tương ứng, bước tái hiện, mong đợi/thực tế và bằng chứng. Mất dữ liệu, tải sai nhóm, tải trùng hoặc mất sửa tay chặn nghiệm thu MVP. Thêm regression test cho lỗi đã tái hiện; cập nhật dashboard với blocker và task xử lý.

### S03 — đạt 2026-09-09

6 test importer và 2 test CLI mới; đã chạy bước red trước implementation. `.venv/bin/python -m unittest discover -s tests -v`: **22 test OK, exit 0**. Fixture bao phủ Unicode, UTC, repeat, ads, URL ngoài YouTube, dữ liệu thiếu/sai, JSON hỏng, HTML, nhiều nguồn/--history, nguồn ngoài folder, library chỉ match ID lịch sử và thay đổi library khi nhập lại, giữ override và active import.

Smoke: `.venv/bin/auralytica import 'artifacts/YouTube and YouTube Music' --database artifacts/import-runs/t03.sqlite3` chạy hai lần exit 0; lần sau reused=true. Số liệu 9.700 dòng, 41 ads, 258 non-video, 9.401 video events, 6.385 video, 58 library matches. Đối chiếu bằng sqlite3 + csv: toàn bộ ID và watch_count khớp `signals-v2/video_features.csv`, một import sau chạy lặp. Database thử nghiệm giữ trong artifacts local.

Các AC toàn luồng chưa nghiệm thu; classifier/web/download chưa có. Test expected event count được sửa từ 7 thành 6 vì fixture gồm 8 dòng trừ 1 quảng cáo và 1 dòng không phải object; không đổi quy tắc để khớp số sai.

### S04 — đạt 2026-09-10

`tests/test_classification.py`: bảng 11 ca gồm Topic/library, tên kênh không phải Topic, podcast lặp, VEVO/music hints, hashtags/duration, category Entertainment, URL Shorts, xung đột và nhãn kênh; kiểm tra evidence có code/source. Integration kiểm chứng phân loại cùng import, reimport giữ override, override thắng nhãn kênh, không sửa video ngoài active import, giữ Shorts evidence khi có cả watch URL. Thêm CLI classify test (thiếu import/empty import/rerun).

Bước red chạy trước code: suggest chưa tồn tại và auto_group còn rest; CLI classify chưa được nhận. Sau triển khai toàn suite **26 test OK, exit 0** (`.venv/bin/python -m unittest discover -s tests`). Smoke import + classify trên artifacts/import-runs/t03.sqlite3: 255 music, 6.130 rest, 6.385 video; cả hai lệnh exit 0. Không diễn giải kết quả này thành accuracy; chưa audit nhãn độc lập. AC toàn luồng còn chưa nghiệm thu.

### S05 — đạt 2026-09-10

`tests/test_review.py` thêm 5 integration test SQLite thật và `test_cli.py` thêm 1 luồng subprocess import/list/move/list. Bước red: list_videos/move_videos chưa tồn tại và CLI chưa nhận list. Sau triển khai: **32 test OK, exit 0**, lệnh `.venv/bin/python -m unittest discover -s tests`.

Bao phủ tổng nhóm khác filtered_count, Unicode/literal search, channel/reason, sort ổn định và page vượt cuối; watch_count chỉ active import; chuyển hàng loạt hai chiều và ID lặp; reopen giữ manual; nhóm/lệnh/page sai; ID không tồn tại hoặc ngoài import không chuyển một phần; file audio fixture và completed record được giữ. Kết quả CLI phản ánh thay đổi giữa các tiến trình.

Smoke chỉ đọc trên artifacts/import-runs/t03.sqlite3: tổng music=255/rest=6130, mỗi trang 50 dòng, hai lần list mất 0,086 giây. Chưa benchmark browser, chưa đánh dấu AC04/AC07 toàn giao diện đạt; S06–S12 còn chờ.

### S06 — đạt 2026-09-10

`tests/test_web.py` có 6 test: upload/library và dữ liệu JSON; API↔CLI/SQLite cùng review; Host/Origin/port/missing Origin; JSON hỏng/nguồn trùng giữ thư viện; traversal/HTML/file không liên quan; body limit cả có/không Content-Length; query/move validation. `tests/test_cli.py` thêm serve loopback/port và từ chối host mạng/port sai. Bước red chạy trước code create_app và serve.

`.venv/bin/python -m unittest discover -s tests`: **40 test OK, exit 0**. Môi trường mới tạo bằng `UV_PROJECT_ENVIRONMENT=/tmp/auralytica-t06-clean uv sync --locked --no-default-groups --group test`; `/tmp/auralytica-t06-clean/bin/python -m unittest discover -s tests` cũng **40 test OK, exit 0**, không có notebook. TestClient phát cảnh báo deprecation httpx; test không fail. Cả hai lần chạy TestClient ngoài giới hạn sandbox do app tối giản cũng treo trong sandbox; đây là giới hạn môi trường chạy kiểm thử đã tái hiện, không phải xác nhận API treo.

Smoke thực qua urllib + subprocess serve trên cổng loopback tạm: root 200, multipart import một fixture, GET list và POST move trả đúng kết quả; process được dừng và dữ liệu tạm dọn trong finally. Kết quả PASS, exit 0. Chưa chạy browser/DOM, nên S07 và AC04 toàn giao diện vẫn chờ; không coi JSON chứa title thành bằng chứng escape HTML đã xong.

### S07 — đạt 2026-09-10

1 test API mới xác nhận root HTML/static assets; bước red root còn JSON. `tests/browser/test_ui.py` là suite Chromium riêng, bước red không có heading/dropzone trước UI. 4 test đạt: folder picker + 54 video + hai chiều/bulk/reload/filter/page; drag/drop directory thật qua Chromium CDP + import JSON lỗi giữ dữ liệu; dialog multi-history; 6.400 video + Unicode-safe rendering + viewport hẹp. Test ảnh lỗi chỉ xét ảnh đã vào viewport vì lazy-load giữ ảnh ngoài màn hình chưa tải.

- `.venv/bin/python -m unittest discover -s tests`: 41 test OK (core/API).
- `.venv/bin/python -m unittest discover -s tests/browser -v`: 4 test OK, exit 0; Chromium, viewport desktop 1440×1000 và mobile 390×844.
- Fixture 6.400 video: import/filter/move 1,39 giây, pageerror rỗng. Thumbnail network được abort có chủ đích; placeholder hoạt động, không chứng minh ảnh YouTube thật luôn truy cập được.
- `node --check src/auralytica/static/app.js`: exit 0.
- `uv build --wheel --out-dir /tmp/auralytica-t07-dist`: thành công; zip kiểm chứng index.html/app.js/style.css có trong wheel.

Ảnh artifacts/browser-runs/t07-ui.png dùng dữ liệu tổng hợp và đã kiểm tra trực quan. Không chạy native browser Firefox/Safari hoặc thử tải audio; S08–S12 chờ. AC toàn MVP còn chưa nghiệm thu vì batch/download chưa có. Các kết quả test T01–T06 ở trên là lịch sử từng mốc, không phải lệnh cài dependencies hiện hành.

### S08 — đạt 2026-09-10

`tests/test_batches.py` có 7 test: toàn bộ music dù list filter/page chỉ hiện một; create trùng trả batch cũ, không tạo thư mục mới; file skip đúng đích/kích thước; file mất/sửa và all-skipped; mutation lock/pause/resume snapshot; output lỗi/nhóm trống không tạo batch; hai process spawn tạo đồng thời chỉ có một ID; process thật giữ flock chặn worker/recover khác, kill rồi recover/resume lấy lại quyền. `test_web.py` thêm 409 cho import/move, GET vẫn 200.

Bước red: API batch chưa tồn tại và HTTP trả 400 thay vì 409. Sau implementation `.venv/bin/python -m unittest discover -s tests` → **49 test OK, exit 0**; `.venv/bin/python -m unittest discover -s tests/browser` → **4 test OK, exit 0**. Test locks là nhiều tiến trình thật, không mock. Crash harness đã bỏ Event.set trong finally sau terminate để không notify semaphore của process đã chết. Chưa nghiệm thu downloader/mạng/dung lượng disk khi tải thật; S09–S12 còn chờ. Không đánh dấu AC05–AC06 toàn luồng đạt chỉ từ fixture batch.

### S09 — đạt ở mức worker, 2026-09-10

- `.venv/bin/python -m unittest discover -s tests -v`: **60 test OK, exit 0**.
- `.venv/bin/python -m unittest discover -s tests/browser -v`: **4 test OK, exit 0**.
- 11 test downloader dùng SQLite/file thật và adapter giả lập: video lỗi không chặn batch, retry skip thành công, dừng giữ partial, progress, file mất tải lại, collision không overwrite, metadata sai không completed, filesystem lỗi paused kể cả item cuối, crash sau link không tạo file cuối thứ hai, lỗi cleanup không làm mất completed. Subprocess thật kiểm tra stop khi im lặng và giữ flock sau khi cha bị terminate.
- Bước red ban đầu thiếu downloader; test cleanup và disk-full item cuối sau đó tái hiện trạng thái sai trước khi sửa. Test crash sau publish dùng KeyboardInterrupt tại ranh giới publish/commit; không tuyên bố đã mô phỏng mọi sự cố mất điện.
- Smoke mạng: video công khai đầu tiên unavailable; mẫu nhạc lấy từ lịch sử local tải thành công. Full worker lưu **1.430.465 byte**, ffprobe xác nhận một stream **Opus/audio**, ffmpeg giải mã toàn file exit 0; batch tiếp theo **skipped=1, queued=0**. [Report local](../../../artifacts/download-smoke/t09-worker/validation.json) không chứa tiêu đề hoặc URL cá nhân.

Stop/retry/hết dung lượng được kiểm tra bằng lỗi có kiểm soát; chưa thử ngắt mạng thật giữa một video. S10–S12 và AC toàn luồng vẫn chưa nghiệm thu; UI tải chưa được bật.

### S10 — đạt mức điều khiển, 2026-09-10

Bước red: ba test API trả 404 trước triển khai; browser chờ #output-dir bị timeout trước khi thêm UI. `tests/test_download_controls.py` có 5 test: preview không tạo thư mục, snapshot đủ nhóm, create lặp, status phân trang, stop/edit/resume giữ snapshot, skip, CLI status/download/stop/resume chia sẻ DB, validation/Origin, lỗi launcher và worker subprocess thật báo lỗi filesystem, recover orphan. Browser thêm luồng lọc/tick một video nhưng tải hai → dừng → sửa nhóm → resume snapshot hai → partial/error → reload → retry → completed và nút không còn việc disabled.

- `.venv/bin/python -m unittest discover -s tests`: **65 test OK, exit 0**.
- `.venv/bin/python -m unittest discover -s tests/browser -v`: **5 test OK, exit 0**.
- CSS regression: cột tiêu đề bảng download 36px làm chữ xuống từng dòng; thêm kiểm tra width >150px trên desktop tái hiện fail trước override CSS.
- [Ảnh fixture](../../../artifacts/browser-runs/t10-download.png) không chứa lịch sử cá nhân. Audio trong browser là bytes fixture, không tuyên bố là file phát được; mẫu audio thật có bằng chứng riêng S09.

S11 tiếp tục nghiệm thu toàn luồng và quy mô dữ liệu; S12 quickstart môi trường sạch. Chưa đánh dấu AC toàn MVP đạt từ riêng S10.

### S11 — đạt 2026-09-10

[Báo cáo nghiệm thu AC01–AC08](ACCEPTANCE.md) là kết quả hiện hành; các đoạn S01–S10 ở trên ghi lịch sử từng mốc. Toàn bộ 66 test core/API và 6 browser đạt. Test browser mới kiểm tra 6.400 video/6.402 sự kiện, snapshot 255 sau sửa tay, một lỗi, restart server, resume, CLI reimport và chỉ tải lại 1 file mất/skip 254. Mẫu tải thật qua CLI hiện hành xác nhận Opus/audio-only, giải mã exit 0 và skip khi chạy lại. Coverage trace thu tiến trình chính + thread, không bao gồm subprocess/JS. S12 kiểm tra môi trường sạch tiếp theo.

### S12 — đạt 2026-09-10

[QUICKSTART.md](QUICKSTART.md) ghi lệnh và report. Package không editable được cài vào môi trường Python mới, không notebook/test; smoke thư viện chuẩn xác nhận CLI help/import, web assets, chuyển nhóm web→CLI và reimport. Một mẫu mạng hoàn tất Opus 1.430.465 byte, giải mã exit 0, lần sau skip. Sau thêm dependency test/browser, **66 test core/API + 6 test Chromium đạt** trên package đã cài. README bỏ trạng thái nút tải cũ, nêu điều kiện Linux/Node/SQLite, dữ liệu và khôi phục. Không phát hiện lỗi production mới; các giới hạn OS/accuracy và cảnh báo TestClient được giữ trong report.


### FE03 — mở rộng metadata đã duyệt, 2026-09-13

Collector chạy trên bản sao DB, đúng 52 ID được cho phép: 52 attempts/52 done/HTTP 200, 29,65 giây; log hợp nhất giữ observation của đủ 70 ID. Video rows không đổi. [Summary local](../../../artifacts/metadata-smoke/fe03-20260913T082334Z/summary.json).

Notebook 05 chạy lại đủ 4 cell code (8 cell tổng cộng) trên cohort cố định. **7 test nghiên cứu đạt**, bổ sung test trước code cho việc giữ ID/nhãn khi cập nhật metadata và giữ notes khi nhập CSV. Không có nhãn non_music độc lập nên metric vẫn được giữ trống; không tuyên bố accuracy. Không chạy lại runtime/browser vì không thay code ứng dụng.


### FE03 — gán nhãn và xuất kết quả trên trình duyệt, 2026-09-13

- `.venv/bin/python -m unittest discover -s tests/research -v`: **7 tests OK**, exit 0.
- `.venv/bin/python -m unittest discover -s tests/research_browser -v`: **2 tests OK**, exit 0; Chromium chạy ngoài sandbox. Bộ này tách khỏi unit nghiên cứu vì cần group browser và notebook.
- Notebook 05 thực thi thành công **4 cell code**; tạo review 70 video, 12 ca ưu tiên, giữ 5 nhãn có trước. Summary hash thêm template HTML. Không gọi thêm metadata/audio.

Bước red trước renderer: test fail vì thiếu trang có thể gán nhãn. Regression note nhập rồi reload trước blur tái hiện mất ghi chú; sau đổi listener input đạt. Browser round-trip CSV → pandas → merge_labels giữ Unicode, dấu phẩy/quote/newline, chỉ sửa đúng video; log ghi before/after/source hash/timestamp. Kiểm tra XSS qua tiêu đề, không có HTTP tự động, bản nháp bộ khác không bị lẫn; chặn localStorage vẫn xuất được nhãn unavailable/notes. Màn hình 390px không tràn ngang. Không chạy lại runtime/API vì lượt này chỉ đổi công cụ nghiên cứu và tài liệu.


### FE03 — CSV người dùng và phân tích lỗi (2026-09-18)

Notebook 05 nhập 18 nhãn hợp lệ, giữ 5 nhãn trước, tổng 23 nhãn/70 ID; không đổi classifier. Thêm bản sao nguyên byte input CSV, nhãn tích lũy, audit dự đoán theo video/quy tắc, lỗi FP/FN, so ngưỡng trên nhãn thật và metrics riêng 18 nhãn mới. Các số liệu và giới hạn tại [báo cáo](../../references/fe03-labelled-results.md).

`uv sync --locked --group notebook` khôi phục dependency notebook còn thiếu; notebook thực thi đủ 4 cell code qua nbclient. `.venv/bin/python -m unittest discover -s tests/research -v`: 7 tests OK, exit 0. Không đổi helper/HTML/runtime nên không chạy lại browser/API. Lint tài liệu đạt sau khi cache offline không còn và chuyển sang `npx --yes ai-devkit@latest lint`. Không có request metadata/audio mới.


### FE04 — preview (2026-09-18)

4 test mới fail trước implementation. Sau triển khai `.venv/bin/python -m unittest discover -s tests -v`: **86 tests OK**, exit 0 (TestClient ngoài sandbox). Bổ sung ca cùng ngày/uncertain rồi `.venv/bin/python -m unittest discover -s tests -p test_classification_preview.py -v`: **5 tests OK**, exit 0. Bao phủ CSV validation, source hash, metadata sai ID, manual conflict, guard, no mutation/overwrite và subprocess CLI. [Chi tiết](../implementation/CLASSIFICATION_PREVIEW.md). Không đổi web assets nên không chạy lại browser.

Kiểm chứng cuối cùng: `.venv/bin/python -m unittest discover -s tests -q` → **87 tests OK**, exit 0. Đối chiếu artifact xác nhận đủ 12 ca nhạc đã biết trong 5 trang đầu được đề xuất chuyển; live DB vẫn 260 Nhạc/6.125 Còn lại.


### FE04 — apply và live verification (2026-09-18)

Đã có classification-apply transaction/kiểm tra snapshot, giữ override và khóa batch. Test fail trước code (thiếu apply/CLI), sau code **90 tests OK**, exit 0, `.venv/bin/python -m unittest discover -s tests -q` ngoài sandbox cho TestClient. `node --check src/auralytica/static/app.js` đạt. Áp dụng thật 18 thay đổi sau backup, kết quả 278 music/6107 rest; đối chiếu mọi bảng download và sửa tay cũ không thay đổi. [Chi tiết và artifact](../implementation/CLASSIFICATION_PREVIEW.md#áp-dụng-đã-triển-khai-và-chạy-thành-công). Không chạy lại Chromium; UI chỉ thêm hai tên lý do.
