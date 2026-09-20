# Phân tích danh sách đang phục vụ tại localhost — 2026-09-18

Nguồn: HTTP GET trực tiếp `http://127.0.0.1:8765/api/videos`, lấy đủ hai nhóm theo watch_count, page_size=1000. Kiểm tra totals và trang đầu trước/sau, đối chiếu toàn bộ ID/nhóm/watch_count với active import trong SQLite read-only. Không đổi code/nhãn/DB, không gọi YouTube.

[Snapshot và summary](../../artifacts/live-list-analysis/20260918T161051Z/summary.json) · [250 dòng đầu, link và tín hiệu](../../artifacts/live-list-analysis/20260918T161051Z/first_250.html) · [CSV toàn bộ Còn lại](../../artifacts/live-list-analysis/20260918T161051Z/rest_analysis.csv).

## Dữ liệu hiện tại đã đổi

Active import **2**, tổng **7.347 video: 502 Nhạc / 6.845 Còn lại**. Các số 278/6107 và danh sách 250 dòng cũ không còn mô tả giao diện hiện tại. Nhóm Nhạc hiện có 263 theo Topic và 239 theo sửa tay. Không quy toàn bộ sửa tay này cho lần apply 18 video.

21 nhãn music trong bộ review FE03 đều đang ở Nhạc; không còn ca có nhãn music cũ nằm ở Còn lại. Hai nhãn loại vẫn ở Còn lại. Không cần người dùng gán lại các nhãn này.

## Bỏ sót trong nhóm Còn lại

| Phạm vi | Chưa rõ | Hint nhạc | Ngữ cảnh nói chuyện | Xung đột |
| --- | ---: | ---: | ---: | ---: |
| 6.845 Còn lại | 6.611 | 185 | 43 | 6 |
| 250 video đầu | 230 | 18 | 1 | 1 |

Phân tích tiêu đề đã chuẩn hóa NFKC tìm **334 ứng viên** trong toàn nhóm Còn lại; 183 vẫn unknown. Trong 250 dòng đầu có **56 ứng viên**, 38 đang unknown. Đây là regex phân tích rộng, không phải nhãn xác minh hoặc ước lượng tổng nhạc.

| Trang | Video có tín hiệu nhạc thử nghiệm / 50 |
| --- | ---: |
| 1 | 19 |
| 2 | 15 |
| 3 | 8 |
| 4 | 10 |
| 5 | 4 |

Tín hiệu gồm Lyrics/Lyric, Karaoke, Official Audio/Visualizer/MV, Soundtrack; biểu diễn/nhạc cụ, OST/AMV, bản phối/cover/slowed. Tên bài ngắn hoặc không từ khóa vẫn có thể bị bỏ sót. Mỗi dòng CSV giữ các cờ riêng, lý do app, lượt/ngày xem và quan hệ với metadata cũ để truy vết.

**111 video Còn lại có ≥3 lượt xem, đồng thời ≥3 ngày xem.** Không tự nhận hết nhóm này: ngay trang đầu có bài học tiếng Nhật, học vẽ, video debut và nội dung bình luận cùng các ca nhạc. Một kênh có cả Karaoke và debut; nhận toàn kênh sẽ kéo theo nội dung ngoài mục tiêu. Chỉ recurrence hoặc chỉ channel không đủ.

## Hạn chế của tích hợp hiện tại đã tái hiện

Hai video được nhận bằng metadata ở lượt apply trước quay về Còn lại sau import mới. Metadata vẫn tồn tại trong `metadata_json`, nhưng `classify_import` bỏ evidence vì `applied_music_evidence.source_hash` khác active import. Đây là hệ quả của guard vừa triển khai, không phải mất file metadata hoặc mất nhãn thủ công.

Cần tách hai phạm vi: type/category của video có thể tái sử dụng theo **video ID + nguồn/parser + freshness**, còn watch_count/watch_days phải tính lại theo **active import**. Preview/apply vẫn kiểm tra snapshot hiện tại để tránh cập nhật dữ liệu cũ. Không nên dùng việc đổi history hash làm lý do duy nhất vô hiệu hóa metadata của cùng video.

Các tín hiệu Lyrics/Karaoke/MV bổ sung trước đó mới nằm trong preview; classifier import mặc định vẫn có regex hẹp. Vì vậy không chỉ thiếu dữ liệu, mà còn thiếu tích hợp đường chạy mặc định. Sửa vocabulary riêng cũng chưa đủ nếu nhánh hint vẫn giữ rest.

## Ưu tiên tiếp theo

1. Sửa tái sử dụng evidence đúng ID qua reimport; regression cho hai ca vừa bị trả về Còn lại, giữ manual và tính lại recurrence theo lịch sử mới.
2. Dùng cùng logic gợi ý/lý do ở preview và classify, tránh bổ sung tín hiệu chỉ trong công cụ xem trước. Không tự nhận từ keyword đơn lẻ.
3. Làm giàu metadata cho danh sách hiện tại, ưu tiên video xem nhiều và tiêu đề có tín hiệu. Trong 250 dòng đầu chỉ **12 ID có observation trong log cũ**, còn **238 ID chưa có trong log đó**; không tiếp tục dùng manifest 232 ID thuộc danh sách trước. Metadata cũ thuộc snapshot trước, chưa được coi là đã kiểm tra mới.
4. Chỉ đưa ca còn mơ hồ ra review sau các bước trên. Tiếp tục bỏ nghiên cứu reel riêng theo yêu cầu.

Lượt này chỉ phân tích danh sách được yêu cầu. Không áp dụng thay đổi hay quét metadata mới. Dữ liệu cá nhân/tiêu đề đầy đủ giữ trong artifacts local.
