---
phase: requirements
title: Auralytica — Tải nhạc từ lịch sử YouTube
description: Phạm vi MVP và tiêu chí nghiệm thu cho CLI cùng web local nhận folder Google Takeout
---

# Auralytica — Requirements

Cập nhật: **2026-09-10**. T01–T12 hoàn tất; AC01–AC08 đã kiểm chứng trong phạm vi Linux/JSON, [quickstart môi trường Python sạch](../testing/QUICKSTART.md) đạt.

[Dashboard tiến độ dự án](../../../PROJECT_DASHBOARD.md)

[Thiết kế MVP](../design/README.md): luồng sử dụng, dữ liệu dùng chung, các thành phần và xử lý lỗi.

Tài liệu này ghi phạm vi MVP đã triển khai. Hướng phiên bản tiếp theo nằm ở [Web workflow — requirements](2026-09-20-feature-web-workflow.md): web-only, Import → Explore → Deduplicate → Download; phần đó ưu tiên khi khác với yêu cầu CLI/màn hình gộp dưới đây. Các phương án audio model, nhận diện bài hát và matching Spotify trong [problem.md](../../references/problem.md) hoặc notebook là tham khảo/thử nghiệm trước đó, không phải yêu cầu triển khai MVP.

## Problem Statement
Người dùng muốn tải audio của các video âm nhạc đã xem trên **YouTube thường**, kể cả video không mang category Music. Đầu vào là folder đã giải nén từ Google Takeout; người dùng không phải tự thu thập URL từng video.

“Toàn bộ” là các video nhạc tìm được trong lịch sử được cung cấp và còn tải được. Không thể khôi phục lịch sử không có trong export hoặc cam kết tải video đã xóa/private/không truy cập được.

Đối tượng ban đầu: cá nhân chạy ứng dụng trên máy của mình, muốn có thư viện audio từ những video đã nghe.

Một video thuộc mục tiêu khi **nội dung chính là âm nhạc**: AMV, cover, OST, reupload, unofficial upload, remix, live biểu diễn, instrumental và video BGM độc lập. Loại YouTube Shorts, podcast, video giải trí không phải nhạc, nói chuyện/game có nhạc nền. Category Entertainment/Gaming tự nó không đủ để loại một video nhạc.

## Goals & Objectives
### Mục tiêu chính — MVP

```text
Kéo thả folder Takeout / truyền đường dẫn qua CLI
→ đọc lịch sử và gom video ID
→ phân vào hai danh sách: Đã nhận dạng là nhạc / Còn lại
→ người dùng chuyển video qua lại để chốt danh sách nhạc
→ bấm Tải toàn bộ để tải audio gốc của tất cả video bên nhạc
→ lưu lựa chọn và trạng thái tải để tiếp tục lần sau
```

| ID | Yêu cầu |
| --- | --- |
| R01 | CLI và web local dùng cùng dữ liệu, kết quả phân loại, lựa chọn và trạng thái tải. |
| R02 | Web nhận folder Takeout bằng kéo thả, có nút chọn folder dự phòng; CLI nhận đường dẫn folder. Tìm file lịch sử bên trong và báo rõ nếu thiếu/không hỗ trợ/có nhiều nguồn cần chọn. |
| R03 | Giữ riêng sự kiện xem và video duy nhất. Phân loại/tải một lần mỗi video ID; số lượt xuất hiện trong lịch sử vẫn được giữ để hiển thị và phân tích. |
| R04 | Đề xuất chọn video có bằng chứng nhạc mạnh như artist Topic và ID khớp music library trong export. Chỉ dùng library để đối chiếu các ID có trong lịch sử, không tự thêm bài chưa xem. |
| R05 | Dùng tiêu đề, kênh, metadata và xem lặp làm tín hiệu hỗ trợ. VEVO, tên nghệ sĩ, từ khóa hay lượt xem riêng lẻ không bảo đảm là nhạc. Không khớp quy tắc thì giữ “chưa rõ”. |
| R06 | Loại Shorts, podcast và nội dung giải trí không phải nhạc khi đủ bằng chứng hoặc người dùng xác nhận. Lưu lý do và nguồn bằng chứng; vẫn cho xem/sửa nhóm bị loại. Quyết định cấp video được giữ khi chạy lại và ưu tiên hơn gợi ý tự động. |
| R07 | Hai danh sách cạnh nhau: trái “Đã nhận dạng là nhạc”, phải “Còn lại”. Mỗi dòng có thumbnail/placeholder, tiêu đề, kênh, link YouTube, số lượt xem, lý do và trạng thái tải. Có nút chuyển từng video và checkbox để chuyển hàng loạt qua lại, tìm kiếm/lọc/sắp xếp mỗi bên. Video được thêm thủ công cũng nằm bên nhạc, có ghi nguồn quyết định. |
| R08 | Tự đưa ca chắc là nhạc sang trái; ca chưa rõ và bị loại ở bên phải, có lý do tương ứng. Nút “Tải toàn bộ” tạo một batch cho mọi video bên nhạc tại thời điểm bấm, không phụ thuộc checkbox, trang hoặc bộ lọc. File hoàn tất còn hợp lệ được bỏ qua; hiển thị tổng số nhạc và số cần tải. Không bắt buộc duyệt hết bên còn lại. |
| R09 | Dùng yt-dlp tải **audio stream tốt nhất truy cập được của chính video đã chọn**, giữ định dạng nguồn, không chuyển mã sang MP3. “Gốc” là stream YouTube cung cấp, không phải file master mà người đăng đã upload. |
| R10 | Hiển thị tiến độ; tải lỗi một video không làm mất kết quả các video khác. Ghi lỗi/unavailable riêng, cho thử lại và tiếp tục sau gián đoạn. Không tải lại những file đã hoàn thành còn tồn tại. |
| R11 | Lưu lựa chọn/nhãn/trạng thái theo video ID; nhãn kênh theo channel ID/URL. Nhập lại cùng export không làm mất review hoặc tạo việc tải trùng. |
| R12 | Xử lý trên máy; không bắt buộc API trả phí, tài khoản Spotify hoặc model audio. Chỉ cần mạng cho metadata/thumbnail/video khi sử dụng các bước đó. Dữ liệu cá nhân và file audio ở máy người dùng. |

### Mục tiêu phụ — sau luồng tải hoạt động

Dashboard **trong ứng dụng** phân tích dữ liệu lịch sử: số video, số sự kiện xem, kênh, thời gian, lượt xem lặp và trạng thái thư viện nhạc. Không diễn giải thời lượng video thành thời gian thực tế người dùng đã nghe. Danh sách biểu đồ chi tiết được để lại cho giai đoạn sau.

### Ngoài phạm vi MVP

- Chuyển playlist sang Spotify; tìm bản tương ứng theo ISRC/album/catalog hoặc tự thay video bằng một bản thu khác.
- Nhận diện tên bài bên trong video, cắt bài, tách giọng/BGM hoặc audio fingerprinting.
- Chạy model audio trên toàn bộ lịch sử; xây bộ phân loại tổng quát với cam kết tự động chính xác 100%.
- Hosted web/SaaS, nhiều tài khoản, upload toàn bộ Takeout lên server bên ngoài.
- Bắt buộc gán nhãn hết các sample nghiên cứu trước khi có luồng tải dùng được.

## User Stories & Use Cases
1. Tôi kéo thả folder Takeout để thấy danh sách video đã xem mà không phải tìm file/URL thủ công (R02–R03).
2. Tôi thấy các video nhạc được gợi ý chọn, kể cả OST/AMV không có category Music (R04–R05).
3. Tôi xem hai danh sách, chuyển video từ “Còn lại” sang nhạc hoặc chuyển ngược khi nhận sai; có thể chọn nhiều dòng để chuyển một lần (R06–R08).
4. Tôi bấm “Tải toàn bộ” để tải mọi video bên nhạc trong một lượt, gồm bản cover/remix/unofficial mà tôi muốn giữ (R08–R09).
5. Tôi chạy lại sau khi mạng gián đoạn; nhãn, lựa chọn và file đã tải vẫn được giữ, chỉ phần chưa hoàn tất cần xử lý tiếp (R10–R11).
6. Tôi dùng CLI cho xử lý hàng loạt và mở web local khi cần duyệt trực quan (R01).

## Success Criteria
Các tiêu chí dưới đây **đạt kiểm chứng chức năng T11** theo [báo cáo nghiệm thu](../testing/ACCEPTANCE.md), gồm test core/API, browser và một mẫu audio thật. Các giới hạn được ghi trong báo cáo; không suy ra accuracy hoặc khả năng tải mọi video.

- [x] **AC01 — Import:** folder hợp lệ được đọc đúng; URL không phải video, bản ghi quảng cáo và dữ liệu thiếu được thống kê. Folder thiếu lịch sử hoặc định dạng chưa hỗ trợ có hướng dẫn rõ (R02–R03).
- [x] **AC02 — Không tải trùng:** một video xuất hiện nhiều lần chỉ có một mục tải nhưng vẫn hiển thị đúng số sự kiện xem; nhập lại export giữ lựa chọn cũ (R03, R11).
- [x] **AC03 — Phân loại có thể sửa:** nhận ứng viên từ Topic/library; Shorts/podcast/giải trí được loại khi đủ bằng chứng; ca không rõ không bị loại chỉ vì thiếu từ khóa; mọi nhóm đều truy cập và sửa được (R04–R06).
- [x] **AC04 — Hai danh sách:** mỗi video ở đúng một bên; chuyển từng dòng/hàng loạt cập nhật cả hai bên và số đếm, lưu được sau reload. Lọc/phân trang không đổi membership; checkbox chỉ dùng để chuyển. Hoạt động trên ~6.400 video, kể cả thumbnail lỗi (R07–R08).
- [x] **AC05 — Tải toàn bộ:** một lần bấm tạo batch cho toàn bộ bên nhạc, kể cả video bị ẩn bởi bộ lọc/trang; bên còn lại không vào batch. File hoàn tất được bỏ qua, audio mới phát được, đúng ID và không chuyển mã. Nhấp lặp khi đang tải không tạo batch/download trùng (R08–R10).
- [x] **AC06 — Khôi phục:** mô phỏng một video lỗi hoặc mạng gián đoạn; phần khác tiếp tục, chạy lại không mất review và không tải trùng file hoàn tất (R10–R11).
- [x] **AC07 — CLI/web thống nhất:** lựa chọn và trạng thái ở một giao diện được giao diện còn lại sử dụng đúng (R01).
- [x] **AC08 — Chạy local:** luồng chính không đòi API key trả phí, Spotify hoặc model audio (R12).

Chưa đặt số precision/recall hay thời gian hoàn tất tải khi chưa có benchmark. Đánh giá bộ gợi ý trên mẫu có nhãn là cải tiến tiếp theo; khả năng người dùng chốt và tải đúng danh sách là điều kiện nghiệm thu chính của MVP.

## Constraints & Assumptions
### Đã xác nhận

- CLI + web local; nhập folder Takeout; hai danh sách chuyển qua lại; một nút tải toàn bộ bên nhạc; giữ audio gốc.
- Chỉ tải video âm nhạc trong lịch sử, bao gồm upload không chính thức; loại Shorts, podcast và video nói chuyện có BGM.
- Tự xử lý, không bắt buộc dịch vụ trả phí. Ưu tiên metadata/quy tắc và review thủ công cho bản đầu.
- Dashboard phân tích lịch sử là chức năng phụ, không làm chậm luồng tải chính.

### Lựa chọn MVP ghi trong thiết kế, chưa nghiệm thu bằng implementation

- MVP nhận folder có `watch-history.json`; HTML và merge nhiều export đồng thời để sau. Định dạng không hỗ trợ có hướng dẫn rõ.
- Linux desktop trước; CLI mở web local. Đóng gói Windows/macOS để sau.
- SQLite lưu trạng thái dùng chung; người dùng nhập đường dẫn thư mục tải trên máy qua web hoặc CLI. Tên file có video ID, không ghi đè file không liên quan.
- Export không có trường xác nhận Shorts hay thời lượng nghe. Hashtag `#fyp`/`#shorts`, tỉ lệ khung hình hoặc duration đơn lẻ không chứng minh mọi trường hợp là Shorts; kết quả proxy trong notebook không phải ground truth.
- Các nhãn kênh cá nhân trong `artifacts/` dùng cho dữ liệu hiện tại; không biến thành blacklist mặc định áp dụng cho tất cả người dùng.

## Questions & Open Items
| Hạng mục | Cách xử lý hiện tại |
| --- | --- |
| Matching Spotify/ISRC trong notebook 02 | Đã bỏ khỏi phạm vi; không triển khai bước này. |
| Độ chính xác bộ gợi ý | Chưa đo; giữ review thủ công, cải tiến khi có nhãn thực tế. |
| Cách xác nhận Shorts và ca metadata thiếu | Xử lý trong thiết kế metadata; ghi nguồn/lý do và cho sửa, không tuyên bố loại đủ chỉ từ hashtag. |
| HTML, đa ngôn ngữ, nhiều export | JSON Unicode, một export đang xem; HTML/merge nhiều export để sau. |
| Đóng gói, hệ điều hành, hiệu năng cụ thể | Linux desktop và CLI mở web local trước; nền tảng khác để sau, hiệu năng đo khi triển khai. |
| Dashboard phân tích trong app | Sau khi AC01–AC08 của luồng tải được kiểm chứng. |

Các mục để lại trên không yêu cầu tiếp tục mở rộng notebook hay catalog matching. Công việc tiếp theo bám theo các tiêu chí luồng import → review → download.
