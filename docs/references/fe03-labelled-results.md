# FE03 — Kết quả sau nhãn người dùng, 2026-09-18

Đã nhập `artifacts/fe03-review-labels.csv`: **18 ID hợp lệ, 16 music + 2 non_music**, không trùng ID, cùng source hash và thuộc cohort cố định. Ghép với 5 ca nhạc đã xác nhận trước đó thành **23 nhãn: 21 music + 2 non_music**, còn 47/70 chưa có nhãn. Nhãn loại ở đây nghĩa là ngoài mục tiêu tải của người dùng; hai ca reel vẫn chứa âm nhạc.

[Summary](../../artifacts/notebook-runs/05_residual/20260918T120720595779Z/summary.json) · [Review mới](../../artifacts/notebook-runs/05_residual/20260918T120720595779Z/review.html) · [Log ca sai](../../artifacts/notebook-runs/05_residual/20260918T120720595779Z/classification_errors.csv) · [Toàn bộ dự đoán có nhãn](../../artifacts/notebook-runs/05_residual/20260918T120720595779Z/labelled_prediction_audit.csv).

## So sánh trên đúng 23 video đã gán nhãn

| Giả thuyết | Nhạc tìm được / 21 | Nhạc bỏ sót | Nhận nhầm / 2 ca loại |
| --- | ---: | ---: | ---: |
| Baseline rules-v1 | 4 | 17 | 0 |
| Seed + metadata mạnh | 15 | 6 | 0 |
| Thêm UGC + nội dung | 17 | 4 | 2 |
| Thêm UGC + xem lại ≥3 ngày | 20 | 1 | 0 |
| Thêm UGC + (nội dung hoặc xem lại ≥3 ngày) | 20 | 1 | 2 |
| Chỉ xem lại ≥3 ngày, đối chứng | 16 | 5 | 0 |

Các con số chỉ mô tả discovery cohort người dùng đã duyệt, **không phải accuracy tổng thể hoặc holdout**. Chỉ hai ca non_music đều là reel, chưa kiểm chứng đủ podcast, BGM trong video nói chuyện hoặc video giải trí lặp nhiều lần. Không suy ra bộ lọc không nhận nhầm từ hai ca này. `submitted_labels_evaluation.json` giữ kết quả riêng 18 nhãn mới: nhánh recurrence tìm 15/16 nhạc, 0/2 nhận nhầm, để tách khỏi 5 ca nhạc đã biết.

## Insight và quyết định

1. **UGC + từ khóa nhạc chưa đủ.** Hai reel người dùng loại đều có type UGC và từ khóa nhạc, không có marker Shorts hiện có. Category/type xác nhận ngữ cảnh âm nhạc nhưng không xác nhận video thuộc phạm vi tải. Không gán nhãn Shorts kỹ thuật chỉ từ ghi chú “reel”; đây là xác nhận loại cấp video.
2. **Xem lại nhiều ngày có ích khi kết hợp metadata.** Hai ca reel chỉ xem một ngày; nhánh recurrence tránh được chúng. Ngưỡng 2 và 3 ngày đều tìm 20/21; ngưỡng 5 hoặc 10 ngày chỉ còn 18/21. Chưa chọn 2 hay 3 ngày từ mẫu này, nhưng tăng ngưỡng lên 5 làm mất nhạc đã xác nhận. Chi tiết trong `labelled_sensitivity.json`.
3. **Tutorial là tín hiệu mơ hồ.** Ca nhạc duy nhất bị nhánh recurrence bỏ sót có tiêu đề Piano Tutorial/Piano Cover, UGC, xem lại 4 ngày; guard `tutorial` chặn trước khi xét recurrence. Cần phân biệt biểu diễn/Synthesia và bài hướng dẫn có lời nói. Chưa bỏ toàn bộ guard chỉ dựa một ca; đã đưa các ca tương tự và How to Play lên đầu review.
4. **Thời lượng không nên là điều kiện loại cứng.** Hai reel dài 15/47 giây nhưng có nhạc được xác nhận dài 78/83 giây. Điều này bác bỏ cách loại chung dưới 90 giây; không chứng minh ngưỡng 60 giây an toàn và không xác minh dạng Shorts.

Hướng tiếp theo: ưu tiên thử metadata mạnh + recurrence cho UGC; nội dung chỉ là tín hiệu hỗ trợ và đưa ca mơ hồ vào review. Cần kiểm chứng thêm các ca Tutorial/performance, short/reel, giải trí lặp và podcast/BGM trước khi đưa vào FE04. **Chưa sửa classifier ứng dụng hoặc nhóm video trong DB.** Tổng giả thuyết 279 trước đây vẫn giữ nguyên vì lượt này thêm nhãn, không đổi quy tắc.

## Truy vết và tiếp tục review

Mỗi lần chạy notebook 05 lưu thêm:

- `input_review_labels.csv`: bản sao nguyên byte CSV đã nộp, có SHA-256 trong summary; không phụ thuộc file download có bị thay thế sau này.
- `cumulative_review_labels.csv`: toàn bộ 70 dòng với nhãn hiện có, 23 đã xác định.
- `labelled_prediction_audit.csv`: 138 dòng (23 video × 6 giả thuyết), có ID, source hash, observation ID, nhãn, notes, tín hiệu và TP/FP/FN/TN.
- `classification_errors.csv`: các dòng FP/FN để xem nguyên nhân; không tự sửa nhãn.
- `labelled_sensitivity.json`, `submitted_labels_evaluation.json`: so ngưỡng trên nhãn thật và kết quả riêng của CSV mới.

[Review mới](../../artifacts/notebook-runs/05_residual/20260918T120720595779Z/review.html) giữ 23 nhãn và đưa 12 ca chưa rõ lên đầu. Nếu xuất CSV từng phần ở lần tiếp theo, cấu hình notebook với cohort đã có nhãn này để không mất nhãn cũ:

```python
os.environ['AURALYTICA_FE03_COHORT'] = str(ROOT / 'artifacts/notebook-runs/05_residual/20260918T120720595779Z/cohort_audit.csv')
os.environ['AURALYTICA_FE03_LABELS'] = str(ROOT / 'artifacts/fe03-review-labels.csv')
```

Đặt các dòng này **trước khi gán biến FROZEN ở cell cấu hình**. Mỗi lần chạy tạo thư mục riêng. Nguồn notebook không lưu output cá nhân; artifacts được ignore. Không thu thập metadata hoặc audio mới trong lượt này.
