# FE04 — Preview phân loại từ dữ liệu local

Cập nhật 2026-09-18: **đã có preview và apply CLI; đã áp dụng 18 thay đổi vào live DB**. Các phần kết quả preview bên dưới là trạng thái trước apply; xem mục Áp dụng cuối tài liệu. `classification-preview` mở SQLite `mode=ro` và đọc trong một transaction; không migrate schema, không gọi mạng, không sửa review/download/audit.

```sh
uv run --no-sync auralytica classification-preview \
  --labels artifacts/notebook-runs/05_residual/20260918T120720595779Z/cumulative_review_labels.csv \
  --metadata-log artifacts/metadata-smoke/fe03-20260913T082334Z/combined70.jsonl \
  --output artifacts/my-classification-preview.json
```

Output cần là file chưa tồn tại. Có thể truyền `--database` để dùng DB khác. Runtime dùng thư viện chuẩn, không cần pandas/notebook. CSV cần video_id/source_hash/manual_label; chấp nhận notes. Từ chối ID trùng/ngoài active import, snapshot sai và nhãn không hợp lệ. Các run_manifest trong JSONL phải khớp source hash. Chỉ xét observation trực tiếp get_song.videoDetails.musicVideoType với requested_id/returned_id đúng video; lấy observation mới nhất theo fetched_at. Không lấy type từ queue. Đây là preview dựa trên observation đã lưu, không khẳng định metadata còn mới hoặc video tải được; không tự refresh/áp TTL cache.

## Thứ tự quyết định

1. Giữ mọi `user_group` hiện có. Nếu CSV xác nhận khác nhóm sửa tay, ghi conflict; không ghi đè.
2. Nhãn xác định music/non_music trong CSV đề xuất nhóm tương ứng. Nhãn uncertain/unavailable giữ nguyên nhóm và yêu cầu review.
3. Giữ quyết định kênh hiện có; các ca Shorts/talk/Tutorial được giữ để review. Với nhãn nhạc đã xác nhận ở bước 2, Tutorial không thể ghi đè nhãn đó.
4. Metadata ATV/OMV/OFFICIAL_SOURCE_MUSIC đề xuất Nhạc; UGC cần ≥3 ngày xem phân biệt trong active import. Ngưỡng 3 là cấu hình thử nghiệm của preview, chưa chốt chất lượng production.
5. Lyrics/Karaoke/MV/official audio/visualizer thêm lý do gợi ý; từ khóa hoặc lượt xem đơn lẻ không tự đưa sang Nhạc. Thiếu metadata giữ nhóm hiện tại.

Không tự hạ các video đang ở Nhạc chỉ vì metadata thiếu. CSV non_music là xác nhận ngoài phạm vi tải, không phải kết luận rằng nội dung không có âm nhạc. Chính sách reel hiện có được giữ; lượt này không nghiên cứu thêm reel.

## Kết quả trên DB hiện tại

[JSON đầy đủ](../../../artifacts/filter-audits/fe04-preview-20260918.json) · [Bảng 18 thay đổi](../../../artifacts/filter-audits/fe04-preview-20260918.html).

- Hiện tại: **260 Nhạc / 6.125 Còn lại**.
- Đề xuất: **278 Nhạc / 6.107 Còn lại**, 18 chuyển sang Nhạc, 0 xung đột sửa tay.
- 16 thay đổi dựa trên nhãn người dùng, 2 từ metadata mạnh. Trong 250 dòng được kiểm tra trước đó có 13 thay đổi, gồm đủ 12 ca nhạc đã xác nhận còn ở Còn lại.
- JSON có SHA-256 đầu vào, source hash, import ID, thời điểm tạo, nhóm trước/sau, nhãn/notes, số ngày xem, observation ID/run ID/fetched_at và lý do cho toàn bộ 6.385 video.

Đây là preview có phạm vi metadata 70 ID; không suy ra đã nhận diện mọi nhạc. Chưa áp dụng vào app. Bước tiếp theo là apply có kiểm tra snapshot chưa đổi, transaction/khóa download batch, giữ override và log quyết định; sau đó nối giải thích vào web. Thu thập thêm 232 ID là việc riêng, chưa thực hiện.

## Kiểm chứng

`tests/test_classification_preview.py`: 5 test SQLite/CLI thật; bước red thiếu module rồi green. Kiểm tra nhãn/snapshot/ID, type sai ID không được nhận, Tutorial/podcast giữ review, nhãn mạnh hơn guard, conflict giữ sửa tay, số lần xem khác số ngày, uncertain không tự nhận, xuất không ghi đè và DB không thay đổi. Core/API trước khi thêm test cuối: 86 test đạt; test cuối bổ sung chạy suite preview 5/5 đạt. Không đổi UI nên không chạy lại Chromium. Không cài/chạy AI DevKit qua mạng trong lượt này sau lần auto-review từ chối trước đó.

Kiểm chứng cuối cùng: `.venv/bin/python -m unittest discover -s tests -q` → **87 tests OK**, exit 0. Đối chiếu artifact xác nhận đủ 12 ca nhạc đã biết trong 5 trang đầu được đề xuất chuyển; live DB vẫn 260 Nhạc/6.125 Còn lại.


## Áp dụng đã triển khai và chạy thành công

```sh
uv run --no-sync auralytica classification-apply \
  --preview artifacts/filter-audits/fe04-apply-preview-v2.json \
  --labels artifacts/notebook-runs/05_residual/20260918T120720595779Z/cumulative_review_labels.csv \
  --metadata-log artifacts/metadata-smoke/fe03-20260913T082334Z/combined70.jsonl
```

Lệnh này đã chạy; không cần chạy lại trên preview cũ. Preview v2 có state_sha256 của video/sự kiện/kênh thuộc active import. Apply mở BEGIN IMMEDIATE, chặn batch queued/running, tính lại toàn bộ preview từ input và từ chối khi nội dung/snapshot/hash/version khác. Preview v1 cần tạo lại. Lỗi bất kỳ, kể cả ghi audit, rollback toàn bộ. Chạy lại cùng preview sau khi dữ liệu đã đổi bị từ chối.

16 nhãn đã xác nhận được lưu thành user_group bằng review service; hai đề xuất metadata được lưu vào auto_group cùng evidence đã kiểm tra và source hash trong metadata_json. `rules-v2-applied-metadata` đọc evidence đã áp dụng để giữ kết quả qua classify/reimport cùng source; source khác không dùng lại evidence đó. Sửa tay luôn ưu tiên. Không lưu suy đoán tự động thành nhãn người dùng. Giao diện có tên lý do metadata mạnh/UGC recurrence.

**Live DB sau apply: 278 Nhạc / 6.107 Còn lại.** Run `f2676b9955a44c75a45cbd71a00f09d5`; [log](../../../artifacts/filter-audits/fe04-applied-events.jsonl), [kiểm chứng](../../../artifacts/filter-audits/fe04-apply-verification.json), [backup trước apply](../../../artifacts/filter-audits/before-fe04-apply.sqlite3). Đối chiếu trước/sau: đúng 18 video thay đổi, mọi sửa tay cũ giữ nguyên; imports/events/settings/channel decisions/download batches/items/cache không đổi.

**90 test core/API đạt**, gồm stale/tampered preview, khóa batch, rollback khi audit lỗi, giữ manual và metadata qua classify, CLI apply/lặp lại bị từ chối. `node --check` đạt cho app.js. Chưa kiểm thử Chromium lượt này vì UI chỉ thêm hai nhãn lý do. Không gọi metadata mới; bước tiếp theo có thể mở rộng metadata cho phần chưa có dữ liệu, không coi toàn bộ FE04/độ chính xác phân loại đã nghiệm thu.
