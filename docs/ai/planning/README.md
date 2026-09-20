---
phase: planning
title: Auralytica — Kế hoạch triển khai MVP
description: Task, phụ thuộc và bằng chứng nghiệm thu cho import, hai danh sách và tải audio
---

# Auralytica — Kế hoạch triển khai

Cập nhật: **2026-09-10**. **T01–T12 hoàn tất**. MVP Linux/JSON đã có nghiệm thu chức năng và quickstart trên môi trường Python sạch.

Nguồn: [Requirements](../requirements/README.md) · [Thiết kế](../design/README.md) · [Kịch bản kiểm chứng](../testing/README.md) · [Dashboard](../../../PROJECT_DASHBOARD.md).

## Milestones

- [x] **M1 — Import dùng được:** runtime SQLite, lưu trạng thái và CLI đọc folder Takeout (T01–T03).
- [x] **M2 — Duyệt dùng được:** gợi ý và web hai danh sách, chuyển từng dòng/hàng loạt, lưu sau reload (T04–T07).
- [x] **M3 — Tải dùng được:** một nút tải toàn bộ bên nhạc, tiến độ và khôi phục (T08–T10).
- [x] **M4 — Nghiệm thu MVP:** kiểm chứng AC01–AC08, tài liệu chạy thực tế (T11–T12).

## Task Breakdown

Trạng thái: **T01–T12 hoàn tất**. [Bằng chứng S01–S02](../testing/README.md): 14 test đạt; 10 test storage dùng SQLite thật. Các cột kiểm chứng của task còn lại là yêu cầu tương lai.

| ID | Kết quả cần triển khai | Phụ thuộc | Requirements | Kiểm chứng / điều kiện hoàn thành |
| --- | --- | --- | --- | --- |
| T01 | Kiểm tra Python đang chạy, sqlite3 import và transaction; thiết lập dependency ứng dụng/test tách khỏi notebook, CLI help. Nếu tái hiện lỗi SQLite thì sửa đúng runtime và ghi nguyên nhân. | — | R01, R11, R12 | S01: môi trường sạch chạy được CLI và transaction; ghi phiên bản/runtime, không tuyên bố lỗi cũ đã sửa nếu chưa tái hiện. |
| T02 | Schema SQLite có migration, Import/WatchEvent/Video/ChannelDecision/Batch/Item/Settings; repository và transaction dùng chung. | T01 | R01, R03, R11 | S02: tạo/mở lại DB, uniqueness, rollback, migration giữ dữ liệu, lưu sửa tay và kết quả tải. |
| T03 | CLI import folder JSON Unicode, phát hiện nguồn, báo thiếu/nhiều nguồn/HTML; chuẩn hóa video ID và sự kiện, hash nhập lại, active import, library tùy chọn. | T02 | R02, R03, R04, R11 | S03: fixture có kết quả đếm biết trước, nhập lại không nhân đôi, lỗi giữ import cũ, library không thêm ID ngoài lịch sử; đối chiếu thống kê export local. |
| T04 | Bộ gợi ý có lý do/nguồn: Topic/library, bằng chứng loại trừ, ca chưa rõ; override cấp video và nhãn kênh local. Tín hiệu yếu chỉ hỗ trợ. | T03 | R04, R05, R06 | S04: bảng ca nhạc/không nhạc/chưa rõ, xung đột và chạy lại; không dùng hashtag/duration hay category Entertainment làm loại trừ tuyệt đối. |
| T05 | Review service và CLI list/move: hai nhóm hiệu lực, tìm/lọc/sort/page, tổng mỗi nhóm, chuyển hàng loạt có transaction. | T04 | R01, R06, R07, R11 | S05: mỗi ID đúng một bên, chuyển/reload và tổng đúng, request lỗi không chuyển một phần, không xóa audio khi đổi nhóm. |
| T06 | Web server loopback dùng chung core; import upload các file cần thiết, API list/move, kiểm tra input/Host/Origin, giới hạn upload/page. | T05 | R01, R02, R07, R12 | S06: CLI/web thấy cùng trạng thái, folder lỗi/nhiều nguồn có phản hồi rõ, request ngoài origin bị chặn, dữ liệu tiêu đề được escape. |
| T07 | Giao diện hai danh sách cạnh nhau, kéo thả/chọn folder, thumbnail/link/lượt xem/lý do; nút chuyển từng dòng/hàng loạt, bộ lọc, trạng thái rỗng/lỗi. | T06 | R02, R07, R08 | S07: thao tác browser thực, reload giữ sửa tay; checkbox chỉ chuyển và được xóa khi đổi trang/lọc; ảnh lỗi không chặn duyệt. |
| T08 | Batch service và khóa worker liên tiến trình: snapshot toàn bộ music, output path, skip file hợp lệ, chống nhấp lặp và xung đột CLI/web. | T05 | R08, R10, R11 | S08: mục ẩn vẫn vào batch, rest không vào; hai tiến trình không tạo hai worker; khóa mutation khi chạy và resume giữ snapshot. |
| T09 | Adapter yt-dlp tải audio tốt nhất giữ codec, tên chứa ID không ghi đè file khác; worker tuần tự, tiến độ/lỗi, stop/resume, kiểm tra file hoàn tất. | T08 | R09, R10, R11, R12 | S09: adapter giả lập lỗi/mạng/disk, restart; smoke tải audio thật đúng ID, kiểm tra codec và phát được; partial không được báo completed. |
| T10 | Nối nút Tải toàn bộ, số cần tải/tổng nhạc, output path, polling, lỗi từng video, stop/resume với CLI download/status/stop/resume. | T07, T09 | R01, R08, R09, R10, R11 | S10: một lần bấm chạy cả batch, không phụ thuộc tick/lọc/page; nút không khả dụng khi không có việc; dừng/sửa/tạo mới và tiếp tục snapshot cũ đúng thiết kế. |
| T11 | Nghiệm thu E2E: import → hai bảng → tải → restart; đo UI trên khoảng 6.400 video; đối chiếu AC và ghi hạn chế. | T10 | R01, R02, R03, R04, R05, R06, R07, R08, R09, R10, R11, R12 | S11: báo cáo AC01–AC08 kèm lệnh/log và thao tác browser; fake downloader cho luồng toàn bộ, mẫu tải thật nhỏ cho codec/phát audio. |
| T12 | Hướng dẫn cài/chạy/import/duyệt/tải/khôi phục, cập nhật implementation, testing và dashboard bằng bằng chứng thực tế. | T11 | R01, R02, R10, R12 | S12: chạy lại quickstart trong môi trường sạch; ghi lỗi còn mở, không đánh dấu đạt tiêu chí chưa kiểm chứng. |

## Dependencies

Thứ tự thực hiện mặc định: **T01 → T02 → T03 → T04 → T05 → T06 → T07 → T08 → T09 → T10 → T11 → T12**. T08 chỉ phụ thuộc T05 về kỹ thuật; ưu tiên hoàn thiện màn hình duyệt trước để sớm kiểm tra dữ liệu thực.

Không còn task MVP chưa hoàn thành. Các cải tiến phân loại hoặc dashboard phân tích cần phạm vi mới dựa trên sử dụng thực tế.

### Feature engineering / YouTube Music — cập nhật 2026-09-11

Phạm vi đang nghiên cứu: dùng metadata YouTube Music theo đúng ID lịch sử trước, sau đó xử lý residual; mọi quyết định phải truy được nguồn và sửa tay. [Báo cáo pilot](../../references/youtube-music-identification.md) là bằng chứng và giới hạn; chưa có classifier mới.

| Bước | Trạng thái | Kết quả / phụ thuộc / kiểm chứng |
| --- | --- | --- |
| FE01 — pilot và phân tích | Hoàn tất trong mẫu đã duyệt | 18 ID cố định, 36 observations/37 HTTP request; notebook 04 chạy đủ 12 cell, xuất audit/review/latency. R03–R06, R12; so nguồn player/queue, giữ nhãn thật tách proxy, không sửa DB. |
| FE02 — collector/cache/audit | Đã triển khai và kiểm chứng | Schema v2, collector/CLI, cache theo provider/version, retry/resume, audit decision/review và xuất JSONL. Smoke 18 ID trên bản sao DB: lần hai 0 network calls, 18 cache hits, video rows không đổi. [Chi tiết](../implementation/METADATA.md). Liên quan R05/R06/R11/R12, S02/S04. |
| FE03 — đánh giá residual | Đã đánh giá 23 nhãn; còn thiếu đối chứng | CSV mới 16 music + 2 non_music; tổng 21 music + 2 non_music, còn 47/70. Metadata mạnh + UGC recurrence tìm 20/21, 0/2 nhận nhầm; nhánh kết hợp nội dung nhận nhầm 2 reel. Cần phân biệt Tutorial/performance và kiểm chứng Shorts/podcast/BGM; chưa chốt ngưỡng. [Kết quả](../../references/fe03-labelled-results.md). |
| FE04 — nối gợi ý và lý do vào CLI/web | Đã có CLI preview/apply; đã cập nhật live DB | Đã áp dụng 18 thay đổi, 0 xung đột; live 278/6107. Preview read-only; apply kiểm tra snapshot/batch và audit, giữ sửa tay. Chưa có nút preview/apply trên web hoặc mở rộng metadata. [Chi tiết](../implementation/CLASSIFICATION_PREVIEW.md).  Sau FE02/FE03: giữ hai bảng và snapshot tải, hiển thị lý do/nguồn và ghi review. R01/R06–R08/R11, S04–S08/S11: override, lỗi mạng không thành non-music, khóa khi batch chạy, không thêm ID ngoài lịch sử. |

T01–T12 vẫn hoàn tất về chức năng. FE01/FE02 chứng minh thu thập và truy vết tín hiệu, không chứng minh accuracy trên toàn lịch sử. Ưu tiên tiếp theo là bộ phản ví dụ và đánh giá residual FE03, rồi FE04; metadata đã có cho 70 ID được duyệt; chưa quét toàn lịch sử hoặc triển khai model audio. T13–T16 từng trao đổi không được tự đánh dấu hoàn tất từ các bước này.

Các kịch bản S01–S12 được mô tả trong testing; mỗi kịch bản có task cùng số chịu trách nhiệm. Test hành vi được viết cùng task, không dồn toàn bộ đến T11.

## Timeline & Estimates

Chưa chốt ngày hoặc số giờ: runtime SQLite, hình dạng export thực và downloader chưa được kiểm chứng trong ứng dụng. Ước lượng lại sau M1, dựa trên kết quả thực tế. M2 có thể nghiệm thu duyệt offline trước khi tải mạng; M3 cần smoke tải thật.

## Risks & Mitigation

| Rủi ro | Task xử lý |
| --- | --- |
| Python thiếu module SQLite hoặc dùng nhầm interpreter | T01 kiểm tra đúng executable, transaction và ghi cách tái lập môi trường. |
| Folder browser không có đường dẫn native; nhiều file lịch sử | T03/T06/T07 đọc cây folder, gửi file cần thiết đến localhost, chọn nguồn rõ ràng. |
| Rule notebook loại nhầm hashtag hoặc nhạc không có từ khóa | T04 giữ nguồn bằng chứng, override; không sao chép blacklist cá nhân thành mặc định chung. |
| Request đồng thời hoặc chết tiến trình tạo tải trùng | T08/T09 kiểm thử bằng nhiều tiến trình, khóa worker và khôi phục trạng thái. |
| YouTube thay đổi, private/xóa, mạng hoặc hết dung lượng | T09 phân biệt lỗi từng video với lỗi cần dừng batch; giữ partial và file thành công. |
| Dữ liệu cá nhân lọt vào fixture/log | T03/T11 dùng fixture tổng hợp trong repo; export và log có dữ liệu thật chỉ ở artifacts local. |

Không có blocker đã xác nhận ngăn bắt đầu T04. Các rủi ro trên cần kiểm tra khi triển khai, không phải kết luận rằng môi trường hoặc tính năng đang hoạt động.

## Resources Needed

- Python >= 3.11 có sqlite3, uv và môi trường ứng dụng tách dependency notebook.
- FastAPI, web HTML/CSS/JavaScript, SQLite local và yt-dlp theo thiết kế; xác minh phiên bản tương thích khi cài. FFmpeg/ffprobe phục vụ remux nếu cần và kiểm tra audio.
- Test runner Python, HTTP test client, browser cho thao tác UI; adapter downloader giả lập để kiểm thử không phụ thuộc YouTube.
- Fixture JSON tổng hợp có expected counts; export thật trong artifacts chỉ dùng đối chiếu local.
- Không cần API key trả phí, tài khoản Spotify hoặc model audio.

T01 đã kiểm chứng Python 3.11.16 / SQLite 3.53.1, CLI help và môi trường sạch không cần notebook. Lỗi SQLite cũ chưa tái hiện; không tuyên bố đã sửa. Test runner dùng unittest chuẩn Python; dependency web/downloader sẽ thêm ở task sử dụng, không cài trước. T02 đã có schema v1, transaction và repository cơ bản; migration lỗi rollback, mở lại giữ review/trạng thái. T03 tiếp tục importer. Chưa có AC toàn ứng dụng nào được nghiệm thu.

### T03 — hoàn tất 2026-09-09

M1 đạt: importer và CLI có 8 test mới, toàn suite 22 test đạt (exit 0). Export local 9.700 dòng: 41 quảng cáo, 258 bản ghi không có video, 9.401 lượt xem / 6.385 video. Mọi ID và watch count khớp CSV notebook; import lần hai reused=true, vẫn một nguồn. T04 tiếp theo, không có blocker mới. Các nhận xét T01/T02 ở trên là bằng chứng tại mốc trước.

### T04 — hoàn tất 2026-09-10

Classifier rules-v1 + tích hợp import + CLI classify. 26 test đạt (exit 0); smoke local 255 music / 6.130 rest. Có bằng chứng/lý do, xử lý xung đột, nhãn kênh local và override video. T05 tiếp theo; không có blocker mới. Chưa có precision/recall hoặc web/download.

### T05 — hoàn tất 2026-09-10

Review service + CLI list/move có 6 test mới; toàn suite 32 test đạt (exit 0). Chuyển một/hàng loạt, nhóm hiệu lực, Unicode search, channel/reason filter, sort/page và tổng nhóm đã kiểm chứng. T06 tiếp theo; khóa mutation khi batch chạy thuộc T08, giao diện browser thuộc T07. Không có blocker mới.

### T06 — hoàn tất 2026-09-10

Server FastAPI/Uvicorn + API import/list/move, CLI serve, multipart và request validation, Host/Origin và body limit. 8 test mới, toàn suite 40 test đạt cả .venv và môi trường sạch; HTTP loopback thực đạt. T07 tiếp theo; UI escape bằng textContent và kéo thả thật kiểm chứng ở T07. Chưa có blocker ứng dụng; TestClient cần chạy ngoài giới hạn sandbox môi trường agent hiện tại (xem S06).

### T07 — hoàn tất 2026-09-10

M2 đạt phần duyệt: UI HTML/CSS/JS thuần cùng origin, hai bảng + folder picker/drop + dialog chọn nguồn + filter/sort/page + chuyển một/hàng loạt. 41 test core/API và 4 browser đạt, wheel chứa assets. T08 tiếp theo; T09 downloader, T10 nối nút tải. Không phát sinh blocker. Browser được mở thủ công từ URL serve; chưa tự mở cửa sổ để giữ lệnh chạy được trong môi trường headless.

### T08 — hoàn tất 2026-09-10

Core create/get/pause/resume/recover/worker_session đã triển khai. 7 test batch mới (gồm multiprocess thật) + 1 HTTP conflict test; toàn suite 49 test đạt, 4 browser regression đạt. Review guard khóa cả queued và running để tránh sửa giữa tạo snapshot và worker nhận việc. T09 tiếp theo, T10 mới nối nút/CLI tải; API tạo batch chưa công bố ở T08. Không có blocker mới.

### T09 — hoàn tất 2026-09-10

Worker tuần tự + adapter yt-dlp đã tải audio thật giữ codec. Thêm 11 test worker: progress, stop, retry, file mất, collision, disk/permission, crash sau publish và child giữ lock khi cha chết. Toàn suite 60 core/API + 4 browser đạt; mẫu Opus thật giải mã được và lần sau skip. Không đổi phạm vi hoặc schema. T10 tiếp theo nối các điều khiển tải vào CLI/web; sau đó T11 nghiệm thu toàn luồng và T12 hướng dẫn. M3 vẫn chờ T10.

### T10 — hoàn tất 2026-09-10

Nút tải, output path, preview số cần tải/tổng, polling và per-file errors có phân trang đã nối. CLI download/status/stop/resume dùng cùng service; worker detached dùng flock hiện có. 5 test controls mới và 1 browser flow mới; tổng 65 core/API + 5 Chromium đạt. M3 chức năng hoàn tất. T11 tiếp theo nghiệm thu mọi AC; T12 kiểm tra hướng dẫn/môi trường sạch. Không mở rộng scope sang analytics hoặc model audio.

### T11 — hoàn tất 2026-09-10

[Báo cáo AC01–AC08](../testing/ACCEPTANCE.md) ghi bằng chứng và giới hạn Linux/JSON. Thêm browser E2E 6.400 video với restart server, CLI reimport, file mất tải lại; thêm protocol error test downloader và hai công cụ kiểm chứng thủ công (trace core, smoke một video mạng). 66 core/API + 6 browser đạt; mẫu thật Opus giải mã được, lần sau skip. Không đổi code production/schema; chưa đo accuracy hoặc tải mọi nhạc cá nhân. T12 tiếp theo để kiểm tra quickstart sạch; M4 còn mở.

### T12 — hoàn tất 2026-09-10

[Kiểm chứng cài đặt](../testing/QUICKSTART.md): môi trường Python sạch cài package không editable với 25 package runtime, offline smoke và mẫu audio thật đạt; sau thêm test/browser, 66 core/API + 6 Chromium đạt. README được sắp lại theo luồng dùng, có dữ liệu/khôi phục và điều kiện chạy. M4 đóng; T01–T12 hoàn tất trong phạm vi Linux/JSON. Không phát sinh thay đổi scope hoặc code production.
