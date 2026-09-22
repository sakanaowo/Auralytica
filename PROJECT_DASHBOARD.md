# Auralytica — Project Dashboard

Cập nhật: **2026-09-20 · Bắt đầu feature-frontend-redesign trong worktree .worktrees/feature-frontend-redesign. Requirements, Design, Planning và Testing docs đã hoàn tất (lint OK). Bắt đầu Milestone 1.**

> Mục tiêu mới: Tái thiết kế Frontend theo phong cách Apple Pro Liquid Glass (React 19 + Vite + Tailwind CSS), Explore Dual-Pane 50/50, 1-Click Select trên thẻ bài hát, loại bỏ hoàn toàn sticker/icon rườm rà.

Đây là dashboard Markdown theo dõi dự án, cập nhật thủ công khi có thay đổi; không phải tính năng dashboard phân tích trong ứng dụng.

## Bắt đầu từ đây

| Tài liệu | Vai trò |
| --- | --- |
| [Requirements hiện hành](docs/ai/requirements/README.md) | Nguồn phạm vi và tiêu chí nghiệm thu MVP |
| [Thiết kế MVP](docs/ai/design/README.md) | Bốn phần đã chốt: luồng sử dụng, dữ liệu chung, thành phần, lỗi/khôi phục |
| [Kế hoạch triển khai](docs/ai/planning/README.md) | T01–T12, bốn mốc, phụ thuộc và điều kiện hoàn thành |
| [Kế hoạch kiểm chứng](docs/ai/testing/2026-09-20-feature-web-workflow.md) | WFT02–WFT09 đạt: 116 core/API + 10 Chromium tests và review cuối |
| [Notebook 01](notebooks/01_takeout_eda.ipynb) · [kết quả local](artifacts/notebook-runs/01_takeout_eda.executed.ipynb) | EDA và khảo sát tín hiệu, chưa phải bộ phân loại production |
| [Notebook 02](notebooks/02_classification_design.ipynb) · [kết quả local](artifacts/notebook-runs/02_classification_design.executed.ipynb) | Thử loại trừ và audit sample; phần matching Spotify đã bị bỏ khỏi phạm vi |
| [Notebook 04](notebooks/04_ytmusic_metadata_audit.ipynb) · [báo cáo YouTube Music](docs/references/youtube-music-identification.md) | So metadata player/queue trên 18 mẫu, log cụ thể và hướng nhận diện nhiều tầng |
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

- [x] Web app chạy local, dùng folder export Google Takeout; launcher chỉ còn tùy chọn kỹ thuật.
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

M1–M4, T01–T12 và WFT01–WFT09 đã hoàn tất. Chạy `uv run --no-sync auralytica`, mở http://127.0.0.1:8765, rồi đi theo Import → Explore → Deduplicate → Download. Máy mới làm theo [README](README.md) trước.

Cải tiến tiếp theo nên dựa trên video bị nhận nhầm/bỏ sót hoặc lỗi tải khi dùng thực tế. Dashboard phân tích trong app, HTML và đa nền tảng chưa thuộc phần đã hoàn thành; không tự mở rộng phạm vi từ kết quả MVP.

Các mốc ở cuối tài liệu là lịch sử tại từng thời điểm; trạng thái hiện hành nằm ở đầu dashboard.

## Còn để lại / rủi ro thực tế

| Hạng mục | Trạng thái / hành động |
| --- | --- |
| Cách nhận Shorts | Takeout chưa đủ; metadata hoặc review bổ sung. Không dùng duration/hashtag đơn lẻ làm chân lý. |
| Nhạc thiếu từ khóa, kênh nhiều loại nội dung | Giữ hàng chờ và sửa cấp video; xem lại nhiều chỉ tăng ưu tiên. |
| Video xóa/private/tải lỗi | Hiện trạng thái và cho thử lại; không mất các file tải thành công. |
| JSON/HTML và đa nền tảng | Đã chọn JSON Unicode và Linux desktop trước; HTML, merge nhiều export và đóng gói nền tảng khác để sau. |
| Chất lượng gợi ý tự động | Fixture độc lập nhỏ đạt precision/recall 0,80/0,80; chưa phải accuracy production. Xem [review WFT09](docs/ai/testing/WFT09_FINAL_REVIEW.md). |

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

Đã có [API local](src/auralytica/web.py) và launcher tiền nhiệm `auralytica serve`. Import/list/move dùng chung SQLite với CLI; upload tối đa hai file, giới hạn 64 MiB, kiểm tra Host/Origin. **40 test đạt**, kể cả môi trường sạch không cài notebook. Smoke HTTP thật đã chạy startup → multipart import → list → move và tự dừng server. Đây là mốc lịch sử; subcommand `serve` đã được thay bằng `auralytica` ở WFT08.

## Mốc T07 — 2026-09-10

Giao diện hai bảng đã dùng được: folder picker, drag/drop thật trên Chromium, chọn nguồn khi có nhiều lịch sử, ảnh lỗi có placeholder, Unicode search, lọc lý do/sort/page, chuyển từng dòng/hàng loạt và reload giữ sửa tay. Checkbox chỉ chuyển; đổi filter/page xóa tick. **41 test core/API + 4 test Chromium đạt**. Fixture 6.400 video import/filter/move trong 1,39 giây (một lần chạy local, không phải cam kết hiệu năng).

[Ảnh UI với dữ liệu tổng hợp](artifacts/browser-runs/t07-ui.png). Wheel có đủ HTML/CSS/JS. Mốc này từng dùng subcommand `serve`; lệnh hiện hành là `uv run --no-sync auralytica` theo README.

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

Mốc này từng dùng subcommand `serve`; lệnh hiện hành là `uv run --no-sync auralytica`. Khi đó M3 hoàn tất phần chức năng và T11–T12 còn chờ; xem trạng thái hiện hành ở đầu tài liệu.

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

## Pilot YouTube Music — 2026-09-11

Đã chạy đúng **18 ID được người dùng cho phép**, 36 lời gọi phương thức/37 HTTP request, **27,79 giây** không gồm khởi tạo. [Log từng truy vấn](artifacts/ytmusic-pilot/20260911T041238Z/events.jsonl) và [notebook đã chạy](artifacts/notebook-runs/04_ytmusic_metadata_audit.executed.ipynb) giữ trong artifacts.

Cả **5 ca nhạc bị bỏ sót** đều có type ở metadata trực tiếp: 2 ca OMV/OFFICIAL_SOURCE_MUSIC, 3 ca UGC. Một ca nhạc có category Gaming. Cả 8 ca đối chứng có UGC ở queue nhưng không có type tại player: không dùng queue UGC hoặc category Music làm điều kiện nhận nhạc duy nhất.

**Tiếp theo:** collector/cache/audit theo ID → kiểm chứng tầng UGC/residual bằng feature và nhãn → tích hợp gợi ý vào hai bảng. Chưa thay rules-v1, chưa quét toàn lịch sử; mẫu chưa kiểm chứng podcast và chưa đo precision/recall. [Báo cáo](docs/references/youtube-music-identification.md) ghi các trường log cần có, khoảng trống dữ liệu và điều kiện đánh giá.

## FE02 — collector/cache/audit — 2026-09-11

Đã có `metadata collect/status`, Ctrl+C/resume, cache mặc định 7 ngày, retry lỗi tạm thời, khóa collector và xuất `audit` JSONL. SQLite v2 lưu lịch sử từng lần phân loại và sửa tay; metadata mới chưa được dùng để tự chuyển nhóm. [Hướng dẫn và thiết kế](docs/ai/implementation/METADATA.md).

Smoke bằng collector hiện hành trên bản sao DB với **18 ID đã duyệt**: lần đầu 18 calls, lần sau **0 calls/18 cache hits**, video rows giữ nguyên. [Log và summary](artifacts/metadata-smoke/fe02-20260911T081317Z/summary.json). Log thật giữ local; không thay DB đang dùng trong smoke.

**82 test core/API + 6 Chromium đạt**, wheel build đạt; [bằng chứng và giới hạn](docs/ai/testing/README.md). Migration lỗi và audit lỗi đều đã kiểm tra rollback; nhãn thủ công/download được giữ sau nâng cấp.

**Tiếp theo FE03:** bổ sung phản ví dụ podcast/music Shorts/BGM, đánh giá strong gate và UGC/residual trên nhãn độc lập trước khi FE04 nối gợi ý vào hai bảng. Chưa công bố accuracy hoặc tự quét toàn lịch sử.

## FE03 — mô phỏng residual — 2026-09-13

[Notebook 05](notebooks/05_residual_evaluation.ipynb) đã chạy: strong metadata tìm lại 2/5 ca nhạc bị bỏ sót; thêm UGC + content tìm 4/5; kết hợp recurrence tìm 5/5. Ngưỡng 2/3/5/10 ngày đều cho kết quả giống nhau trên 5 ca này, nên chưa có cơ sở chọn ngưỡng. Metadata vẫn chỉ có cho 18/6.385 video.

Đã xuất **70 mẫu review, 12 ưu tiên**, 5 nhãn music có sẵn và 65 ca chưa có nhãn; manifest 52 ID mới chưa gửi. Mẫu mới tách khỏi holdout 300; không điền nhãn từ policy kênh/YTM. Không có ứng viên token podcast rõ trong snapshot, cần bổ sung phản ví dụ thật. [Báo cáo, mẫu và log phép tính](docs/references/residual-evaluation.md).

**4 cell code của notebook và 5 test nghiên cứu đạt.** FE03 chưa hoàn tất phần đánh giá có nhãn; FE04 chưa triển khai, không thay đổi classifier/DB ứng dụng trong lượt này.


## FE03 — đã thu thập 52 ID bổ sung — 2026-09-13

Đã chạy đúng manifest được người dùng cho phép: **52/52 done, 52 attempts, 29,65 giây**, HTTP 200; [log và summary](artifacts/metadata-smoke/fe03-20260913T082334Z/summary.json). Bản sao DB giữ nguyên nhóm video. Hợp với 18 ID trước thành đủ metadata cho 70 mẫu.

Giữ nguyên cohort khi chạy lại notebook 05: strong/UGC-content/UGC-kết hợp cho **269/276/279 ứng viên** so baseline 255; không phải nhãn đã xác minh. Có type nhạc nhưng UNPLAYABLE và ca OMV/Tutorial mâu thuẫn cần kiểm tra nội dung chính. [Báo cáo cập nhật và 12 ca ưu tiên](docs/references/residual-evaluation.md).

**4 cell code của notebook + 7 test nghiên cứu đạt**; test mới giữ cohort/nhãn cố định sau enrichment và giữ notes khi nhập review. FE03 còn chờ nhãn video; không đổi quy tắc ứng dụng hoặc công bố accuracy.


## FE03 — đã có trang gán nhãn trực tiếp (2026-09-13)

Mở [trang review mới](artifacts/notebook-runs/05_residual/20260913T100651571887Z/review.html) bằng trình duyệt. Duyệt 12 dòng đầu → chọn Nhạc/Không phải nhạc/Chưa rõ/Không mở được → ghi chú → **Xuất CSV nhãn đã sửa**. Nút **Xuất log chỉnh sửa** giữ lịch sử trước/sau. Bản nháp lưu trong trình duyệt; cần xuất file để đưa kết quả vào notebook. [Cách nhập nhãn](docs/references/residual-evaluation.md#gán-nhãn-trực-tiếp-trong-trình-duyệt).

**7 test nghiên cứu + 2 test Chromium đạt; notebook chạy đủ 4 cell code.** Mẫu vẫn 70 ID, chỉ 5 nhãn music đã xác nhận; chưa có nhãn mới từ người dùng nên chưa tính precision/recall, chưa đổi classifier ứng dụng. Bước tiếp theo: nhận CSV đã gán nhãn, chạy đánh giá và xem ca sai trước khi chốt quy tắc FE04.


## FE03 — đã nhập CSV và đánh giá có nhãn (2026-09-18)

CSV người dùng có 18 nhãn mới hợp lệ (16 nhạc, 2 loại); cộng 5 nhãn trước thành **23/70**, còn 47 chưa gán nhãn. [Kết quả hiện hành](docs/references/fe03-labelled-results.md): baseline tìm 4/21 nhạc; metadata mạnh + UGC recurrence tìm **20/21**, không nhận nhầm hai ca reel; nhánh UGC + nội dung hoặc recurrence cũng tìm 20/21 nhưng nhận nhầm cả hai reel. Đây là mẫu khám phá, chưa phải accuracy tổng thể.

Ca còn bỏ sót bị guard Tutorial chặn dù được người dùng xác nhận nhạc. Tăng ngưỡng lên 5 ngày mất thêm hai bài. Đã lưu log dự đoán/sai từng video, bản sao CSV đầu vào và CSV nhãn tích lũy. Notebook chạy đủ 4 cell code, 7 test nghiên cứu đạt. Chưa sửa classifier/DB.

Tiếp theo: [duyệt các ca ưu tiên còn lại](artifacts/notebook-runs/05_residual/20260918T120720595779Z/review.html), nhất là Tutorial/performance và reel/Shorts; bổ sung đối chứng trước khi chốt FE04. Nhãn có trước đã được giữ trong trang mới; hướng dẫn giữ nhãn khi nhập CSV từng phần nằm trong báo cáo.


## Kiểm tra trang 1–5 — ưu tiên mới (2026-09-18)

Theo yêu cầu, tạm bỏ phần nghiên cứu reel. Đọc live DB khớp ảnh: **260 Nhạc / 6.125 Còn lại**. Trong 250 dòng đầu có 12 video đã xác nhận nhạc vẫn ở Còn lại; 203 unknown, 46 music_hint, 1 xung đột. Live DB chưa có cache metadata; log nghiên cứu chỉ phủ 18/250. Chạy lại rules-v1 vẫn không nhận thêm video nào trong 250 dòng.

**Nguyên nhân chính: FE04 chưa tích hợp nhãn/metadata nghiên cứu vào app**, cộng với chính sách chỉ tự nhận chủ yếu Topic/library. Bổ sung regex riêng lẻ không đủ. [Bằng chứng và kế hoạch sửa](docs/references/rest-first-five-audit.md). Bước tiếp theo ưu tiên tích hợp nhãn đã xác nhận + metadata và preview thay đổi trên nhóm này; không yêu cầu duyệt reel thêm trước. Lượt kiểm tra không sửa DB/code hay gọi metadata mới.


## FE04 — đã tích hợp nhãn/metadata vào preview (2026-09-18)

Đã có `auralytica classification-preview`: đọc CSV + JSONL local và DB active import ở chế độ read-only. [Xem 18 thay đổi đề xuất](artifacts/filter-audits/fe04-preview-20260918.html), [JSON/log căn cứ](artifacts/filter-audits/fe04-preview-20260918.json), [hướng dẫn](docs/ai/implementation/CLASSIFICATION_PREVIEW.md).

16 video từ nhãn bạn đã xác nhận, 2 video từ metadata mạnh; không xung đột sửa tay. Có 13 thay đổi trong 5 trang đầu, gồm đủ 12 nhạc đã xác nhận còn bên Còn lại. Tổng dự kiến 278 Nhạc/6.107 Còn lại. Không gọi metadata mới, không sửa live DB. Còn bước apply có bảo vệ snapshot/batch và nối lý do vào web; FE04 chưa hoàn tất.


## FE04 — đã áp dụng vào thư viện (2026-09-18)

Đã chạy apply sau backup: **16 nhãn xác nhận + 2 metadata mạnh**, tổng 278 Nhạc/6.107 Còn lại. Giữ mọi sửa tay cũ và bảng download. [Log 18 thay đổi](artifacts/filter-audits/fe04-applied-events.jsonl) · [kiểm chứng trước/sau](artifacts/filter-audits/fe04-apply-verification.json). `rules-v2-applied-metadata` giữ evidence đã áp dụng qua classify cùng source.

90 test core/API đạt. Preview cũ/sửa tay thay đổi/input thay đổi bị từ chối; batch queued/running khóa apply; lỗi audit rollback toàn bộ. Lượt này không cần người dùng gán nhãn lại và không truy vấn metadata mới. Tải lại trang để thấy nhóm mới; khởi động lại server để nạp classifier/lý do mới trước lần import hoặc classify tiếp theo.

Còn lại: metadata vẫn chỉ phủ 70 ID nghiên cứu; trong 250 dòng đã kiểm tra vẫn thiếu 232 ID. Việc mở rộng cần cho phép truy vấn riêng. Web chưa có nút preview/apply, hiện thao tác bằng CLI; không tuyên bố đã tìm hết nhạc.


## Phân tích danh sách web hiện tại — import 2 (2026-09-18)

Đọc đủ API local và đối chiếu SQLite: **7.347 video, 502 Nhạc/6.845 Còn lại**. Trong 250 dòng đầu có 230 unknown, 56 ứng viên theo tín hiệu tiêu đề (chưa phải nhãn nhạc), 111 video quay lại ≥3 ngày. 21 nhãn music cũ đều đã ở Nhạc.

Phát hiện hai video nhận bằng metadata bị trả về Còn lại khi import thay đổi vì guard source_hash. [Phân tích và hướng xử lý](docs/references/live-library-analysis.md). Ưu tiên sửa metadata theo video ID qua reimport, đồng bộ logic preview/classify và làm giàu danh sách mới. Trong 250 dòng hiện tại chỉ 12 có observation cũ, còn 238 chưa có; phạm vi 232 trước đây đã cũ. Lượt này không sửa nhóm hoặc gọi YouTube.


## Web workflow — requirements đã tạo (2026-09-20)

[Requirements](docs/ai/requirements/2026-09-20-feature-web-workflow.md) có W01–W15 và WA01–WA12; [design nháp](docs/ai/design/2026-09-20-feature-web-workflow.md), [kế hoạch WFT01–WFT09](docs/ai/planning/2026-09-20-feature-web-workflow.md), [kịch bản test](docs/ai/testing/2026-09-20-feature-web-workflow.md).

Chốt: bỏ CLI khỏi luồng sử dụng, bốn trang có mục đích/URL riêng, Explore lấy nhạc đã nhận dạng làm trung tâm; dedup theo tiêu đề cùng bài đa ngôn ngữ (Shoujo A / 少女A), giữ khác biệt cover/live/remix và người dùng chọn bản tải. Không tự xóa file hoặc đổi bản bị bỏ thành non_music. Download dùng tập sau dedup.

Chưa đổi code/schema, chưa gỡ CLI hoặc triển khai trang mới. Bước tiếp theo là review requirements/design, chốt alias/matching, dữ liệu và API. Không đánh dấu các task mới hoàn tất từ kết quả 90 test MVP trước đó. Task CLI chưa khả dụng (`unknown command 'task'`); dùng tài liệu theo dõi. Workspace còn thay đổi chưa commit, chưa chuyển branch/worktree.


## Web workflow — design review (2026-09-20)

[Thiết kế cụ thể](docs/ai/design/2026-09-20-feature-web-workflow.md) đã có route, contract API, job/revision, dữ liệu alias/nhóm/selection và snapshot tải sau dedup. Matching baseline dùng Unicode + alias có nguồn, không tự dịch hoặc gộp cover/live; thiếu alias có thể ghép/xác nhận thủ công. Video mới default keep, lựa chọn loại bản không đổi nhãn music.

Bước tiếp theo: chia task triển khai chi tiết và chuẩn bị workspace bảo toàn code chưa commit. Chưa đổi code hoặc DB, chưa nghiệm thu browser mới. Task CLI vẫn chưa khả dụng theo probe trước; theo dõi bằng docs.


## Web workflow — kế hoạch và worktree sẵn sàng (2026-09-20)

Workspace làm tiếp: `.worktrees/feature-web-workflow`, branch `feature-web-workflow`. 43 file đang sửa/chưa theo dõi đã được chép và kiểm tra hash; thư mục gốc giữ nguyên, chưa commit. Không copy Takeout/audio/live DB. `.venv` riêng đã cài lockfile, 90 test core/API đạt, lint feature đạt cả docs/branch/worktree.

[Kế hoạch triển khai](docs/ai/planning/2026-09-20-feature-web-workflow.md) có bốn milestone, checklist WFT01–WFT09 và mapping 29 kịch bản test. WFT01 hoàn tất chuẩn bị; **tiếp theo WFT02: navigation bốn trang**, rồi WFT03 Import/Explore và WFT04 metadata web. Chưa đổi giao diện/schema ứng dụng trong lượt này.


## Web workflow — WFT02 đã triển khai (2026-09-20)

Code mới ở `.worktrees/feature-web-workflow` trên branch `feature-web-workflow`; app tại workspace gốc chưa tự cập nhật. Đã có bốn URL Import / Explore / Deduplicate / Download, root redirect, workflow state/khóa batch, query giữ lọc và phân trang khi reload/Back/Forward, empty/error/retry. Deduplicate hiện báo rõ chưa có gợi ý cùng bài và cho bỏ qua; chưa loại bản nào.

**92 core/API + 7 Chromium tests đạt**, gồm giữ batch cũ khi Nhạc trống, stop/resume/retry/restart/reimport. Đã kiểm tra giao diện 390px; không dùng live DB hoặc tải audio thật. WFT01–WFT02 done; **tiếp theo WFT03: Explore music-first + thống kê**, rồi WFT04 metadata web, WFT05–WFT07 dedup/tải. CLI chỉ gỡ ở WFT08 sau web parity. Không commit/push.


## Web workflow — WFT03 đã triển khai (2026-09-20)

Explore mặc định nhóm Nhạc; Còn lại thu gọn và chỉ tải khi mở. Có thống kê video/lượt xem cá nhân/ngày UTC, manual/automatic, phân bố lượt/ngày, top kênh, tín hiệu tiêu đề, dữ liệu metadata có/thiếu. Summary toàn nhóm, không đổi theo filter. Bổ sung lọc kênh, page size 25/50/100 và lưu trạng thái trên URL. Kết quả nhập hiển thị khi tới Explore.

**93 core/API + 8 Chromium tests đạt.** Fixture 7.500 video: import/filter/move 1,559s, summary 16,8ms; không lỗi JS hoặc tràn màn hình 390px. Code chỉ trong `.worktrees/feature-web-workflow`, không đổi live DB, chưa commit/push. **WFT01–WFT03 done; tiếp theo WFT04 metadata + preview/apply trên web**, rồi WFT05–WFT06 dedup/chọn bản. Metadata coverage hiện không chứng nhận freshness hoặc chất lượng phân loại.

## Web workflow — WFT04–WFT06 đã triển khai (2026-09-20)

Explore có metadata scope/progress/log, stop/resume, server-side preview/apply và cache freshness. Deduplicate có alias có nguồn, nhóm nghi cùng bài, raw title/marker phiên bản, phân trang nhóm/thành viên, chọn bản keep/exclude, từ chối/hoàn tác và revision chống ghi đè giữa tab. Shoujo A / 少女A được nhóm khi người dùng xác nhận alias; tên/kênh xung đột chỉ là gợi ý và mọi bản mặc định keep.

**109 core/API + 10 Chromium tests đạt.** Fixture 7.500 video/3.750 nhóm dedup mất 0,134 giây. WFT01–WFT06 done; **WFT07 tiếp theo phải làm Download dùng selection dedup**. Hiện Download vẫn tải toàn bộ nhóm Nhạc, nên chưa dùng nó để xác nhận exclude. Code chỉ ở worktree, chưa commit/push và không sửa live DB.

## Web workflow — WFT07 đã triển khai (2026-09-20)

Download dùng đúng tập Nhạc được giữ sau Deduplicate, độc lập bộ lọc/trang/checkbox tạm. Preview tách music/excluded/kept/file đã có/file cần tải và phát token gắn selection, output, trạng thái file. Start với token cũ trả 409; batch mới chỉ chứa ID được giữ, batch cũ vẫn bất biến khi selection đổi rồi resume.

**113 core/API + 10 Chromium tests đạt.** Chromium Shoujo A / 少女A xác nhận loại một ID và chỉ tải ID còn lại; stop/resume/retry/restart/file mất vẫn đạt trong regression. Screenshot mobile `wft07-download.png` không tràn ngang. WFT01–WFT07 done; **tiếp theo WFT08: web parity, launcher local và gỡ CLI nghiệp vụ**. Không commit/push, không sửa live DB.

## Web workflow — WFT08 đã triển khai (2026-09-20)

Đã đối chiếu parity và gỡ toàn bộ subcommand nghiệp vụ sau khi các thao tác có mặt trên web. `auralytica` không đối số chạy loopback và mở browser; chỉ còn `--port`, `--database`, `--no-browser`. Health identity ngăn tái dùng nhầm process/database, desktop entry Linux không mở terminal. Backend và worker vẫn giữ nguyên.

**113 core/API + 10 Chromium tests đạt.** Browser acceptance restart/reimport/status/list không còn gọi CLI. Wheel build và help từ bản cài không editable đạt. Đây là checkpoint trước WFT09; xem kết quả cuối bên dưới.

## Web workflow — WFT09 nghiệm thu xong (2026-09-20)

[Review cuối](docs/ai/testing/WFT09_FINAL_REVIEW.md) đạt: **116 core/API + 10 Chromium + 7 research + 2 research-browser tests**; wheel, lint, JS, bytecode và diff checks đều đạt. Database copy giữ manual label/download/selection; code schema cũ từ chối schema mới mà không ghi. Fixture 7.500 video đạt benchmark phân trang; bộ nhãn độc lập 16 video cho precision/recall 0,80/0,80 trong phạm vi gợi ý tổng hợp, không phải accuracy production.

Security review sửa log yt-dlp để không lưu exception thô, signed URL hoặc token. Không có finding chặn; không commit/push và không sửa live database.

## Frontend Redesign — FE-01 đến FE-05 hoàn thành (2026-09-20)

Đã chuyển đổi toàn bộ giao diện sang kiến trúc **React 19 + Vite + Tailwind CSS v4 + TanStack Query** trong thư mục `frontend/`, đóng gói tĩnh trực tiếp vào `src/auralytica/static/`:
- **Thẩm mỹ Apple Pro Liquid Glass:** Gam màu tối trung tính (Dark Zinc `#09090b`), viền kính mờ sắc sảo 1px, loại bỏ hoàn toàn các emoji/sticker trang trí, điều khiển text-driven trực quan.
- **Explore Dual-Pane 50/50:** Chia đôi màn hình song song giữa Nhạc đã nhận diện và Còn lại. Thẻ bài hát có thumbnail 16:9 sắc nét, cơ chế **1-click select** (bấm thẳng vào thẻ để chọn) và nút chuyển nhanh khi hover.
- **Modal Metadata & Phân loại:** Mở hộp thoại kính mờ riêng biệt để lấy metadata YouTube Music và xem trước bảng phân loại, không choán diện tích 2 cột duyệt bài.
- **Import, Deduplicate & Download:** Đã tái thiết kế đồng bộ theo phong cách tối giản cao cấp.
- **Kiểm thử & Đóng gói:** `npm run build` hoàn tất trong ~700ms; **116/116 unit tests của backend đạt 100% OK**; wheel build đóng gói đầy đủ bundle mới.

