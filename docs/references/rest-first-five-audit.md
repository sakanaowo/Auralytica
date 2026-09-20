# Kiểm tra 5 trang đầu Còn lại — 2026-09-18

Phạm vi theo yêu cầu: tạm bỏ nghiên cứu reel, tập trung nhạc bị bỏ sót trong ứng dụng. Đọc database local ở chế độ read-only, cùng service `list_videos`, sort watch_count giảm dần rồi ID, 50 dòng/trang. Snapshot đang có **260 Nhạc / 6.125 Còn lại**, khớp ảnh người dùng.

[Summary](../../artifacts/filter-audits/20260918T125311Z/summary.json) · [250 dòng và nguyên nhân](../../artifacts/filter-audits/20260918T125311Z/rest_first_250.csv) · [Script tái hiện](../../artifacts/filter-audits/20260918T125311Z/probe.py).

## Kết quả

- 203/250 dòng có lý do unknown, 46 music_hint, 1 conflicting_evidence.
- **12 video đã có nhãn music do người dùng xác nhận** trong cohort FE03 vẫn nằm ở Còn lại. Phân bố trang 1–5: **5 / 2 / 2 / 1 / 2**. Đây là mức bỏ sót đã xác minh tối thiểu, không phải toàn bộ nhạc trong 250 dòng.
- Chỉ 18/250 có observation trong log nghiên cứu 70 ID; 232/250 chưa có trong log đó. Live DB có **0 metadata cache rows, 0 audit runs**. Dữ liệu thu thập trước nằm ở DB nghiên cứu riêng.
- Chạy lại hàm `suggest` hiện hành trên dữ liệu của 250 dòng vẫn cho **0 music**. Chỉ bấm classify lại không giải quyết vấn đề.
- 48/250 có marker lyrics/karaoke/MV/official audio/visualizer; trong đó 38 hiện unknown. Đây là tín hiệu để nhận diện/duyệt, không tự chuyển thành nhãn xác minh.
- Đã tìm đúng các dòng trong ảnh ở trang 5: Karaoke, Plastic Love, Apocalypse, get you the moon, Trốn Tìm, Thắc Mắc và happier. Plastic Love đã có music_hint nhưng vẫn ở Còn lại; các ví dụ còn lại đang unknown. Không tự gán nhãn chỉ từ ảnh/tiêu đề trong lượt này.

## Nguyên nhân

1. **Khoảng trống tích hợp:** CSV review phục vụ notebook; ứng dụng chưa nhập nhãn đó. Metadata collector đã có nhưng kết quả nghiên cứu chưa được tích hợp với classifier/live DB. FE04 chưa triển khai.
2. **Chính sách rules-v1 quá hẹp:** chủ yếu tự nhận Topic/library hoặc quyết định kênh có trước. `music_hint`, VEVO và repeat_views chỉ bổ sung evidence, không chuyển nhóm. Bởi vậy ngay cả Official Music Video vẫn có thể nằm ở Còn lại.
3. **Từ vựng thiếu:** regex MUSIC chưa bao gồm lyrics/lyric, karaoke, M/V, official audio và visualizer. Chỉ bổ sung regex cũng chưa đủ vì nhánh music_hint vẫn giữ rest.

Không tìm thấy bằng chứng lỗi phân trang trong phép đối chiếu này. Nút thắt là quyết định phân loại và dữ liệu đầu vào, không phải bản thân bảng hiển thị.

## Hướng sửa tiếp theo

Ưu tiên **FE04 giới hạn trên 5 trang đầu**; không lấy việc duyệt thêm reel làm điều kiện chặn:

1. Đưa các nhãn video người dùng đã xác nhận vào luồng review ứng dụng theo ID/source hash, giữ mọi quyết định thủ công hiện có và ghi log trước/sau; preview xung đột trước khi áp dụng.
2. Nối metadata đúng ID với bộ lọc; dùng nguồn mạnh, thử UGC kết hợp số ngày xem lại. Thiếu metadata giữ là chưa biết. Muốn kiểm chứng thêm 232 ID phải có bước thu thập riêng; lượt check này không thực hiện request mới.
3. Mở rộng tín hiệu tiêu đề và tách Tutorial/biểu diễn khỏi guard nói chuyện. Preview các chuyển nhóm cùng căn cứ trước khi áp dụng; không tự chuyển mọi video xem nhiều hoặc có từ khóa.
4. Regression: các ca nhạc có nhãn và ví dụ ảnh, giữ override, chỉ active import, không làm thay đổi snapshot download, có log và lý do. Các ca reel đã gán nhãn vẫn được giữ nguyên, nhưng không mở rộng nghiên cứu reel lúc này.

Lượt này chỉ điều tra và lưu bằng chứng, **không sửa classifier hoặc nhóm video trong DB**. Tra cứu memory bằng AI DevKit bị automatic approval review từ chối (tải/chạy npm và truy vấn chưa được xác nhận an toàn); điều tra tiếp tục hoàn toàn local. Không chạy test sản phẩm vì không đổi code.
