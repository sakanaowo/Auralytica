# FE03 — Đánh giá UGC và phần còn lại

**Kết quả mới nhất 2026-09-18:** đã nhập CSV người dùng, có 23 nhãn và log ca sai; xem [báo cáo có nhãn](fe03-labelled-results.md). Các số liệu bên dưới ghi giai đoạn trước khi nhập CSV.

Ngày **2026-09-13**. Đã ghép feature snapshot notebook 03 với log collector FE02, so giả thuyết và tạo bộ review. **Chưa chốt ngưỡng hoặc đổi classifier ứng dụng.**

[Notebook 05](../../notebooks/05_residual_evaluation.ipynb) · [Bản đã chạy](../../artifacts/notebook-runs/05_residual_evaluation.executed.ipynb) · [Summary local](../../artifacts/notebook-runs/05_residual/20260913T100651571887Z/summary.json).

## Dữ liệu và kết quả

Snapshot có **6.385 video**, nhưng metadata đã được thu thập cho **70 ID** (18 cũ + 52 mới được cho phép). 6.315 video chưa được truy vấn, không được coi là thiếu musicVideoType hoặc không phải nhạc. Ghép theo đúng ID và kiểm tra source hash giữa feature và run; giữ observation ID/fetched_at và hash các đầu vào/code trong kết quả. Phân tích này dùng snapshot nghiên cứu, không đọc trạng thái DB đang chạy.

| Giả thuyết mô phỏng | Tổng khớp với dữ liệu đã có | Trong 5 ca nhạc bị bỏ sót đã được xác nhận |
| --- | ---: | ---: |
| Baseline rules-v1 | 255 | 0 |
| Seed + metadata mạnh | 269 | 2 |
| Thêm UGC + tín hiệu nội dung | 276 | 4 |
| Thêm UGC + quay lại nhiều ngày | 274 | 5 |
| Thêm UGC + (nội dung hoặc quay lại) | 279 | 5 |

Đây là **độ phủ giả thuyết**, không phải số nhạc đã xác minh trên toàn lịch sử hay recall tổng thể. Seed vẫn là Topic/library proxy. Các nhánh mới giữ ca có dấu hiệu talk/Shorts/policy kênh ở review; không sử dụng queue UGC, category Gaming/Entertainment, thời lượng ngắn hoặc UNPLAYABLE làm nhãn non-music.

Một ca UGC không có từ khóa nhạc được tìm lại nhờ xem lại qua nhiều ngày; ca UGC thuộc Gaming vẫn được giữ khi có tín hiệu nhạc. Đây là hai lý do thử phối hợp nội dung và recurrence thay vì bắt buộc từ khóa/category Music.

## Vì sao chưa chọn ngưỡng

| Ngưỡng ngày quay lại | UGC kết hợp + strong khớp | Chỉ recurrence khớp | Recurrence khớp trong kênh người dùng yêu cầu loại |
| --- | ---: | ---: | ---: |
| 2 | 279 | 624 | 75 |
| 3 | 279 | 371 | 9 |
| 5 | 277 | 227 | 0 |
| 10 | 277 | 103 | 0 |

Tăng từ 3 lên 5 ngày làm giảm 2 ứng viên chưa gán nhãn. Cả bốn ngưỡng cùng tìm đủ 5 ca đã biết: mẫu đang thiên về nhạc được xem rất nhiều, nên không phân biệt được ngưỡng nào tốt. Không suy ra 5 ngày là ngưỡng an toàn chỉ vì không gặp kênh bị loại trong snapshot. Policy kênh là thông tin người dùng cung cấp, không phải bộ nhãn video độc lập.

Hiện chỉ có **5 nhãn music, chưa có nhãn non_music độc lập ở cấp video** trong cohort. Bộ đánh giá không xuất precision/recall khi thiếu một lớp; hàng trống/uncertain/unavailable không bị đổi thành non_music. Khi bổ sung nhãn, kết quả chỉ mô tả phần đã gán nhãn trong discovery cohort; vẫn cần holdout độc lập trước khi kết luận chất lượng tổng thể.

## Bộ review và khoảng trống

Đã tạo **70 video: 18 pilot cũ + 52 ca mới**, trong đó 65 chưa có nhãn. Có [12 mẫu ưu tiên](../../artifacts/notebook-runs/05_residual/20260913T100651571887Z/priority_review.csv) để duyệt trước, [review CSV đầy đủ](../../artifacts/notebook-runs/05_residual/20260913T100651571887Z/review.csv) và [trang gán nhãn offline](../../artifacts/notebook-runs/05_residual/20260913T100651571887Z/review.html). Trang có chọn nhãn, ghi chú, lưu bản nháp và xuất CSV/log; không tự tải ảnh/media.

Mẫu mới phân tầng: từ khóa nhạc kèm Shorts, talk + nhạc, lặp ở kênh bị loại, lặp không từ khóa, nhạc có từ khóa chỉ xem một lần, lặp 2–4 ngày, biểu diễn chưa có metadata, ngữ cảnh BGM và phần còn lại. Mỗi stratum tối đa 2 video/kênh, lấy theo hash cố định. Giới hạn này áp dụng cho mẫu mới từng stratum; 18 pilot cũ giữ nguyên.

- 7 video khớp từ khóa nhạc + marker Shorts; 9 video khớp cả talk và tín hiệu nhạc. Đây là ca cần duyệt, chưa xác minh loại video.
- Không có ca khớp token podcast/talkshow rõ trong snapshot; không thay bằng gameplay rồi tuyên bố đã kiểm chứng podcast. Test tổng hợp có podcast chỉ kiểm tra logic guard.
- Không có ca cùng một ngày nhưng xem ≥3 lần theo stratum đang thử. Ghi lại strata rỗng thay vì bù bằng loại video khác.
- Chỉ đọc ID của holdout 300 cũ. Mẫu mới không trùng holdout; trong lượt này cả cohort cũng không trùng. `eval_role=discovery_only` và `holdout_exclusions.csv` ghi vai trò rõ ràng cho lần chạy khác.
- Nhãn kênh, Topic/library và output YTM không điền sẵn manual_label. Chỉ 5 nhãn có trước pilot được giữ; người dùng có thể sửa chúng trong CSV nếu cần.

Đã thu thập đúng [manifest 52 ID đã duyệt](../../artifacts/notebook-runs/05_residual/20260913T080143642628Z/metadata_request_manifest.json). Manifest gốc giữ nguyên trạng thái lúc chuẩn bị để bảo toàn provenance; [summary thực thi](../../artifacts/metadata-smoke/fe03-20260913T082334Z/summary.json) ghi **52/52 done, 52 attempts, 29,65 giây**, HTTP 200, không tải audio. Log mới: [new52.jsonl](../../artifacts/metadata-smoke/fe03-20260913T082334Z/new52.jsonl); log hợp nhất: [combined70.jsonl](../../artifacts/metadata-smoke/fe03-20260913T082334Z/combined70.jsonl). Các row video trong bản sao DB giữ nguyên.

## Chạy lại và kiểm chứng

Notebook chỉ dùng dữ liệu local. Các biến cấu hình: `AURALYTICA_FE03_FEATURES` (folder output notebook 03), `AURALYTICA_FE03_LOG` (JSONL export FE02), `AURALYTICA_FE03_LABELS` (CSV review đã điền). Các đường dẫn pilot/holdout/channel cũng cần phù hợp khi đổi snapshot; notebook từ chối ghép source hash khác.

Mỗi lần chạy tạo folder output mới, không ghi đè review cũ. CSV nhãn phải có video_id/source_hash/manual_label; từ chối ID ngoài cohort, ID trùng, snapshot sai hoặc label không thuộc music/non_music/uncertain/unavailable. `cohort_audit.csv` giữ feature, metadata và từng mask; `all_video_hypotheses.csv`, `coverage.csv`, `sensitivity.csv`, `strata.csv`, `summary.json` cho phép truy lại kết quả.

**Notebook chạy đủ 4 cell code (8 cell tổng cộng), 7 test nghiên cứu đạt** (`.venv/bin/python -m unittest discover -s tests/research -v`). Kiểm tra synthetic gồm UGC không từ khóa, nhạc category Gaming, podcast/gameplay/Shorts, missing/mismatch/error, thiếu watch_days, UNPLAYABLE, metric khi thiếu nhãn và validation CSV. Chúng kiểm tra tính đúng của phép tính/guard, không chứng minh accuracy trên video thật.

FE03 đã lấy metadata cho toàn bộ cohort 70. Phần còn mở: gán nhãn ưu tiên, bổ sung podcast/BGM/music Shorts thật, rồi so các giả thuyết trên nhãn độc lập. FE04 chỉ nối cách quyết định đã có đủ bằng chứng vào hai bảng.


## Insight sau khi bổ sung 52 video

- Type mới: **12 OMV, 1 ATV, 14 UGC, 25 không có type**. Đây là nhãn nền tảng, không phải 27 nhãn music-primary đã được người dùng kiểm tra.
- Trong 52 ca, **5 ca có type nhạc nhưng UNPLAYABLE**; không thể dùng playability làm nhãn non-music. Không gọi yt-dlp để kiểm tra khả năng tải ở bước này.
- Mô phỏng kết hợp đưa tổng ứng viên từ baseline 255 lên **279 (+24)**; chỉ 5 trong các ca bổ sung đã được xác nhận trước đó, 19 ca còn cần duyệt. Tổng này dùng metadata mới ở 70 ID, không phải ước lượng mọi nhạc trong 6.385 video.
- Có OMV mang tiêu đề hướng dẫn chơi nhạc. Đồng thời nhiều UGC piano/Synthesia có chữ Tutorial bị guard giữ lại: cần xem có lời giải thích hay chỉ biểu diễn/hiển thị nốt. Không tự đổi nhãn từ tiêu đề.
- 12 ca ưu tiên mới tập trung vào type có nhưng bị guard, category ngoài Music, UGC chỉ dựa recurrence, OMV có tiêu đề hướng dẫn và type nhạc nhưng UNPLAYABLE. File lý do ưu tiên nằm riêng `priority_reasons.csv` để tránh đưa dự đoán vào CSV gán nhãn.

Notebook mặc định dùng log hợp nhất và **cohort cố định** qua `AURALYTICA_FE03_COHORT`; xác minh cùng source hash, ID duy nhất, giữ nhãn/notes/sample_reason. Không chọn lại cohort từ các nhóm “chưa có metadata” sau enrichment. Bản review cuối không còn ID nào chưa được truy vấn; manifest yêu cầu bổ sung mới có count=0. Lượt nghiên cứu trước giữ nguyên để so sánh.


## Gán nhãn trực tiếp trong trình duyệt

Mở `review.html` bằng trình duyệt, duyệt 12 dòng đầu trước. Chọn **Nhạc / Không phải nhạc / Chưa rõ / Không mở được** và ghi căn cứ vào ô ghi chú. Giữ nhãn chưa rõ nếu chỉ có tiêu đề hoặc không đủ bằng chứng; không dùng nhãn nền tảng thay xác nhận nội dung.

Bản nháp tự lưu trong trình duyệt theo hash của bộ review ban đầu, tách khỏi bộ khác. Nếu lưu trữ bị chặn, trang thông báo và vẫn xuất được kết quả đang nhập. Nhấn **Xuất CSV nhãn đã sửa** để lưu `fe03-review-labels.csv`; file chỉ có các dòng đã sửa, notebook giữ nguyên nhãn/notes của dòng khác. Không xóa nhãn cũ bằng ô trống; chọn Chưa rõ nếu cần rút lại kết luận. Nhấn **Xuất log chỉnh sửa** để lưu `fe03-review-events.jsonl`: video ID, source hash, thời gian trình duyệt, giá trị nhãn/notes trước và sau. Đây là log review local do người dùng xuất, không phải log DB hoặc lịch sử chống sửa đổi.

Đặt file CSV đã xuất vào `artifacts/` và cấu hình `AURALYTICA_FE03_LABELS` tới file trước khi chạy notebook 05. Trong VS Code có thể thêm vào cell cấu hình, trước cell đọc nhãn:

```python
os.environ['AURALYTICA_FE03_LABELS'] = str(ROOT / 'artifacts/fe03-review-labels.csv')
```

Nhãn mới chỉ phục vụ nghiên cứu; trang không sửa hai nhóm trong ứng dụng. Bản nháp trình duyệt không tự nhập vào notebook, cần xuất CSV. Đầu ra mới vẫn tạo thư mục riêng và kiểm tra ID/source hash. Template HTML được hash trong summary để truy được phiên bản giao diện.

Kiểm chứng bước giao diện: **7 test nghiên cứu + 2 test Chromium đạt**, notebook chạy lại đủ 4 cell code. Browser kiểm tra nhãn/notes qua reload, CSV → `merge_labels`, log trước/sau, escape tiêu đề, không gọi mạng tự động, cô lập bản nháp, localStorage bị chặn và màn hình 390px. Chạy riêng browser bằng `.venv/bin/python -m unittest discover -s tests/research_browser -v` (cần group notebook/browser và Chromium).
