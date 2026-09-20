# WFT09 — Nghiệm thu và review cuối

Ngày kiểm chứng: **2026-09-20**. Kết luận: **đạt trong phạm vi Linux + Google Takeout JSON đã chốt; không còn finding chặn phát hành**.

## Kết quả kiểm chứng

| Phạm vi | Lệnh / bằng chứng | Kết quả |
| --- | --- | --- |
| Core, API, migration, worker | `.venv/bin/python -m unittest discover -s tests -q` | **116 tests OK**, 4,182 giây, exit 0 |
| Web Chromium | `.venv/bin/python -m unittest discover -s tests/browser -v` | **10 tests OK**, 27,193 giây, exit 0 |
| Nghiên cứu offline | `.venv/bin/python -m unittest discover -s tests/research -v` | **7 tests OK**, exit 0 |
| Trang review nghiên cứu | `.venv/bin/python -m unittest discover -s tests/research_browser -v` | **2 tests OK**, exit 0 |
| Static/package/docs | `node --check` 5 module; `compileall`; `git diff --check`; `npx ai-devkit@latest lint --feature web-workflow`; `uv build --wheel` | Tất cả exit 0; wheel `auralytica-0.1.0-py3-none-any.whl` tạo thành công |
| Gói cài không editable | `pip install --no-deps <wheel>` rồi `auralytica --help` trong venv mới | Exit 0; help chỉ có `--port`, `--database`, `--no-browser` |

TestClient còn phát `StarletteDeprecationWarning` về httpx; đây không phải test failure. Core/Chromium cần chạy ngoài filesystem/network sandbox vì test dùng loopback socket, nhiều process và uv cache.

## Migration và khôi phục

`test_database_copy_preserves_manual_download_selection_and_rejects_old_code` tạo database fixture, sao lưu bằng SQLite backup API rồi mở bản sao. Sau reopen vẫn giữ:

- `videos.user_group=music` do người dùng chốt;
- download item `completed`, đường dẫn và kích thước file;
- `download_selections.keep=0`, revision 7.

Test sau đó mô phỏng binary cũ chỉ biết schema v3. Binary này từ chối schema v4 trước khi ghi; `user_version`, nhãn và selection vẫn nguyên. Migration v1 → v4 và rollback DDL lỗi tiếp tục được test riêng. Quy trình quay lại phiên bản cũ là khôi phục bản backup tương ứng; ứng dụng không tự hạ schema.

## Quy mô và chất lượng matching

Chromium fixture **7.500 video** trên Linux/Chromium 151.0.7922.34:

- import + filter + move: **1,596 giây**;
- Explore summary: **16,0 ms**;
- trang Nhạc 50 hàng: **49,7 ms**;
- tìm một video trong Còn lại: **36,8 ms**;
- không có page error và UI không render toàn bộ 7.500 hàng.

Dedup fixture 7.500 video/3.750 cặp mất **0,137 giây**, trả 20 nhóm/trang. Đây là benchmark local một lượt, không phải SLA.

[Bộ nhãn độc lập](../../../tests/fixtures/dedup_quality.json) có 16 video và 5 cặp đúng do người viết fixture xác định trước, gồm cùng bài/cùng bản thu, cùng bài/khác phiên bản, khác bài có tên phổ biến, tên đa ngôn ngữ và thiếu metadata. Với một alias đa ngôn ngữ đã xác nhận:

| Chỉ số gợi ý cùng bài | Kết quả |
| --- | ---: |
| Cặp gợi ý / cặp đúng | 5 / 5 |
| True positive / false positive / false negative | 4 / 1 / 1 |
| Precision / recall | **0,80 / 0,80** |

False positive là hai bài khác nhau cùng tên `Home`; UI hiển thị xung đột nghệ sĩ và giữ cả hai mặc định. False negative là `Plastic Love` so với tiêu đề có thêm nghệ sĩ Nhật; cần alias người dùng hoặc phương pháp matching mới. Live được đưa vào nhóm cùng bài nhưng giữ marker `live` và không bị tự loại. Các số trên chỉ mô tả fixture tổng hợp nhỏ cho **gợi ý review**, không phải accuracy trên lịch sử thật hoặc khả năng tự loại bản tải.

## Review bảo mật, network và recovery

Không phát hiện finding chặn phát hành sau review.

- Server chỉ bind loopback; middleware kiểm tra Host/Origin, giới hạn request 64 MiB, chặn traversal/tên upload lạ và thêm `nosniff`/`no-store`. Pydantic giới hạn ID, enum, list, revision, token và độ dài input.
- UI dựng nội dung người dùng bằng `textContent`/DOM node; link YouTube dùng video ID đã validate và `noopener noreferrer`. Alias/title không được thực thi như HTML.
- Không có telemetry/analytics. Import, phân loại và dedup chạy local. Thumbnail chỉ gọi `i.ytimg.com` khi hiển thị danh sách; metadata chỉ gọi YouTube Music khi người dùng bắt đầu run; audio chỉ gọi YouTube qua yt-dlp khi bắt đầu download.
- Metadata allowlist trường và không lưu exception/raw response chứa token. Review lần này sửa yt-dlp child để không lưu exception thô, signed URL hoặc token vào SQLite; chỉ giữ mã lỗi và thông báo an toàn.
- Worker tách process, validate ID và file audio trả về, không overwrite file có sẵn; batch snapshot/revision, process lock, stop/resume và restart recovery đã được test.

Giới hạn còn lại: upload được buffer trong RAM tới 64 MiB; kiểm tra file đã tải dựa trên path/kích thước thay vì checksum; desktop entry cài thủ công; chưa kiểm chứng Windows/macOS, HTML Takeout, nhiều export cùng lúc, mất điện vật lý hoặc tải toàn bộ lịch sử qua mạng. Chất lượng matching production vẫn cần nhãn thực tế lớn hơn.

## Đối chiếu nghiệm thu

WA01–WA12 đều có bằng chứng: bốn trang web và workflow browser (WA01–WA02), Explore/music-first và sửa Còn lại (WA03), dedup/alias/version/reject/undo (WA04–WA06), eligible snapshot và counts (WA07), metadata preview/audit/stale/lock (WA08), reimport giữ state theo ID (WA09), lỗi/stop/resume/retry (WA10), migration/input/network scope (WA11), fixture 7.500 và phân trang (WA12). Audio thật một mẫu là bằng chứng lịch sử T09/T12; lượt WFT09 không gọi mạng YouTube thật.
