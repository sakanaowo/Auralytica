---
phase: requirements
title: Web workflow — Import, Explore, Deduplicate, Download
description: Yêu cầu chuyển Auralytica sang web-only và gợi ý video cùng bài theo tiêu đề đa ngôn ngữ
---

# Web workflow — Requirements

Ngày: **2026-09-20**. Feature: `web-workflow`. Trạng thái: **đã ghi nhận yêu cầu người dùng; chưa triển khai hoặc nghiệm thu**.

Tài liệu này thay thế yêu cầu CLI + web và màn hình gộp trong [requirements MVP cũ](README.md) đối với phiên bản tiếp theo. Các giới hạn nguồn Takeout, audio nguồn, lưu sửa tay và khôi phục tải vẫn giữ. Các báo cáo kiểm thử cũ chứng minh nền tảng hiện có, không phải nghiệm thu luồng mới.

## Problem Statement

Ứng dụng hiện có nhập Takeout, hai bảng duyệt và tải batch nhưng gộp trên một trang. Metadata, preview/apply và công cụ nghiên cứu còn cần CLI/CSV, không phù hợp với luồng sử dụng mong muốn. Người dùng muốn thao tác hoàn toàn qua web local với bốn trang có mục đích rõ ràng.

Nhóm **Đã nhận dạng** hiện chứa phần lớn nhạc theo xác nhận của người dùng; Explore cần xuất phát từ nhóm này để hiểu thư viện và tìm đặc điểm hữu ích. Không lấy phần Còn lại hoặc 5 trang đầu của nó làm trung tâm sản phẩm. “Phần lớn” là nhận định người dùng, chưa phải số đo recall.

Nhiều video khác ID đăng cùng bài, có tên gốc/phiên âm/tên ở ngôn ngữ khác: **Shoujo A / 少女A**. Gom các lần xem cùng ID và bỏ qua file đã tải chưa giải quyết được dạng trùng này. Cần gợi ý nhóm cùng bài, trình bày các phiên bản để người dùng chọn bản tải.

## Goals & Objectives

### Luồng đã chốt

**Import → Explore → Deduplicate → Download**. Mỗi bước là trang riêng có URL và điều hướng rõ, có thể quay lại; mỗi danh sách có phân trang dữ liệu riêng.

| Trang | Mục đích | Đầu vào | Đầu ra |
| --- | --- | --- | --- |
| Import | Chọn folder Takeout, kiểm tra nguồn và nhập dữ liệu | Folder đã giải nén | Lịch sử đang hoạt động, thống kê kết quả nhập |
| Explore | Khám phá nhạc đã nhận dạng, phân tích đặc điểm và sửa lựa chọn | Lịch sử + nhóm nhạc + bằng chứng | Danh sách nhạc muốn tải |
| Deduplicate | Tìm các video khác ID có thể cùng bài, chọn bản giữ | Danh sách nhạc từ Explore | Danh sách bản được giữ để tải |
| Download | Xác nhận thư mục và tải danh sách đã chốt | Danh sách sau dedup | File audio, kết quả và lỗi từng video |

### Yêu cầu chức năng

| ID | Yêu cầu |
| --- | --- |
| W01 | Web là giao diện sử dụng duy nhất: import, review, enrichment, preview/apply, dedup và điều khiển tải đều thao tác trên web. Người dùng không phải chạy lệnh hoặc trao đổi CSV giữa các bước. Loại bỏ CLI nghiệp vụ khỏi giao diện/tài liệu sử dụng sau khi web đạt tương đương; tái sử dụng backend và worker nội bộ. |
| W02 | Bốn trang có tên, mục đích, trạng thái đầu vào và nút bước tiếp theo rõ ràng. Hỗ trợ refresh, Back/Forward, truy cập URL trực tiếp; thiếu đầu vào phải hướng dẫn tới bước cần làm, không hiện màn hình rỗng khó hiểu. |
| W03 | Import nhận folder Takeout JSON như hiện tại; chọn nguồn khi có nhiều history/library, báo dữ liệu lỗi/không hỗ trợ, thống kê sự kiện/video. Import thất bại không làm mất thư viện trước đó. HTML/multi-export merge vẫn ngoài phạm vi. |
| W04 | Explore mặc định trình bày nhóm Nhạc, có tìm kiếm/kênh/lý do/sắp xếp và phân trang. Còn lại là mục phụ có thể mở để bổ sung/sửa video. Mỗi video có tiêu đề, kênh, link, ảnh hoặc placeholder, lượt xem cá nhân và nguồn quyết định. |
| W05 | Explore có phân tích nhóm Nhạc: số video, phân bố lượt/ngày xem, kênh, tín hiệu tiêu đề và mức có/thiếu metadata. Phân biệt nhãn người dùng với quy tắc tự nhận; không dùng nhóm Còn lại như bộ nhãn non_music mặc định hoặc gọi tỷ lệ khớp là accuracy. |
| W06 | Thu thập metadata và preview/apply có giao diện tiến độ, lỗi, số video, lý do, nguồn và log. Hiển thị phạm vi trước khi chạy; không tự gửi toàn bộ lịch sử hoặc tải audio khi chỉ làm enrichment. Cache/tạm dừng/tiếp tục giữ hành vi backend đã có. |
| W07 | Giữ quyết định thủ công theo video ID khi chuyển trang/reload/reimport. Metadata thuộc video cần được phân biệt với watch_count/watch_days thuộc lịch sử hiện tại; đổi import không được tự làm mất evidence còn hợp lệ chỉ vì history hash khác. Preview/apply vẫn kiểm tra snapshot hiện tại, khóa batch và ghi audit. |
| W08 | Deduplicate xét video **khác ID** có tiêu đề chỉ cùng bài, cả khác ngôn ngữ/phiên âm. Chuẩn hóa Unicode, khoảng trắng, hoa/thường, dấu câu và phụ tố trình bày. Giữ tiêu đề gốc, nguồn alias/matching và căn cứ ghép để người dùng kiểm tra. |
| W09 | Trình bày nhóm **nghi cùng bài**, không khẳng định cùng bản thu chỉ vì cùng tên. Không xóa thông tin cover/live/remix/slowed/instrumental khỏi việc phân biệt phiên bản. Tên ngắn/phổ biến, nghệ sĩ khác hoặc alias chưa có bằng chứng không đủ để tự gộp chắc chắn. |
| W10 | Người dùng có thể giữ một, nhiều hoặc tất cả video trong nhóm; bỏ một gợi ý ghép sai; hoàn tác lựa chọn. Hiển thị tiêu đề/kênh/link/preview và metadata hữu ích nếu có. Chưa có metadata phải thể hiện chưa biết, không chế tạo số liệu. |
| W11 | Dedup chỉ quyết định bản được đưa vào danh sách tải, không xóa lịch sử/file và không chuyển video bị bỏ bản sang nhóm không phải nhạc. Khi chưa chọn loại bản nào, giữ mọi bản; cho phép bỏ qua bước dedup để tiếp tục. Không buộc duyệt toàn bộ nhóm nghi trùng. |
| W12 | Download xem trước số được giữ, số bỏ do dedup và số file có thể skip, chọn thư mục đích, rồi tạo snapshot tải. “Tải toàn bộ” nghĩa là mọi bản được giữ **sau dedup**, không chỉ trang/bộ lọc/checkbox tạm đang xem. |
| W13 | Tải audio tốt nhất truy cập được của đúng video giữ lại; không tự thay bằng bản khác, không chuyển mã MP3. Giữ tiến độ, dừng/tiếp tục/thử lại và skip file hoàn tất hợp lệ. Lỗi một video không chặn những video khác. |
| W14 | Lưu trạng thái từng bước, lựa chọn phiên bản và căn cứ thay đổi. Đổi tập nhạc/import làm tập dedup thay đổi phải đánh dấu phần cần xem lại; không âm thầm loại video mới theo quyết định nhóm cũ. Batch đã tạo giữ snapshot, sửa lựa chọn sau đó không sửa batch đang chạy. |
| W15 | Bảng có tổng số, vị trí trang, trước/sau hoặc chọn trang và kích thước trang rõ ràng; đổi lọc đưa về trang hợp lệ. Phân biệt chọn để chuyển nhóm ở Explore với chọn bản giữ ở Deduplicate. Số tổng tải không phụ thuộc phân trang. |

### Ngoài phạm vi

- Không tìm bản thay thế trên Spotify/Apple Music, ISRC matching, nhận diện tên bài bằng audio hoặc fingerprint/tách giọng.
- Không tự xóa file hoặc tự giữ một bản duy nhất cho mọi bài. Cùng bài không đồng nghĩa cover/live/remix dư thừa.
- Không cam kết nhận diện mọi tên dịch/phiên âm chỉ bằng regex, hoặc không có false positive.
- Không mở rộng nghiên cứu reel trong giai đoạn này; nhãn đã có vẫn được giữ.
- Chưa làm hosted SaaS, đăng nhập nhiều người, merge nhiều Takeout hay đóng gói đa nền tảng.

### Phương án đã cân nhắc

- Giữ một màn hình với các phần thu gọn: ít thay đổi nhưng không đáp ứng bốn trang theo mục đích.
- Wizard bắt buộc hoàn tất tuần tự: dễ hướng dẫn nhưng cản quay lại/duyệt một phần.
- **Bốn trang có điều hướng, giữ trạng thái và kiểm tra đầu vào**: hướng đã chọn; được phép bỏ qua dedup, không buộc gán nhãn hết.

## User Stories & Use Cases

1. Tôi nhập Takeout bằng web và biết đã đọc được bao nhiêu video, không phải truyền đường dẫn qua terminal.
2. Tôi khám phá thư viện nhạc đã nhận dạng và đặc điểm của nó; chỉ mở Còn lại khi cần tìm thêm hoặc sửa kết quả.
3. Tôi thấy Shoujo A / 少女A có thể là cùng bài dù khác ID/tên, hiểu căn cứ ghép và chọn bản muốn giữ.
4. Tôi vẫn giữ được bản gốc và cover/live/remix yêu thích; bỏ bản trùng không làm chúng biến thành non_music.
5. Tôi tải toàn bộ danh sách sau lựa chọn, đóng/mở web hoặc thử lại khi lỗi mà không mất tiến độ.
6. Tôi quay lại Explore sửa nhãn; web báo tác động lên dedup/danh sách tải, không thay âm thầm batch đã chạy.

## Success Criteria

| AC | Tiêu chí nghiệm thu quan sát được | Liên quan |
| --- | --- | --- |
| WA01 | Đi từ nhập folder tới tải và retry chỉ bằng browser, không cần CLI nghiệp vụ hoặc CSV trung gian. | W01, W03, W06, W13 |
| WA02 | Cả bốn trang có URL; refresh/back/direct URL hoạt động, thiếu dữ liệu được hướng dẫn đúng bước. | W02, W14 |
| WA03 | Explore mở nhóm Nhạc mặc định; số liệu và nguồn nhãn được đối chiếu fixture độc lập; Còn lại không bị coi là ground truth âm tính. | W04–W05 |
| WA04 | Fixture hai video khác ID tên Shoujo A và 少女A, có bằng chứng alias cùng bài, được đề xuất chung nhóm; UI giữ nguyên tên và hiển thị căn cứ. | W08–W10 |
| WA05 | Tên giống nhau nhưng khác nghệ sĩ/nội dung không bị tự loại; cover/live/remix được phân biệt và người dùng có thể giữ nhiều bản, từ chối ghép, hoàn tác. | W09–W11 |
| WA06 | Loại một bản khỏi tải không xóa video/file hoặc đổi nhãn music; reload giữ lựa chọn. Bỏ qua dedup giữ đầy đủ nhạc đã chọn. | W10–W11, W14 |
| WA07 | Với nhiều trang/lọc đang bật, snapshot tải vẫn chứa chính xác toàn bộ bản được giữ; loại bản và skip file đã có được đếm riêng. | W12, W15 |
| WA08 | Enrichment/preview/apply chạy trên web, ghi audit và giữ override; snapshot cũ bị từ chối, không sửa thư viện khi batch queued/running. | W06–W07 |
| WA09 | Reimport cùng hoặc khác nguồn giữ lựa chọn theo ID; metadata còn hợp lệ không bị bỏ chỉ vì hash lịch sử đổi; recurrence tính từ nguồn mới. | W07, W14 |
| WA10 | Một video tải lỗi không chặn batch; stop/resume/retry giữ snapshot và các file đã hoàn tất hợp lệ. | W13–W14 |
| WA11 | Không mất dữ liệu hiện có khi nâng cấp; metadata/audio/thumbnail chỉ gọi khi chức năng tương ứng cần; title/alias không thực thi HTML/script. | W03, W06–W14 |
| WA12 | Chạy thử browser với ít nhất 7.500 video: số trang/tổng/nhóm chính xác, không treo luồng điều hướng, không bắt render toàn bộ danh sách một lượt; báo cáo thời gian đo thực tế. | W02, W04–W05, W15 |

Không đặt ngưỡng accuracy/latency thiếu bằng chứng. Đánh giá matching cần bộ ca có nhãn, gồm đúng/sai/cùng bài khác bản thu và tên đa ngôn ngữ; báo cáo kết quả có phạm vi, không đánh đồng unit test với accuracy thực tế.

## Constraints & Assumptions

- Phạm vi nền tảng kế thừa: web local trên Linux, Takeout JSON, Python/SQLite/worker tải đã có. Có thể tái cấu trúc frontend nhưng không yêu cầu viết lại backend.
- Cách cài/mở ứng dụng local được chốt ở thiết kế. Yêu cầu sản phẩm là không cần terminal cho nghiệp vụ sau khi mở web; cơ chế khởi động/worker nội bộ không phải tính năng CLI cho người dùng.
- Không bắt buộc API trả phí/model audio. Công cụ alias/phiên âm và thuật toán ứng viên sẽ được so ở design; mặc định ưu tiên xử lý local và evidence đã có. Nếu cần gửi thêm tiêu đề ra dịch vụ ngoài hoặc thêm chi phí phải quay lại review phạm vi, không coi đây là đã được chấp thuận.
- Giữ snapshot/log nghiên cứu riêng; dữ liệu cá nhân, nhãn và file tải không commit. Dùng fixture tổng hợp cho test.
- Số 502 nhạc thuộc lần đo trước, không hardcode làm giới hạn/số nghiệm thu.
- Triển khai web tương đương trước khi gỡ CLI nghiệp vụ, tránh mất thao tác đang có. Các lệnh/code backend hiện tại chưa bị xóa trong phase requirements.

## Questions & Open Items

**Đã chốt:** web-only; bốn trang; Explore lấy nhóm Nhạc làm trung tâm; dedup theo bài qua tiêu đề đa ngôn ngữ; giữ phân biệt phiên bản; người dùng quyết định bản tải; không tự xóa.

**Chuyển sang design, không phải điều kiện sản phẩm chưa chốt:** công cụ alias/phiên âm/matching và ngưỡng ứng viên; bố cục từng trang; schema/migration và API; cách khởi động local; kế hoạch loại bỏ CLI sau khi web đạt tương đương. Không mặc định dùng dịch vụ dịch/LLM hoặc tự nhận mọi tên khác ngôn ngữ.

**Trạng thái workspace:** có nhiều thay đổi chưa commit trên `feature/music-feature-engineering`. Lượt này chỉ tạo tài liệu tại workspace người dùng đang mở; chưa chuyển nhánh/worktree hoặc commit. Tách workspace implementation cần bảo toàn phần code chưa commit trước đó; không lấy checkout HEAD cũ làm nền mà bỏ các thay đổi này.

**Task tracing:** probe `npx ai-devkit@latest task list --name web-workflow --json` gần nhất exit 1, `unknown command 'task'`; dùng tài liệu và dashboard theo dõi, không coi task CLI là đã tạo.

Tài liệu liên quan: [design nháp](../design/2026-09-20-feature-web-workflow.md), [kế hoạch ban đầu](../planning/2026-09-20-feature-web-workflow.md), [kịch bản nghiệm thu](../testing/2026-09-20-feature-web-workflow.md). Bước tiếp theo: review requirements/design; chưa phê duyệt triển khai từ việc khởi tạo tài liệu.
