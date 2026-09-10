# Auralytica — Project Dashboard

Cập nhật: **2026-09-10** · Giai đoạn: **T01–T12 hoàn tất về chức năng; đang nghiên cứu feature engineering cho bộ lọc**.

> Mục tiêu: kéo thả folder Google Takeout → hai danh sách Nhạc / Còn lại → chuyển video qua lại → bấm Tải toàn bộ để tải audio nguồn của mọi video bên nhạc.

Đây là dashboard Markdown theo dõi dự án, cập nhật thủ công khi có thay đổi; không phải tính năng dashboard phân tích trong ứng dụng.

## Bắt đầu từ đây

| Tài liệu | Vai trò |
| --- | --- |
| [Requirements hiện hành](docs/ai/requirements/README.md) | Nguồn phạm vi và tiêu chí nghiệm thu MVP |
| [Thiết kế MVP](docs/ai/design/README.md) | Bốn phần đã chốt: luồng sử dụng, dữ liệu chung, thành phần, lỗi/khôi phục |
| [Kế hoạch triển khai](docs/ai/planning/README.md) | T01–T12, bốn mốc, phụ thuộc và điều kiện hoàn thành |
| [Kế hoạch kiểm chứng](docs/ai/testing/README.md) | S01–S12 đạt: 66 test core/API + 6 test browser, gồm môi trường Python sạch |
| [Notebook 01](notebooks/01_takeout_eda.ipynb) · [kết quả local](artifacts/notebook-runs/01_takeout_eda.executed.ipynb) | EDA và khảo sát tín hiệu, chưa phải bộ phân loại production |
| [Notebook 02](notebooks/02_classification_design.ipynb) · [kết quả local](artifacts/notebook-runs/02_classification_design.executed.ipynb) | Thử loại trừ và audit sample; phần matching Spotify đã bị bỏ khỏi phạm vi |
| [Hướng dẫn notebooks](notebooks/README.md) | Chạy phân tích và tìm file review |
| [Vấn đề ban đầu](docs/references/problem.md) | Bối cảnh lịch sử; phương án cũ được thay thế bởi requirements hiện hành |

Các link `artifacts/` chỉ hoạt động trên máy có dữ liệu local; thư mục này không được commit.

## Tiến độ theo kết quả có thể dùng

| Mốc | Trạng thái | Bằng chứng / điều kiện hoàn thành |
| --- | --- | --- |
| Khảo sát Takeout | Đã có | Notebook 01 và bảng feature/sample đã xuất |
| Thử tín hiệu loại/nhận nhạc | Có bản nghiên cứu | Notebook 02; chưa có đo accuracy hoặc áp dụng trong app |
| Requirements đúng phạm vi | Đã cập nhật | R01–R12, AC01–AC08; lựa chọn kỹ thuật còn lại được ghi rõ |
| Thiết kế MVP | Đã ghi tài liệu | Hai danh sách, chuyển qua lại, tải batch; chưa phải implementation |
| Planning và kịch bản kiểm chứng | Đã lập | T01–T12 và S01–S12; 12/12 task hoàn tất |
| T01: runtime và CLI help | Hoàn tất | [S01](docs/ai/testing/README.md): 4 test đạt cả môi trường sạch; Python 3.11.16 / SQLite 3.53.1; lỗi SQLite cũ chưa tái hiện |
| T02: schema và persistence | Hoàn tất | [Storage](src/auralytica/storage.py), 10 test storage: schema v1, rollback, ràng buộc và giữ review/trạng thái khi mở lại |
| T03: CLI import | Hoàn tất | 9.700 dòng → 9.401 lượt xem / 6.385 video; khớp toàn bộ ID và watch count với notebook; nhập lại không nhân đôi |
| T07: web local và bảng duyệt | Hoàn tất phần duyệt | Hai danh sách, folder drop/picker, ảnh/link, lọc, chuyển từng/hàng loạt và reload; T10 đã nối tải |
| T09: tải audio và tiếp tục khi lỗi | Hoàn tất core | Mẫu Opus thật 1.430.465 byte giải mã được, lần sau skip; T10 đã nối nút tải |
| Kiểm thử toàn luồng | T11 đạt | [AC01–AC08](docs/ai/testing/ACCEPTANCE.md) có bằng chứng Linux/JSON; [quickstart sạch](docs/ai/testing/QUICKSTART.md) đạt |
| Dashboard phân tích trong app | Để sau MVP | Không chặn việc hoàn thành luồng tải |

Không tính phần trăm hoàn thành vì notebook và code sản phẩm có khối lượng khác nhau.

## Quyết định đã chốt

- [x] CLI + web chạy local, dùng folder export Google Takeout.
- [x] Chỉ lấy video có nội dung chính là nhạc, kể cả AMV/cover/OST/live/remix/unofficial không mang category Music.
- [x] Loại Shorts, podcast và video giải trí/nói chuyện/game có BGM; nhóm bị loại vẫn có thể xem/sửa.
- [x] Hai danh sách: “Đã nhận dạng là nhạc” và “Còn lại”; có nút chuyển từng video hoặc nhiều dòng qua lại.
- [x] Một nút tải toàn bộ bên nhạc, không phụ thuộc checkbox/bộ lọc/trang; bỏ qua file hoàn tất còn hợp lệ.
- [x] Thiết kế MVP dùng JSON, Linux desktop, Python + SQLite và một worker tải tuần tự.
- [x] Giữ audio stream nguồn, không chuyển mã MP3.
- [x] Lưu nhãn/lựa chọn và kết quả tải để chạy tiếp.
- [x] Không bắt buộc API trả phí, tài khoản Spotify hay model audio.
- [x] Bỏ matching Spotify, ISRC/album matching, tách giọng và tìm tên bài trong video khỏi MVP.

## Snapshot dữ liệu nghiên cứu

Nguồn: snapshot nghiên cứu được đối chiếu ngày **2026-09-07**, từ các CSV của notebook 01 `signals-v2` và notebook 02 `classification-design-v1`; không phải phép đo mới ngày cập nhật dashboard. Đây là kết quả rule thử nghiệm, **không phải danh sách nhạc đã được xác minh hoặc đã tải**. Các nhóm nghiên cứu dưới đây sẽ được gom vào hai danh sách trong giao diện.

| Chỉ số | Số lượng |
| --- | ---: |
| Video duy nhất sau lọc bản ghi quảng cáo | 6.385 |
| Nguồn Topic/library được rule nhận | 255 |
| Ứng viên nhạc cần duyệt | 652 |
| Rule thử nghiệm loại | 1.687 |
| Ứng viên loại cần duyệt | 219 |
| Chưa đủ bằng chứng | 3.572 |
| Sample khám phá / mẫu ngẫu nhiên giữ riêng | 262 / 300 |
| Nhãn thủ công đã điền trong hai bộ sample | 0 |

Lưu ý: 1.687 là kết quả gồm nhãn kênh người dùng và proxy hashtag; rule cũ gộp cả `#fyp`/`#foryou` vào dấu hiệu short-form. Chưa thể nói đã xác nhận hoặc loại hết Shorts/podcast. Sửa cách phân biệt bằng chứng chắc chắn và nghi ngờ khi chuyển sang app.

## Trạng thái hiện tại và bước sử dụng

M1–M4, T01–T12 đã hoàn tất. Chạy `uv run --no-sync auralytica serve`, mở http://127.0.0.1:8765, nhập Takeout, duyệt Nhạc/Còn lại rồi bấm Tải toàn bộ. Máy mới làm theo [README](README.md) trước.

Cải tiến tiếp theo nên dựa trên video bị nhận nhầm/bỏ sót hoặc lỗi tải khi dùng thực tế. Dashboard phân tích trong app, HTML và đa nền tảng chưa thuộc phần đã hoàn thành; không tự mở rộng phạm vi từ kết quả MVP.

Các mốc ở cuối tài liệu là lịch sử tại từng thời điểm; trạng thái hiện hành nằm ở đầu dashboard.

## Còn để lại / rủi ro thực tế

| Hạng mục | Trạng thái / hành động |
| --- | --- |
| Cách nhận Shorts | Takeout chưa đủ; metadata hoặc review bổ sung. Không dùng duration/hashtag đơn lẻ làm chân lý. |
| Nhạc thiếu từ khóa, kênh nhiều loại nội dung | Giữ hàng chờ và sửa cấp video; xem lại nhiều chỉ tăng ưu tiên. |
| Video xóa/private/tải lỗi | Hiện trạng thái và cho thử lại; không mất các file tải thành công. |
| JSON/HTML và đa nền tảng | Đã chọn JSON Unicode và Linux desktop trước; HTML, merge nhiều export và đóng gói nền tảng khác để sau. |
| Chất lượng gợi ý tự động | Chưa có nhãn độc lập để đo; không tuyên bố accuracy. |

## Quy tắc cập nhật dashboard

1. Chỉ đánh dấu “đã xong” khi có file, kết quả chạy hoặc kiểm thử tương ứng; thêm link bằng chứng.
2. Nếu thay đổi phạm vi, sửa requirements trước rồi cập nhật bảng quyết định và công việc ở đây.
3. Mỗi mốc cập nhật ngày, trạng thái, việc tiếp theo và lỗi còn tồn tại. Snapshot thống kê là dữ liệu nghiên cứu tại thời điểm chạy.
4. Không lưu tiêu đề/URL lịch sử cá nhân, credentials hoặc nội dung CSV review vào dashboard.

## Mốc T04 — 2026-09-10

Đã có [classifier](src/auralytica/classification.py), tự chạy trong import và lệnh classify. **26 test đạt**; smoke local: 255 music / 6.130 rest, tổng 6.385 video. Đây là gợi ý chưa đo accuracy; rest gồm cả ca chưa rõ và có bằng chứng loại trừ. Không dùng blacklist kênh cá nhân mặc định. T05 tiếp theo để xem/chuyển nhóm qua CLI, sau đó T06–T07 làm web.

## Mốc T05 — 2026-09-10

Đã có [review service](src/auralytica/review.py) và CLI list/move. **32 test đạt**: lọc, phân trang, tổng hai nhóm, chuyển hàng loạt atomic, giữ sau reopen và không xóa file. Smoke local 6.385 video: hai trang 50 dòng trong 0,086 giây (một lần đo, chưa phải benchmark web). T06 API web local tiếp theo.

## Mốc T06 — 2026-09-10

Đã có [API local](src/auralytica/web.py) và `auralytica serve`. Import/list/move dùng chung SQLite với CLI; upload tối đa hai file, giới hạn 64 MiB, kiểm tra Host/Origin. **40 test đạt**, kể cả môi trường sạch không cài notebook. Smoke HTTP thật đã chạy startup → multipart import → list → move và tự dừng server. T07 tiếp theo để dựng giao diện hai bảng; chưa có nút tải/audio.

## Mốc T07 — 2026-09-10

Giao diện hai bảng đã dùng được: folder picker, drag/drop thật trên Chromium, chọn nguồn khi có nhiều lịch sử, ảnh lỗi có placeholder, Unicode search, lọc lý do/sort/page, chuyển từng dòng/hàng loạt và reload giữ sửa tay. Checkbox chỉ chuyển; đổi filter/page xóa tick. **41 test core/API + 4 test Chromium đạt**. Fixture 6.400 video import/filter/move trong 1,39 giây (một lần chạy local, không phải cam kết hiệu năng).

[Ảnh UI với dữ liệu tổng hợp](artifacts/browser-runs/t07-ui.png). Wheel có đủ HTML/CSS/JS. Chạy `uv run --no-sync auralytica serve`, mở http://127.0.0.1:8765. T08 tiếp theo: snapshot và khóa worker; tải audio/nút tải chưa hoạt động.

## Mốc T08 — 2026-09-10

[Batch core](src/auralytica/batches.py) đã có: snapshot mọi video bên nhạc, skip file hợp lệ ở đúng thư mục, create idempotent khi đang chờ/chạy, pause/resume/recover và flock giữ quyền worker. Hai tiến trình thật cùng tạo batch chỉ nhận một ID; chỉ một worker giữ khóa, tiến trình bị kill vẫn khôi phục được. Import/move/classify bị chặn khi queued/running; API trả 409, list vẫn hoạt động.

**49 test core/API + 4 test Chromium đạt.** Chưa tải audio hoặc bật nút tải; T09 tiếp theo cho yt-dlp, T10 nối điều khiển người dùng.

## Mốc T09 — 2026-09-10

[Worker audio](src/auralytica/downloader.py) dùng yt-dlp, giữ codec nguồn, lưu tiến độ/lỗi từng video. Lỗi một video vẫn chạy tiếp; dừng giữ file dở, resume bỏ qua file thành công. Tên chứa video ID và không ghi đè file có sẵn. Downloader con giữ khóa worker nếu tiến trình cha bị kill.

**60 test core/API + 4 test Chromium đạt.** Mẫu tải thật từ lịch sử local: audio Opus, 1.430.465 byte, ffmpeg giải mã exit 0; batch kế tiếp skip 1 file. [Bằng chứng local](artifacts/download-smoke/t09-worker/validation.json). Kiểm thử dừng, crash và hết dung lượng dùng giả lập có kiểm soát; chưa nghiệm thu toàn bộ lịch sử.

Tiếp theo **T10**: bật nút Tải toàn bộ, chọn thư mục đích, hiển thị tiến độ/lỗi, dừng/tiếp tục và CLI download/status/stop/resume. Nút tải hiện vẫn disabled; M3 và AC toàn luồng chưa hoàn tất.

## Mốc T10 — 2026-09-10

Đã bật **Tải toàn bộ**, nhập thư mục đích, số file cần tải, tiến độ/lỗi từng video và dừng/tiếp tục. CLI có download/status/stop/resume dùng chung database. Worker nền tiếp tục khi đóng tab/server; dừng qua CLI hoặc giao diện. Nhóm nhạc trống hoặc mọi file còn hợp lệ thì nút tải bị khóa. Bộ lọc/checkbox không giới hạn snapshot.

**65 test core/API + 5 test Chromium đạt.** Browser đã chạy tải → dừng → sửa nhóm → tiếp tục snapshot cũ → lỗi từng video → reload → thử lại; fixture audio tổng hợp, không tải mạng trong lượt kiểm thử này. [Ảnh giao diện](artifacts/browser-runs/t10-download.png). Worker subprocess thật đã kiểm chứng báo lỗi filesystem và khôi phục trạng thái orphan.

Chạy `uv run --no-sync auralytica serve`, mở http://127.0.0.1:8765. M3 hoàn tất phần chức năng; tiếp theo **T11** đối chiếu AC01–AC08 và nghiệm thu toàn luồng, rồi **T12** kiểm tra quickstart môi trường sạch. Chưa tuyên bố hoàn thành nghiệm thu MVP.

## Mốc T11 — 2026-09-10

**AC01–AC08 đạt kiểm chứng chức năng**: [báo cáo nghiệm thu](docs/ai/testing/ACCEPTANCE.md). **66 test core/API + 6 test Chromium đạt**. Luồng 6.400 video chạy qua import → sửa hai chiều → tải 255 video fixture → một lỗi → restart server → retry → reimport; xóa một file khiến lượt mới tải đúng 1, skip 254 và giữ mtime các file cũ.

Mẫu thật qua CLI hiện hành: Opus 1.430.465 byte, giải mã exit 0, lần sau skip 1. Export thật nhập lại: 9.401 lượt xem / 6.385 video, reused=true. Không tải toàn bộ lịch sử qua mạng hoặc đo accuracy từ các kết quả này.

Tiếp theo **T12**: kiểm tra quickstart trên môi trường sạch và hoàn thiện hướng dẫn. M4 chưa đóng cho đến khi T12 hoàn tất. Không phát hiện lỗi production mới ở T11; cảnh báo TestClient/httpx vẫn được ghi trong báo cáo.

## Mốc T12 — 2026-09-10

[Quickstart môi trường sạch](docs/ai/testing/QUICKSTART.md) đạt: package cài không editable, 25 dependency runtime, không notebook/test; CLI import → web/static → chuyển nhóm → CLI đọc lại → reimport giữ lựa chọn. Sau đó thêm dependency kiểm thử: **66 core/API + 6 Chromium đạt**.

Mẫu thật dùng runtime mới tải Opus 1.430.465 byte, giải mã exit 0 và lượt sau skip. README đã sắp lại theo luồng sử dụng, bỏ trạng thái nút tải cũ và bổ sung khôi phục/dữ liệu/điều kiện chạy. Không thay code production/schema.

**12/12 task và M1–M4 hoàn tất trong phạm vi Linux/JSON.** Môi trường Python mới dùng Node.js/FFmpeg/Chromium có sẵn trên máy; chưa phải kiểm chứng hệ điều hành mới hoặc mọi nền tảng. Không tuyên bố accuracy hay đã tải toàn bộ nhạc cá nhân.

## Nghiên cứu chất lượng bộ lọc — 2026-09-11

Người dùng xác nhận các video nhạc bị bỏ sót trong nhóm Còn lại. Kết quả T01–T12 chứng minh luồng hoạt động theo rules-v1; không phải kiểm chứng recall nhận nhạc trên lịch sử thực tế.

Đã [tham khảo hệ thống tương tự](docs/references/music-feature-engineering.md) và chạy [notebook 03](notebooks/03_music_feature_engineering.ipynb): 273 video Còn lại có ≥3 lượt xem, 268 quay lại ≥3 ngày; 207 ca lặp không có tín hiệu nội dung đang thử. 118 seed Topic/library chỉ xem một lần, nên lượt xem lặp không thể là điều kiện bắt buộc. Các số này chưa phải số video nhạc đã xác minh.

Có 126 mẫu khám phá, giữ tách 300 ID eval cũ. Tiếp theo: gán nhãn và so từng nhóm feature trên cùng tập đánh giá trước khi chốt cách quyết định. Chưa đổi classifier/nhãn DB, chưa triển khai metadata crawler hoặc model audio. T13–T16 từng đề xuất chưa được coi là đã hoàn tất hay đã chốt thiết kế.
