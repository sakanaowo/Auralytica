# Feature engineering để nhận dạng video âm nhạc từ Takeout

Nghiên cứu và chạy dữ liệu: **2026-09-11**. Kết luận: cần phối hợp nội dung với **hành vi xem lại của chính người dùng**, đo chất lượng trên nhãn độc lập trước khi thay rule. Nghiên cứu này chưa thay nhóm video, classifier production hoặc triển khai model/API.

[Notebook 03](../../notebooks/03_music_feature_engineering.ipynb) · [Notebook đã chạy local](../../artifacts/notebook-runs/03_music_feature_engineering.executed.ipynb) · [Số liệu local](../../artifacts/notebook-runs/03_music_features/3ef0ba60cbf2/fe-v1-633cf963/summary.json).

## 1. Các hệ thống tương tự làm gì?

| Nguồn | Phương pháp được công bố | Áp dụng cho Auralytica và giới hạn |
| --- | --- | --- |
| Spotify music videos | Nguồn video chủ yếu từ label/distributor; hiện cũng có upload trực tiếp cho một số nghệ sĩ. Người gửi cung cấp thông tin bài hát. | Đây là catalog có nguồn và metadata, không phải bằng chứng Spotify phân loại video YouTube bất kỳ. Không lấy quy trình matching catalog làm bộ lọc nhạc. [Spotify for Artists](https://artists.spotify.com/en/music-videos) |
| YouTube Recommendations, RecSys 2016 | Tách lấy ứng viên và xếp hạng; kết hợp lịch sử hoạt động với feature người dùng/video. | Học cách tách **tìm ứng viên** và **quyết định tự chọn**. Chỉ tìm trong lịch sử đã import. Bài báo về gợi ý, không trực tiếp giải bài toán music/non-music và không đại diện cho toàn bộ hệ thống YouTube năm 2026. [Bài báo gốc](https://research.google.com/pubs/archive/45530.pdf) |
| Spotify Research, 2018 | Hành vi được hiểu theo mục tiêu nghe; chuẩn hóa theo thói quen cá nhân hữu ích hơn một ngưỡng chung. | Dùng percentile lượt xem trong lịch sử cá nhân và nhiều dạng recurrence. Không mang skip/completion từ Spotify sang khi Takeout không có trường tương ứng. [Nghiên cứu](https://research.atspotify.com/2018/7/understanding-and-evaluating-user-satisfaction-with-music-discovery) |
| PISA, RecSys 2024, dữ liệu Deezer/Last.fm | Kết hợp chuỗi phiên nghe và hành vi lặp lại bằng mô hình session dùng Transformer/ACT-R. | Có căn cứ thử tần suất, quay lại qua phiên/ngày và ngữ cảnh. Kết quả trên catalog nhạc không chứng minh video xem lặp là nhạc; không cần sao chép Transformer cho một lịch sử ít nhãn. [Bài báo](https://arxiv.org/abs/2408.16578) |
| Spotify podcast research, 2022 | Chọn tín hiệu tối ưu như plays hay subscriptions dẫn tới hành vi gợi ý khác nhau. | Phân biệt nhãn nội dung với mức quan tâm. Podcast vẫn tạo tương tác mạnh; không dùng engagement làm nhãn nhạc. [Nghiên cứu](https://research.atspotify.com/2022/05/choice-of-implicit-signal-matters-accounting-for-user-aspirations-in-podcast-recommendations) |
| YAMNet/AudioSet | Dự đoán 521 loại sự kiện âm thanh, trả score/embedding theo thời gian. | Có thể thử làm tầng bổ sung cho ca chưa rõ; phát hiện âm nhạc trong audio chưa chứng minh video có nội dung chính là nhạc. Cần xét BGM, speech và nhiều đoạn; chưa chạy model trong công việc này. [Tài liệu TensorFlow](https://www.tensorflow.org/hub/tutorials/yamnet) |

Các nhận xét ở cột áp dụng là suy luận thiết kế cho Auralytica, không phải kết quả các nguồn đã kiểm chứng trên Takeout của người dùng.

## 2. Dữ liệu có và không có

Snapshot đọc từ SQLite hiện hành ở chế độ read-only: **9.401 sự kiện / 6.385 video**, 10 sự kiện thiếu timestamp, không phát hiện trùng cặp video/timestamp hợp lệ. Thời gian là khoảng lịch sử trong export, không phải toàn bộ tuổi tài khoản. Ngày được tính theo `Asia/Bangkok`, có thể đổi cấu hình.

Có video ID, tiêu đề, kênh, timestamp, số lần xuất hiện và đối chiếu library. Không có số giây đã xem, completion rate, skip hay session ID thật. Khoảng cách tới sự kiện tiếp theo không phải thời lượng xem: có pause, đa tab, nhiều thiết bị và lịch sử bị thiếu.

`watch_count` của ứng dụng là lượt xuất hiện trong Takeout cá nhân; `view_count` từ metadata YouTube là lượt xem công khai. Hai trường phải đặt tên/nguồn riêng. yt-dlp có thể lấy metadata không tải video; các trường category/artist/track không được bảo đảm luôn có. [Tài liệu yt-dlp](https://github.com/yt-dlp/yt-dlp#output-template)

## 3. Các nhóm feature nên thử

| Nhóm | Feature cụ thể trong notebook | Insight cần kiểm chứng |
| --- | --- | --- |
| Tần suất cá nhân | raw count, log(1+count), percentile trong lịch sử | Video được quay lại khác video tình cờ xuất hiện; log tránh để một video cực nhiều lượt áp đảo. |
| Quay lại dài hạn | distinct days/weeks, span, median khoảng cách xem lại | Lặp qua nhiều ngày có thể phân biệt với replay dồn một buổi; vẫn cần đối chứng podcast/tutorial. |
| Phân bố lượt xem | max lượt/ngày, tỷ lệ dồn vào ngày cao nhất | Tách các kiểu nghe lặp thay vì gộp mọi count≥3 thành một boolean. |
| Cơ hội quan sát | ngày từ lần thấy đầu tới cuối export, tỷ lệ ngày có xem | Video mới xuất hiện có ít cơ hội tích lũy count. Feature bị giới hạn bởi cửa sổ export nên không dùng làm nhãn âm. |
| Phiên và ngữ cảnh | số phiên suy đoán; tỷ lệ video Topic/library ở hai hàng xóm thời gian | Phát hiện video thiếu từ khóa xuất hiện gần nhạc. Thử gap 15/30/60 phút; bỏ hàng xóm cùng ID/timestamp. Không khẳng định đồng phiên là cùng loại nội dung. |
| Nội dung | Unicode NFKC, OST/AMV, music video/symphony/orchestra, version/cover, artist–title shape | Tách family để thấy nhóm nào bổ sung thông tin. Sửa ranh giới OST dính chữ Nhật, nhưng tên ngắn/ngôn ngữ riêng vẫn thiếu bằng chứng. |
| Kênh | số video quan sát, tỷ lệ seed ở các video khác trong kênh, tỷ trọng lượt xem cá nhân của video | Kênh có thể hữu ích cho ca thiếu từ khóa. Loại chính video đang xét khi tính seed share; không gộp tất cả kênh thiếu ID vào một nhóm. |
| Phản chứng và thiếu dữ liệu | talk/reaction/tutorial, Shorts URL, missing timestamps/channel, conflict | Không chỉ cộng tín hiệu dương. Một title nhắc “music video reaction” có thể là nội dung nói chuyện. |
| Tương tác | log-count × dấu hiệu nội dung; recurrence × ngữ cảnh | Kiểm tra liệu kết hợp có tốt hơn mỗi feature riêng lẻ; chưa đặt trọng số. |

Metadata bổ sung là bước sau khảo sát: category, description/tags, track/artist và đặc điểm định dạng, lưu cache và nguồn. Không dùng category Gaming/Entertainment hoặc thời lượng đơn lẻ để kết luận. Chưa chạy crawler toàn bộ lịch sử.

## 4. Insight quan sát được trên dữ liệu hiện tại

| Quan sát | Ý nghĩa thực tế |
| --- | --- |
| 273 video Còn lại có ≥3 lượt xem; 268 có ≥3 ngày xem | Hành vi quay lại nhiều ngày là feature khả dụng và đáng ưu tiên audit; chưa thể gọi 268 video là nhạc. |
| 207/273 video xem lặp không khớp cả bộ tín hiệu nội dung đang thử | Chỉ thêm regex sẽ còn khoảng trống lớn. Cần ngữ cảnh/kênh hoặc metadata cho nhóm này. |
| 118 video seed Topic/library chỉ có 1 lượt xem | Không dùng count≥3 làm điều kiện bắt buộc. Seed là proxy bằng chứng, không phải ground truth. |
| Tín hiệu nội dung hiện có khớp 224 video bên Còn lại; các family bổ sung tìm thêm 48, hợp thành 272 | Đây là độ phủ từ khóa, không phải “tìm thêm 48 bài nhạc”. Con số 224 gồm cả ca conflict nên khác 218 có auto_reason=music_hint. |
| 7 ca bên Còn lại đồng thời có dấu hiệu nội dung và talk | Cần mẫu phản ví dụ khi nâng tín hiệu nội dung thành quyết định chọn. |
| Ngưỡng phiên 15/30/60 phút cho 690/473/324 phiên; đều có 377 video xuất hiện trong ≥3 phiên | Số phiên nhạy với giả định; feature recurrence thô này ổn định trên snapshot, chưa chứng minh ngữ cảnh phiên phân loại tốt. |

Các nhóm trên có giao nhau, không cộng thành số bài nhạc mới. Không dùng non-seed/Còn lại làm lớp non-music để đo chất lượng.

## 5. Xem lại phương thức hiện tại

`rules-v1` tự chọn chủ yếu Topic/library; keyword/repeat chỉ tạo evidence. Notebook 01 thực ra đã có watch_days, span, concentration và nhiều tín hiệu nội dung, nhưng production chưa sử dụng chúng. Vì vậy vấn đề gồm cả **thiếu feature trong quyết định** và **chưa đánh giá giá trị của feature**, không chỉ thiếu vài từ trong regex.

Hướng đề xuất:

1. Giữ rules-v1 làm baseline, tạo bảng feature có nguồn, version và cờ missing.
2. Hợp nhiều nguồn để tìm ứng viên: seed, nội dung, recurrence, kênh/ngữ cảnh. Tất cả vẫn chỉ là video có trong lịch sử.
3. Phân biệt quyết định tự chọn với thứ tự ưu tiên duyệt. Có thể tăng khả năng tìm nhạc ở hàng chờ mà chưa tự chuyển mọi ứng viên sang Nhạc. Vẫn giữ giao diện hai nhóm.
4. So sánh trên cùng nhãn/split: content-only → thêm recurrence → thêm context/channel → thêm metadata. Dùng rule kết hợp làm baseline mới; chỉ thử logistic regression/cây nhỏ khi đã có đủ nhãn.
5. Model audio chỉ là phương án bổ sung nếu dữ liệu rẻ hơn chưa đủ; đo cả thời gian tải mẫu/inference và nhầm BGM. Không chọn model trước khi có ca thất bại cụ thể.

## 6. Kiểm chứng trước khi đổi bộ lọc

Notebook đã xuất **126 mẫu khám phá**, tối đa 3 video/kênh mỗi stratum, tránh 300 ID eval cũ và không đọc nhãn eval. Sample phủ lặp không keyword, nhạc có keyword nhưng xem một lần, conflict và thiếu bằng chứng. Sample này để tìm insight/tune, không ước lượng accuracy toàn thư viện. Các ca đã lộ nhãn trong hội thoại là regression/discovery, phải loại khỏi eval cuối nếu trùng.

Cần nhãn `music`, `non_music`, `uncertain`, `unavailable` ở **cấp video**. Giữ một tập kiểm tra cuối, không dùng nó để tạo feature nhãn kênh; thêm kiểm tra tách theo channel để phát hiện học thuộc uploader. Feature hồi cứu có thể dùng toàn export cho bài toán hiện tại; nếu dự đoán tương lai phải cắt theo thời gian.

Đo hai nhóm kết quả: precision/recall và confusion matrix cho auto-select; số nhạc tìm được trong K mục đầu và thao tác review cho hàng chờ. Báo mẫu số, độ bất định; không dùng sample thiên lệch làm tổng thể. Hiện chưa có nhãn đủ để công bố trọng số/ngưỡng hoặc xác suất “video lặp là nhạc”.

## 7. Tái lập

Mở notebook 03 bằng kernel `.venv`. Biến `AURALYTICA_EDA_DB` chọn SQLite đã import; `AURALYTICA_EDA_TIMEZONE` chọn múi giờ. `EVAL_FILES` cần trỏ đúng cohort đánh giá nếu thay export.

Notebook chạy thành công với nbclient, có kiểm tra tổng event, ID duy nhất, tỷ lệ hợp lệ, Unicode và sample không trùng eval. Notebook nguồn không chứa output cá nhân. Output nằm dưới `artifacts/notebook-runs/03_music_features/<snapshot>/<feature-version>/`; phiên bản có hash code để không trộn nhãn giữa feature khác nhau. Chạy lại không ghi đè CSV review đã tồn tại.

Chưa sửa classifier hoặc chuyển bất kỳ video nào trong database trong nghiên cứu này. Bước cần làm tiếp là review mẫu và kiểm chứng giá trị feature trước khi triển khai cách quyết định mới.
