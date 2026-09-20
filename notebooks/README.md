# Notebooks phát triển Auralytica

Phạm vi hiện hành nằm ở [requirements](../docs/ai/requirements/README.md); theo dõi việc triển khai tại [Project Dashboard](../PROJECT_DASHBOARD.md). Notebook là tài liệu nghiên cứu, không thể hiện tính năng đã có trong ứng dụng.

Notebook được đánh số theo giai đoạn; chỉ tạo notebook khi bắt đầu giai đoạn đó.

| Giai đoạn | Notebook / đầu ra |
| --- | --- |
| 01 — khảo sát dữ liệu | [`01_takeout_eda.ipynb`](01_takeout_eda.ipynb): kiểm tra Takeout, khám phá tiêu đề/kênh, xuất mẫu gán nhãn |
| 02 — thiết kế tín hiệu | [`02_classification_design.ipynb`](02_classification_design.ipynb): thiết kế content gate, audit sample v2 và mô phỏng hàng chờ |
| 03 — feature engineering | [`03_music_feature_engineering.ipynb`](03_music_feature_engineering.ipynb): recurrence, phiên/ngữ cảnh, nội dung/kênh và audit rules-v1; chưa huấn luyện/chốt ngưỡng |
| 04 — metadata YouTube Music | [`04_ytmusic_metadata_audit.ipynb`](04_ytmusic_metadata_audit.ipynb): đọc log mẫu 18 video offline, so player/queue, độ phủ giả thuyết và latency; chưa đổi classifier |
| 05 — đánh giá residual | [`05_residual_evaluation.ipynb`](05_residual_evaluation.ipynb): ghép feature với log FE02, so giả thuyết UGC/recurrence, tạo review và kiểm tra nhãn; chưa chốt ngưỡng |

## Chạy

Notebook 05: [kết quả sau 23 nhãn và cách giữ nhãn qua các lần review](../docs/references/fe03-labelled-results.md); [kết quả và giới hạn FE03](../docs/references/residual-evaluation.md). Chạy offline bằng kernel notebook hiện có; output mỗi lượt ở `artifacts/notebook-runs/05_residual/`. Mở `review.html` bằng trình duyệt, duyệt 12 dòng ưu tiên, chọn nhãn/ghi chú rồi bấm Xuất CSV nhãn đã sửa; đặt `AURALYTICA_FE03_LABELS` tới CSV đã xuất để đánh giá lại. Nút Xuất log chỉnh sửa lưu JSONL trước/sau từng lần sửa; bản nháp trình duyệt chưa tự nhập vào notebook. Vẫn có thể điền `priority_review.csv` trực tiếp. Metadata đã có trên đủ 70 ID của cohort cố định (18 cũ + 52 bổ sung được duyệt); cấu hình cohort bằng `AURALYTICA_FE03_COHORT`, không tự chọn lại mẫu sau enrichment. Test nghiên cứu chạy riêng bằng `.venv/bin/python -m unittest discover -s tests/research -v` và cần pandas trong group notebook.

Từ thư mục gốc repo:

```bash
uv sync --group notebook
uv run --group notebook jupyter lab notebooks/01_takeout_eda.ipynb
```

Notebook 02 đọc output của notebook 01 và `artifacts/notebook-runs/channel_labels.csv`. File channel labels lưu quyết định thủ công theo `channel_key`; không commit vì `artifacts/` bị ignore.

Chọn kernel của `.venv` nếu mở bằng VS Code. Sửa `TAKEOUT_DIR` ở cell cấu hình nếu dùng export khác; có thể chỉ tới thư mục Takeout hoặc thư mục `YouTube and YouTube Music`. Notebook 01 hỗ trợ **watch-history.json**; báo rõ nếu chỉ có HTML hoặc có nhiều file lịch sử để người dùng chọn chính xác. Notebook chạy phân tích offline, không gọi API, không tải metadata/audio/model.

Chạy kiểm chứng toàn bộ notebook, lưu kết quả riêng:

```bash
uv run --group notebook python - <<'PY'
from pathlib import Path
import nbformat
from nbclient import NotebookClient
root = Path.cwd()
path = root / 'notebooks/01_takeout_eda.ipynb'
nb = nbformat.read(path, as_version=4)
NotebookClient(nb, timeout=180, kernel_name='python3', resources={'metadata': {'path': str(root)}}).execute()
out = root / 'artifacts/notebook-runs/01_takeout_eda.executed.ipynb'
out.parent.mkdir(parents=True, exist_ok=True)
nbformat.write(nb, out)
print(out)
PY
```

## Dữ liệu và gán nhãn

- Notebook nguồn không chứa output cá nhân. Output đã chạy và CSV/biểu đồ nằm trong `artifacts/`, vốn được git-ignore. Trước khi commit notebook đã mở/chạy, dùng **Clear All Outputs** và lưu lại.
- CSV mẫu hiện tại nằm trong `artifacts/notebook-runs/01_takeout_eda/<source-hash>/signals-v2/`. Thư mục gắn với nội dung file đầu vào và phiên bản phân tích để tránh trộn các export hoặc ghi đè mẫu cũ.
- Điền `manual_label` bằng `music`, `non_music`, `uncertain` hoặc `unavailable`; ghi lý do vào `notes`. Chạy lại không ghi đè các CSV mẫu đã tồn tại.
- `discovery_review.csv` để khám phá/tinh chỉnh. `random_review.csv` là mẫu ngẫu nhiên riêng để đánh giá sau khi chốt quy tắc; không dùng nhãn của mẫu này để điều chỉnh quy tắc.
- Nhãn `music`: nội dung chính là âm nhạc (AMV, cover, OST, remix, live biểu diễn, BGM độc lập…). Video nói chuyện/game có nhạc nền là `non_music`. Khi chưa kiểm tra được thì giữ `uncertain`/`unavailable`.
- Trường `signal_*` chỉ biểu thị khớp giả thuyết văn bản; **không phải nhãn, điểm xác suất hay kết luận phân loại**. Category không phải điều kiện bắt buộc để nhận nhạc.

## Revision signals-v2

- Bổ sung tên kênh Topic, ID trong music library (nếu có), VEVO, phiên bản slowed/reverb/lofi, nhạc cụ, từ vựng âm nhạc đa hệ chữ và liên kết tên nghệ sĩ với Topic.
- Tách số lượt xem khỏi số timestamp và số ngày xem lại; đối chiếu với ngữ cảnh podcast, tutorial và behind-the-scenes. Bảng tương quan Topic/library không phải xác suất video là nhạc.
- Tách ký tự hệ chữ chỉ nằm ở hashtag (ví dụ `#fypシ`) khỏi phần tiêu đề chính; đây là đặc trưng chọn mẫu, không phải tín hiệu nhạc.
- Sample discovery giới hạn số video mỗi kênh, hiển thị lý do chọn và nhóm cần duyệt. Giữ nguyên 300 ID random của v1 với cùng source/seed/cỡ mẫu; bảng khám phá không hiển thị các ID holdout này.
- Giữ nguyên CSV v1; khi tạo v2 lần đầu chỉ mang nhãn và notes cùng cohort theo ID. Các số liệu feature luôn tính lại từ dữ liệu, không biến Topic/library thành `manual_label`.
- `legacy_discovery_audit.csv` đối chiếu sample cũ; `feature_coverage.csv`, `repeat_analysis.csv` và `channel_evidence.csv` cung cấp bằng chứng cho thiết kế quy tắc. Nếu thay đổi cách lấy mẫu, tăng `EDA_VERSION` để bảo toàn nhãn đã nhập.

## Giai đoạn 02: content gate

Thứ tự quyết định được thử nghiệm là: Shorts → kênh/video đã xác nhận là giải trí hoặc podcast → nguồn nhạc chắc chắn → tín hiệu nhạc hỗ trợ → hàng chờ. Video có marker rõ như `#shorts` bị loại trong pilot nhưng vẫn lưu lý do `proxy`; implementation cần bổ sung `confirmed_is_short` bằng metadata/probe vì YouTube Data API không có trường `isShort` công khai. Category `Entertainment` không được dùng làm hard exclusion vì nhiều video nhạc cũng có thể nằm trong category này.

Phần matching Spotify/ISRC trong notebook 02 đã được bỏ khỏi phạm vi sau khi rà lại yêu cầu. MVP tải audio của chính video YouTube được chọn; không cần tìm bản tương ứng trong catalog khác. Giữ notebook để truy vết nghiên cứu, không triển khai bước matching đó.

Không chia sẻ CSV/output notebook khi chưa rà soát dữ liệu lịch sử cá nhân.

## Notebook 04 — kiểm chứng YouTube Music

[Báo cáo và thiết kế log](../docs/references/youtube-music-identification.md). Notebook đọc log của pilot đã được người dùng cho phép, **không gọi mạng hoặc sửa DB**. Mặc định đọc `artifacts/ytmusic-pilot/20260911T041238Z`; đổi bằng `AURALYTICA_YTM_RUN` tới một folder có manifest/events/summary cùng schema. Log raw không được commit nên máy mới cần có bộ log local trước khi chạy.

Output ở `artifacts/notebook-runs/04_ytmusic_audit/<run>/<analysis>/`: bảng từng video, giả thuyết khớp, độ phủ, latency và review. Mỗi lần chạy tạo folder mới, không ghi đè nhãn đã điền. Chỉ 5 nhãn người dùng xác nhận trước pilot được điền sẵn; Topic/library/queue/type không biến thành nhãn thật. Không suy diễn độ phủ mẫu thành accuracy toàn lịch sử.

## Notebook 03 — nghiên cứu 2026-09-11

[Tổng hợp phương pháp và insight](../docs/references/music-feature-engineering.md). Đọc DB ứng dụng ở chế độ read-only; mặc định `~/.local/share/auralytica/library.sqlite3`, đổi bằng `AURALYTICA_EDA_DB`. Ngày tính theo `AURALYTICA_EDA_TIMEZONE` (mặc định Asia/Bangkok). Chạy bằng kernel .venv có group notebook.

Output gồm video_features.csv, summary.json, biểu đồ và discovery_review.csv, dưới artifacts theo hash dữ liệu + phiên bản feature. Notebook nguồn không chứa lịch sử cá nhân. Giữ eval cũ tách sample khám phá; khi dùng export khác, kiểm tra lại EVAL_FILES. Số khớp feature là độ phủ, không phải accuracy. Chưa thay rule hoặc nhãn app.
