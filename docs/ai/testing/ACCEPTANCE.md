# T11 — Báo cáo nghiệm thu chức năng

> Báo cáo này giữ bằng chứng MVP cũ. CLI nghiệp vụ được nhắc trong các tiêu chí đã bị gỡ ở WFT08; nghiệm thu hiện hành nằm tại [web workflow](2026-09-20-feature-web-workflow.md).

Ngày kiểm chứng: **2026-09-10**. Kết quả: **AC01–AC08 đạt trong phạm vi MVP Linux, Takeout JSON**. [T12 quickstart/môi trường Python sạch](QUICKSTART.md) đã đạt; đây không phải cam kết phân loại đủ mọi video nhạc hoặc tải được mọi URL.

## Bằng chứng theo tiêu chí

| Tiêu chí | Kết quả và bằng chứng |
| --- | --- |
| AC01 — Import | `test_importer.py`/`test_web.py`: thiếu nguồn, HTML/JSON sai, nhiều nguồn, quảng cáo/non-video, Unicode. Import export local mới: 9.700 dòng → 9.401 lượt xem / 6.385 video, 41 quảng cáo, 258 non-video, 136 dòng thiếu kênh. |
| AC02 — Không tải trùng | Browser nghiệm thu: 6.402 sự kiện / 6.400 video; video lặp vẫn watch_count=3 nhưng chỉ một download item. Nhập lại qua CLI reused=true, giữ hai sửa tay. `test_batches.py` kiểm tra tạo đồng thời bằng nhiều tiến trình. |
| AC03 — Phân loại có thể sửa | `test_classification.py`: Topic/library, Shorts URL, podcast/conflict, nhãn kênh, ca thiếu từ khóa ở unknown; sửa tay thắng gợi ý. Browser chuyển cả hai chiều rồi reimport/restart vẫn giữ. Đây là đúng quy tắc đã chốt, chưa phải phép đo accuracy trên lịch sử cá nhân. |
| AC04 — Hai danh sách | 6 browser test: picker/drop, từng dòng/bulk, filter/page/reload, 6.400 video, thumbnail lỗi và thiếu kênh, desktop/mobile. Luồng lớn import + sửa hai chiều: 1,042 giây trên máy hiện tại, một lần đo; không đặt SLA. |
| AC05 — Tải toàn bộ | Browser lọc/tick một dòng vẫn snapshot 255 music; video chuyển ra rest không có file, video thêm tay có file. Mẫu thật qua CLI/worker/yt-dlp: Opus 1.430.465 byte, đúng ID trong tên file, ffprobe chỉ có audio, ffmpeg giải mã exit 0; adapter dùng bestaudio không chuyển mã. Lần sau skip=1. Tests batch/adapter kiểm tra không tạo worker/tải trùng và không nhận output sai ID/video stream. |
| AC06 — Khôi phục | Browser: một video giả lập unavailable, 254 video khác thành công → dừng và khởi động lại server → giữ partial → resume thành công. Xóa một file: batch mới completed=1/skipped=254, mtime của 254 file còn lại không đổi. Test worker bổ sung stop/partial/crash/file collision/disk-full và khóa giữ bởi child sau khi cha chết. |
| AC07 — CLI/web thống nhất | Cùng database: nhập và sửa trên web, CLI status/list thấy batch và watch_count; CLI reimport được web sử dụng sau reload. Controls tests kiểm chứng download/status/stop/resume subprocess và API cùng snapshot. |
| AC08 — Chạy local | Browser dùng HTTP loopback, input/state/audio ở thư mục local. Mẫu thật chạy bằng CLI hiện hành và yt-dlp không truyền API key, Spotify hoặc model audio. Host/Origin/upload limits được test; không đưa export cá nhân vào fixture trong repo. |

## Lệnh và kết quả

- `.venv/bin/python tests/manual/coverage_core.py`: **66 test OK, exit 0**; runner unittest toàn bộ core/API có trace.
- `.venv/bin/python -m unittest discover -s tests/browser -v`: **6 test OK, exit 0**, 14,671 giây toàn suite.
- `.venv/bin/python tests/manual/smoke_download.py artifacts/download-smoke/t09-worker/input artifacts/acceptance-runs/t11-network`: **exit 0**. Chỉ một video thật; thư mục work phải chưa tồn tại để tránh lấy nhầm bằng chứng cũ.
- `.venv/bin/auralytica import 'artifacts/YouTube and YouTube Music' --database artifacts/acceptance-runs/t11-takeout.sqlite3`: hai lần **exit 0**, lần hai reused=true, giữ import_id=1 và thống kê.
- `node --check src/auralytica/static/app.js` và `git diff --check`: **exit 0**.

[Browser report local](../../../artifacts/acceptance-runs/t11-browser.json) · [Audio report local](../../../artifacts/acceptance-runs/t11-network/validation.json). Dữ liệu đầu vào, SQLite, audio và status chi tiết chỉ ở artifacts đã ignore. Đường dẫn artifact chỉ dùng được trên máy có dữ liệu.

## Coverage và giới hạn

Dùng `trace` chuẩn Python vì môi trường chưa có package coverage. Runner thu dòng Python trong tiến trình chính và thread HTTP, xuất `.cover` dưới `artifacts/acceptance-runs/coverage`. Không thu subprocess CLI/yt-dlp, JS/browser hoặc các dòng import đã chạy trước tracer; **không diễn giải tỷ lệ này là tổng coverage dự án**. Các subprocess được kiểm chứng riêng qua kết quả tích hợp và mẫu mạng.

Sau rà khoảng trống, thêm test cho protocol downloader: stdout không phải JSON, message không phải object, structured error, exit 0 thiếu output và ID không hợp lệ. Tracer ghi downloader 80%, web 77%, controls 63%; phần controls còn thiếu gồm nhánh chạy ở subprocess. Không có ngưỡng coverage phần trăm đã chốt; dùng hành vi AC để nghiệm thu.

Chưa thử mất điện thật, rút mạng giữa video hoặc mọi nền tảng/browser. Dừng/crash/hết dung lượng được mô phỏng có kiểm soát; audio trong browser là fixture không phát được, bằng chứng phát audio đến từ mẫu mạng riêng. Chưa tải toàn bộ 255 gợi ý trong lịch sử cá nhân và chưa đo precision/recall. Không tái hiện lỗi sqlite3 cũ nên không tuyên bố đã sửa lỗi đó. Cảnh báo deprecation httpx của TestClient vẫn còn, không làm test thất bại.

Không phát hiện lỗi production mới trong T11. T12 đã hoàn tất sau mốc này; xem [báo cáo quickstart](QUICKSTART.md).
