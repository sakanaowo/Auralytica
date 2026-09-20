---
phase: implementation
title: Auralytica — Trạng thái triển khai
description: Kết quả T01–T12, CLI/web local, tải audio và giới hạn kiểm chứng
---

# Auralytica — Implementation

> Tài liệu này giữ lịch sử MVP/CLI cũ. Entry point hiện hành là launcher web-only `auralytica`; xem [implementation web workflow](2026-09-20-feature-web-workflow.md). Các subcommand nghiệp vụ trong các mốc lịch sử bên dưới không còn khả dụng.

Cập nhật 2026-09-11: **T01–T12 hoàn tất; FE02 collector/cache/audit đã triển khai**. [Metadata hiện hành](METADATA.md) mô tả schema v2, CLI và giới hạn. [Quickstart sạch](../testing/QUICKSTART.md) và [nghiệm thu chức năng](../testing/ACCEPTANCE.md) ghi bằng chứng MVP trước FE02; các mục T01–T12 dưới đây là lịch sử từng bước.

## Development Setup

Python >= 3.11 có sqlite3, uv và lockfile hiện có. Test dùng unittest chuẩn Python; chưa cần dependency ngoài cho T01. Notebook giữ group riêng trong pyproject.toml. FastAPI/yt-dlp được thêm ở task sử dụng.

```sh
uv sync --locked --no-default-groups --group test
uv run --no-sync auralytica --help
uv run --no-sync python -m unittest discover -s tests -v
```

Xem [README](../../../README.md) để kiểm tra trong môi trường riêng và giữ .venv notebook.

## Code Structure

- `src/auralytica/__init__.py`: entry point hiện có, dùng argparse hiển thị help và từ chối đối số không hợp lệ.
- `tests/test_cli.py`: chạy console script đã cài qua subprocess.
- `tests/test_runtime.py`: SQLite thật trong thư mục tạm, kiểm tra commit Unicode, rollback và mở lại file.
- `pyproject.toml`, `uv.lock`: sử dụng cấu hình/lockfile sẵn có; T01 không cần thêm dependency.

- `src/auralytica/storage.py`: schema v1, mở/migrate DB, transaction và repository video/settings.
- `tests/test_storage.py`: 10 test persistence và ràng buộc trên SQLite thật.

## Implementation Notes

**T02:** 7 bảng imports, watch_events, videos, channel_decisions, download_batches, download_items, settings. `PRAGMA user_version` giữ phiên bản schema. Khóa `BEGIN IMMEDIATE` bao trọn đọc phiên bản và migration; từng câu DDL nằm trong transaction để lỗi không để lại schema dở. Version mới hơn bị từ chối, không tự hạ cấp. V1 là schema ứng dụng đầu tiên, không tự chuyển database notebook.

`open_database(path)` tạo thư mục cha và trả connection có foreign_keys, row_factory; caller đóng connection, mỗi thread/request dùng connection riêng. Statement riêng autocommit; mutation nhiều bước phải dùng `transaction(db)`. Không hỗ trợ transaction lồng nhau. `get_video` trả effective_group theo manual override; `set_video_group(..., None)` reset về tự động. Settings là key/value; active import dùng ID dạng chuỗi, validation nghiệp vụ sẽ ở importer.

Repository hiện cung cấp thao tác video/settings; importer và batch service sẽ bổ sung thao tác nghiệp vụ theo T03/T08, dùng cùng connection/transaction. Không có worker lock hoặc kiểm tra file completed ở T02.

Kiểm chứng mới: `.venv/bin/python -m unittest discover -s tests -v` → 14 test OK, exit 0. S02 chi tiết trong testing.


Ba test CLI fail với hành vi cũ in lời chào, sau thay đổi cả 4 test đạt. SQLite runtime hiện hoạt động: Python 3.11.16, SQLite 3.53.1. Không tái hiện lỗi SQLite trước đây nên không nhận đã sửa lỗi đó.

Môi trường mới /tmp/auralytica-t01-clean được tạo bằng uv sync --locked --no-default-groups, chỉ cài auralytica 0.1.0; cả 4 test và help đều exit 0. Bằng chứng chi tiết ở [testing](../testing/README.md).

Triển khai tiếp trong workspace hiện hành trên master, không đổi branch hoặc ghi đè thay đổi notebook/requirements của người dùng. Chưa tạo commit. Tiến độ lưu bằng tài liệu local; phiên này không có task tracing được lifecycle thiết lập.

## Integration Points

Console entry point giữ auralytica:main. Đã có schema thư viện và API local; chưa có giao diện hai bảng hoặc downloader; CLI không quảng cáo các subcommand chưa triển khai.

## Error Handling

Đối số không hợp lệ trả exit 2 và thông báo argparse. Help hoặc không truyền đối số trả exit 0. SQLite thiếu module là vấn đề interpreter, không giải quyết bằng cài package sqlite3 từ pip.

## Performance Considerations

T01 chỉ kiểm tra nền tảng; chưa đo import 6.400 video hoặc hiệu năng tải. Môi trường kiểm chứng riêng không cài pandas/Jupyter.

## Security Notes

T01 không đọc Takeout, tạo server hoặc tải mạng trong runtime. Test database nằm trong thư mục tạm và được dọn sau test. Các kiểm tra Host/Origin, upload và đường dẫn thuộc T06–T09, chưa triển khai.

### T03 — importer và CLI (2026-09-09)

`src/auralytica/importer.py` tìm watch-history.json, hỗ trợ --history khi nhiều nguồn, JSON UTF-8/BOM, music library songs.csv trong subtree export. Xác thực host/ID video, chuẩn hóa giờ UTC, giữ event theo dòng nguồn. Bỏ ads có marker From Google Ads và dòng không phải object; bản ghi không có video vẫn lưu event với video_id NULL. Thống kê rõ các nhóm này. Title hỗ trợ bỏ tiền tố Watched/Đã xem.

Hash chỉ nội dung history: nhập lại không tạo event mới; library được đối chiếu lại, ghi metadata music_library cho video trong nguồn đang xem. Chưa đưa video sang nhóm music. Import metadata không ghi đè user_group hoặc trạng thái tải. Parse và kiểm tra library trước transaction; lưu import/video/events/active_import trong một transaction. Một active import, không cộng chồng các export.

CLI `auralytica import <folder> [--history <relative-path>] [--database <path>]` trả JSON thống kê, lỗi input/SQLite trả exit 2. Database mặc định ~/.local/share/auralytica/library.sqlite3; --database dùng chung được với core sau này. Chưa có worker nên khóa import trong batch chạy thuộc T08. Giao diện chọn folder/upload thuộc T06–T07.

Kiểm chứng: 22 test đạt, smoke local và đối chiếu từng ID/count với notebook đạt; xem S03. Chưa hỗ trợ HTML hoặc ngôn ngữ tiền tố title ngoài hai dạng đã nêu. Mọi thay đổi ngày này ở workspace hiện hành, không commit và không sửa export/notebook.

### T04 — phân loại có giải thích (2026-09-10)

`classification.py`: suggest trả group/reason/evidence (code, source), classify_import cập nhật auto_group/auto_reason/evidence_json cho ID thuộc import, classify_active bọc transaction. Không ghi user_group. Import gọi phân loại trong cùng transaction; CLI classify chạy lại trên active import. Bộ quy tắc rules-v1 là heuristic, không phải model hay phép đo độ chính xác.

Thứ tự: URL Shorts rõ ràng → nhãn kênh local đã lưu → xung đột nhạc/nói chuyện → Topic/library → music hint → unknown. Override video ưu tiên hơn mọi gợi ý. Tiêu đề podcast/interview/gameplay chỉ tạo talk_context để duyệt, không phải xác nhận loại tuyệt đối. Lượt lặp >=3, VEVO và từ khóa chỉ là bằng chứng phụ. Không dùng category Entertainment/duration/hashtag làm loại trừ độc lập. Regex đa ngôn ngữ còn hạn chế; thiếu match giữ unknown.

Importer thêm metadata takeout_shorts_url từ URL /shorts/ hợp lệ; gom OR trong một export kể cả video cũng có watch URL. Database nhập trước T04 cần reimport nguồn để bổ sung dấu hiệu này. Music library và Shorts evidence được làm mới theo nguồn nhập; các trường metadata khác giữ nguyên. Không có blacklist kênh cài sẵn; classifier chỉ đọc channel_decisions đã lưu, giao diện quản lý nhãn sẽ ở phần review.

Kiểm chứng: `.venv/bin/python -m unittest discover -s tests` → 26 test OK, exit 0. Import và classify cùng database local đều cho 255 music / 6.130 rest; chưa tải audio. API list/move và giao diện còn chờ T05–T07.

### T05 — review service và CLI (2026-09-10)

`review.py` cung cấp list_videos/move_videos dùng chung cho CLI và API sắp tới. Chỉ xét active import; watch_count tính theo event trong nguồn đó. Mỗi dòng có group hiệu lực, decision_source, reason (manual nếu sửa tay), evidence, link, thumbnail nếu có và download_status gần nhất theo batch ID. Status này là bản ghi tải, không khẳng định file còn hợp lệ (T09 kiểm tra file).

List đọc tập active từ SQLite, lọc/sort trong Python để casefold Unicode và tìm chuỗi literal; trả tối đa page_size 1–1000, mặc định 50, sort watch_count giảm dần/title/channel tăng dần và ID làm tie-break. group_totals không phụ thuộc filter; filtered_count trước phân trang. Chọn cách đơn giản cho quy mô ~6.400 video; chưa tối ưu lịch sử rất lớn hoặc nhiều download records.

Move xác thực toàn bộ 1–1000 ID thuộc active import trong BEGIN IMMEDIATE, deduplicate ID rồi lưu user_group. Nếu bất kỳ ID sai, rollback toàn bộ; không xóa file hoặc sửa bản ghi download. Giá trị moved là số ID duy nhất đã áp dụng override, kể cả vốn đã ở nhóm đích. Group count trả về trong cùng transaction. CLI list/move trả JSON và lỗi nghiệp vụ exit 2.

Kiểm chứng: `.venv/bin/python -m unittest discover -s tests` → 32 test OK, exit 0. Read-only smoke 6.385 video trả đúng tổng 255 music / 6.130 rest, hai trang 50 dòng trong 0,086 giây trên máy hiện tại. Không thử sửa nhãn cá nhân trong smoke. API/browser và batch lock chưa triển khai.

### T06 — API local (2026-09-10)

`web.py` cung cấp create_app(database, port=8765), GET /api/videos, POST /api/videos/move và POST /api/imports; root hiện trả JSON trạng thái. CLI serve dùng Uvicorn host=127.0.0.1, không nhận --host; proxy_headers/access_log tắt. Giao diện/browser auto-open để T07.

Dependencies theo lockfile: FastAPI 0.141.1, Uvicorn 0.52.4, python-multipart 0.0.32; HTTP client httpx ở group test, group notebook giữ nguyên. Cài test bằng uv sync --locked --group test; thêm --group notebook nếu cần giữ notebook trong cùng .venv.

Middleware ASGI kiểm tra Host khớp localhost/127.0.0.1 + port, Origin trùng chính xác trên mọi mutation; không có Origin bị từ chối POST. Không mở CORS. Kiểm tra Content-Length và đếm bytes thực trước parse (gồm request không khai báo length), giới hạn tổng 64 MiB. MVP buffer body trong RAM trước multipart; chưa tối ưu upload khổng lồ/nhiều request đồng thời. Response có nosniff/no-store; dữ liệu title/kênh là JSON, rendering HTML an toàn thuộc T07.

Upload multipart chỉ có trường files: đúng một watch-history.json, library tùy chọn, tối đa hai file. Từ chối nguồn trùng, file khác/HTML và đường dẫn traversal. Tên relative dùng để nhận dạng basename; backend chỉ ghi hai tên cố định trong TemporaryDirectory rồi gọi importer; dọn thư mục sau request. Frontend phải chọn đúng nguồn/library cùng export trước gửi, không upload toàn bộ Takeout. Import chạy thread pool; DB connection mở/đóng trong cùng worker. Lỗi nghiệp vụ 400, validation 422, Origin 403, quá cỡ 413, SQLite 503, filesystem 500 với thông báo không chứa dữ liệu lịch sử.

Kiểm chứng: 40 test đạt và smoke real HTTP với fixture tổng hợp. TestClient treo cả app FastAPI tối giản trong sandbox; chạy ngoài sandbox đạt. Starlette phát cảnh báo deprecation httpx trong test (gợi ý httpx2), không có test fail; chưa đổi client sang thư viện khác trong T06.

Tham khảo chính thức: [FastAPI upload](https://fastapi.tiangolo.com/tutorial/request-files/), [TestClient](https://fastapi.tiangolo.com/reference/testclient/), [Uvicorn settings](https://uvicorn.dev/settings/).

### T07 — giao diện duyệt (2026-09-10)

`static/index.html`, `style.css`, `app.js` được serve ở root/static và đóng gói cùng wheel. DOM tạo bằng createElement/textContent, không dùng innerHTML cho dữ liệu người dùng. Link chỉ tạo từ video ID; thumbnail lazy-load từ i.ytimg.com có referrer-policy no-referrer và fallback khi lỗi. Desktop hai bảng, màn hình hẹp xếp dọc.

UI mỗi nhóm có search Unicode, reason/sort, phân trang 50 dòng, tổng nhóm/filtered count riêng và checkbox trang hiện tại. Mỗi request list có revision để bỏ response cũ; lúc đổi filter/page xóa selection và khóa thao tác trên dữ liệu đang tải. Mutation khóa các nút chuyển/import; sau server xác nhận refresh cả hai nhóm. Chuyển hết trang cuối tự về trang cuối hợp lệ. Reload đọc lại từ DB.

Folder picker dùng webkitdirectory; drop capture entry handles ngay trong event rồi đọc mọi batch readEntries đến rỗng. Chỉ đọc nội dung history/library cần thiết; nhiều nguồn hiện dialog, library được giới hạn subtree lịch sử. Chặn file >63 MiB phía UI để chừa multipart overhead cho giới hạn server 64 MiB. JSON lỗi giữ thư viện cũ và hiện thông báo. Nút tải là disabled placeholder có nhãn Sắp có, không giả lập tải. serve hiện yêu cầu mở URL thủ công; không tự mở browser trong headless.

Kiểm chứng: 41 core/API và 4 Chromium test đạt; native directory drop qua CDP, folder picker, multi-source, error, XSS fixture, ảnh lỗi, bulk/reload/filter/page, 6.400 video và viewport 390px không overflow. Một smoke import/filter/move 1,39s, không có pageerror. Snapshot local ở artifacts/browser-runs/t07-ui.png đã xem. uv build --wheel đạt, kiểm tra zip có cả ba assets. Tham khảo [Playwright input](https://playwright.dev/python/docs/input) và [MDN directory reader](https://developer.mozilla.org/en-US/docs/Web/API/FileSystemDirectoryReader/readEntries).

### T08 — batch snapshot và quyền worker (2026-09-10)

`batches.py` cung cấp create_batch/get_batch/pause_batch/resume_batch/recover_batch/worker_session. Dùng schema v1 hiện có, không migration mới. create_batch giữ BEGIN IMMEDIATE, lấy mọi ID có effective_group music trong active import, không nhận checkbox/filter/page. Nếu đã queued/running trả cùng batch trước cả kiểm tra output mới. Output resolve, mkdir và thử ghi tempfile; snapshot rỗng báo lỗi. Mỗi item queued hoặc skipped; toàn bộ skipped đánh dấu batch completed và không khóa review.

Skip chỉ khi bản ghi completed/skipped cùng video ID, batch output giống đường dẫn đích resolve, file regular ở trực tiếp thư mục đó và kích thước dương khớp DB. File mất/đổi kích thước/khác thư mục không skip. Đây không phải kiểm tra checksum; worker T09 phải kiểm tra lại trước khi bỏ qua vì file có thể thay đổi sau tạo batch.

`storage.BatchBusyError` và assert_review_unlocked dùng trong transaction của importer/review/classify; API map lỗi sang 409, CLI vẫn exit 2. List không bị khóa. Các helper SQL cấp thấp không thay thế service guard. Khóa review cả queued/running; dừng queued bằng pause_batch. Running phải yêu cầu worker dừng (điều khiển thuộc T09/T10), không giả vờ pause trong khi process còn tải.

Worker giữ flock độc quyền không blocking trên <database-resolved-path>.worker.lock suốt context, dùng một DB connection của worker. Không unlink lockfile để các tiến trình luôn khóa cùng inode. Khóa file lấy trước transaction khi claim/resume/recover. Chỉ queued được claim; context exit còn running thì reset running items về queued và batch paused. Worker T09 có thể hoàn tất batch trước exit. OS thả lock khi process chết; recover_batch thử lấy lock trước rồi đổi running thành paused, không tự chạy. Resume giữ nguyên item IDs/output snapshot, reset phần chưa hoàn tất, kiểm tra lại file completed/skipped. Batch khác active thì từ chối resume.

Phạm vi Linux local, flock advisory và DB trên đĩa; chưa hỗ trợ Windows hoặc alias database qua hardlink. Không có downloader hoặc API/nút tạo batch ở bước này. T09 dùng worker_session để chạy yt-dlp; T10 nối controls.

Kiểm chứng: 49 test core/API + 4 browser đạt. Test crash ban đầu treo ở cleanup multiprocessing.Event.set sau khi process đợi event bị kill; traceback xác định nằm trong harness, bỏ notify tiến trình đã chết. Fixture review cũ có completed item nhưng batch queued được sửa batch completed cho đúng nghiệp vụ mới.

### T09 — worker audio (2026-09-10)

`downloader.run_batch` chạy snapshot tuần tự với connection riêng, dưới `worker_session`. `YtDlpAdapter` chạy subprocess `_ytdlp` và nhận JSON progress/result/error. Child kế thừa file descriptor flock: khi cha chết, recover không được nhận việc cho đến khi child thoát. Stop được lưu trong settings, adapter kiểm tra mỗi 0,2 giây kể cả child không phát progress; gửi TERM rồi KILL nếu cần. Resume xóa stop request và giữ snapshot.

yt-dlp chọn `bestaudio`, không postprocess/chuyển mã; có Node.js runtime và retries hữu hạn cho request/fragment. File dở ở `<output>/.auralytica/batch-ID/video-ID/`; kiểm tra ID, codec audio-only và file dương trước publish. Tên sạch chứa ID; hardlink tạo file cuối không overwrite, thêm số nếu trùng. Lưu planned path trước link để khôi phục sau crash bằng inode. Lỗi dọn staging không đổi trạng thái completed. Skip kiểm tra lại file cùng đích và kích thước; chưa dùng checksum.

Lỗi video ghi failed rồi tiếp tục; lỗi filesystem dừng paused, giữ kết quả thành công. Output preflight lỗi trả DownloadFailure cho caller và context đưa batch về paused. Core request_stop có sẵn; T10 mới công bố API/CLI và bật UI. Schema vẫn v1. Dependency `yt-dlp[default]` được khóa trong uv.lock. Tham khảo [tài liệu yt-dlp](https://github.com/yt-dlp/yt-dlp#usage-and-options).

Kiểm chứng S09: 60 test core/API, 4 browser; một mẫu thật Opus 1.430.465 byte giải mã exit 0, batch tiếp theo skip. Không suy ra mọi video đều tải được từ mẫu này.

### T10 — điều khiển CLI/web (2026-09-10)

`download_controls.py` gom preview chỉ đọc, status phân trang, danh sách 50 lượt gần đây ưu tiên active, start/stop/resume. `worker.py` chạy qua subprocess detached, connection riêng; launcher có thread daemon để reap child khi parent còn sống. CLI trả snapshot ngay, status là nguồn kết quả cuối. Đóng tab/server không dừng worker. Lỗi launch/preflight được lưu trong settings theo batch ID và hiển thị; resume xóa lỗi cũ. Stop thử recover bằng flock trước, worker còn sống thì gửi stop flag.

`web.py` công bố routes /api/downloads, /preview, /{id}, /{id}/stop và /resume; kiểm tra output, phân trang, extra fields và Origin. UI nhập đường dẫn trên máy, lưu lựa chọn thư mục trong localStorage, polling mỗi giây, hiển thị tiến độ byte nếu có và lỗi từng video, 20 item/trang. Bảng gần đây cho chọn snapshot cũ; CLI theo ID truy cập cả lượt ngoài 50 gần đây. Khi active khóa import/move/output/start nhưng giữ search/filter/page. Dừng xong được sửa nhóm; resume giữ snapshot/output cũ.

65 test core/API + 5 browser đạt. Browser dùng server/SQLite/worker thật với adapter audio giả lập, kiểm chứng filter/tick không thu hẹp tải và stop/edit/resume/error/reload/retry. CSS cột tiêu đề bảng tiến độ từng bị áp width checkbox 36px; test tái hiện rồi override độ rộng riêng bảng tải. Không đổi schema. T11 chưa nghiệm thu mọi AC hoặc mạng gián đoạn thật.

### T11 — hoàn tất 2026-09-10

[Báo cáo AC01–AC08](../testing/ACCEPTANCE.md) ghi bằng chứng và giới hạn Linux/JSON. Thêm browser E2E 6.400 video với restart server, CLI reimport, file mất tải lại; thêm protocol error test downloader và hai công cụ kiểm chứng thủ công (trace core, smoke một video mạng). 66 core/API + 6 browser đạt; mẫu thật Opus giải mã được, lần sau skip. Không đổi code production/schema; chưa đo accuracy hoặc tải mọi nhạc cá nhân. T12 tiếp theo để kiểm tra quickstart sạch; M4 còn mở.

### T12 — hoàn tất 2026-09-10

Không thay runtime/schema. Bổ sung `tests/manual/quickstart.py` dùng thư viện chuẩn để kiểm tra package cài riêng, CLI/server/static/review/reimport; README viết lại theo luồng dùng và khôi phục. Môi trường mới không editable nạp code từ site-packages, đủ HTML/CSS/JS. 25 package runtime; không notebook/test trước smoke. Mẫu thật Opus giải mã được; sau cài dependency test, 66 core/API + 6 browser đạt. Tất cả task MVP hoàn tất; xem QUICKSTART cho giới hạn môi trường OS dùng chung.


### FE03 — giao diện gán nhãn nghiên cứu (2026-09-13)

Notebook 05 gọi `notebooks/residual_study.py::render_review` với cohort đã sắp 12 ca ưu tiên lên đầu. `notebooks/review_template.html` tạo trang độc lập có chọn nhãn/notes, tiến độ, localStorage theo hash toàn bộ review đầu vào, xuất CSV chỉ dòng đã sửa và log JSONL trước/sau/thời gian/source hash. Ghi chú lưu ngay khi nhập, kể cả reload khi chưa rời ô. Khi storage lỗi vẫn có thể xuất dữ liệu trong bộ nhớ. JSON nhúng escape HTML delimiter; văn bản render bằng textContent, URL chỉ dựng từ ID YouTube, không tự gọi mạng. Template được thêm vào inputs_sha256 của summary.

Nhãn/log được tải về qua browser, không tự ghi DB hay sửa classifier. CSV đi qua validation `merge_labels` hiện có; ca thiếu nhãn không tự thành non_music. Đây là công cụ hoàn thành phần gán nhãn FE03, không phải FE04. Task tracing chưa được lifecycle thiết lập; tiến độ/bằng chứng giữ trong planning/testing/dashboard.

Kiểm chứng: 7 unit nghiên cứu, 2 Chromium (desktop/mobile), notebook 4 cell code đạt; test notes reload đã tái hiện fail trước khi chuyển listener từ change sang input. [Hướng dẫn review](../../references/residual-evaluation.md).


### FE03 — CSV người dùng và phân tích lỗi (2026-09-18)

Notebook 05 nhập 18 nhãn hợp lệ, giữ 5 nhãn trước, tổng 23 nhãn/70 ID; không đổi classifier. Thêm bản sao nguyên byte input CSV, nhãn tích lũy, audit dự đoán theo video/quy tắc, lỗi FP/FN, so ngưỡng trên nhãn thật và metrics riêng 18 nhãn mới. Các số liệu và giới hạn tại [báo cáo](../../references/fe03-labelled-results.md).

`uv sync --locked --group notebook` khôi phục dependency notebook còn thiếu; notebook thực thi đủ 4 cell code qua nbclient. `.venv/bin/python -m unittest discover -s tests/research -v`: 7 tests OK, exit 0. Không đổi helper/HTML/runtime nên không chạy lại browser/API. Lint tài liệu đạt sau khi cache offline không còn và chuyển sang `npx --yes ai-devkit@latest lint`. Không có request metadata/audio mới.


### FE04 — preview (2026-09-18)

[Classification preview](CLASSIFICATION_PREVIEW.md) mô tả CLI mới, validation, thứ tự giữ sửa tay/nhãn/metadata và giới hạn. `classification_preview.py` đọc DB và các artifact có sẵn, `__init__.py` thêm nhánh CLI read-only trước nhánh mở/migrate DB thường. Không đổi classify/import/web hoặc schema. Preview thật: 18 chuyển nhóm đề xuất, 0 xung đột. Apply còn chờ, không cần gán nhãn reel thêm để làm bước tích hợp tiếp.


### FE04 — apply và live verification (2026-09-18)

Đã có classification-apply transaction/kiểm tra snapshot, giữ override và khóa batch. Test fail trước code (thiếu apply/CLI), sau code **90 tests OK**, exit 0, `.venv/bin/python -m unittest discover -s tests -q` ngoài sandbox cho TestClient. `node --check src/auralytica/static/app.js` đạt. Áp dụng thật 18 thay đổi sau backup, kết quả 278 music/6107 rest; đối chiếu mọi bảng download và sửa tay cũ không thay đổi. [Chi tiết và artifact](../implementation/CLASSIFICATION_PREVIEW.md#áp-dụng-đã-triển-khai-và-chạy-thành-công). Không chạy lại Chromium; UI chỉ thêm hai tên lý do.
