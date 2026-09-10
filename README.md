# Auralytica

Tải audio nhạc từ lịch sử YouTube trong Google Takeout bằng CLI hoặc web chạy trên máy. Duyệt hai nhóm **Nhạc / Còn lại**, chuyển video qua lại, rồi bấm **Tải toàn bộ**.

MVP Linux/JSON đã hoàn tất T01–T12. Xem [dashboard dự án](PROJECT_DASHBOARD.md), [nghiệm thu chức năng](docs/ai/testing/ACCEPTANCE.md) và [kiểm chứng cài đặt](docs/ai/testing/QUICKSTART.md).

## Bắt đầu

Cần Linux, **uv**, Python **≥3.11 có sqlite3** và **Node.js** trong PATH để yt-dlp xử lý YouTube. Môi trường đã kiểm chứng: Python 3.11.16, Node.js 24.19.0, uv 0.12.10. FFmpeg/ffprobe dùng để kiểm tra audio trong bài smoke; ứng dụng giữ codec nguồn, không chuyển mã sang MP3. Không cần API key, Spotify, model audio hoặc notebook.

Tại thư mục repository:

```sh
uv sync --locked --no-default-groups
uv run --no-sync auralytica --help
uv run --no-sync auralytica serve
```

Mở **http://127.0.0.1:8765** bằng trình duyệt. Server không tự mở cửa sổ browser.

1. Kéo folder Takeout **đã giải nén** vào vùng nhập, hoặc bấm **Chọn folder**. Cần lịch sử ở dạng `watch-history.json`; nếu có nhiều nguồn, chọn một lịch sử và music library cùng export.
2. Xem hai bảng. Topic/library là gợi ý mạnh; ca chưa rõ và có bằng chứng loại trừ ở **Còn lại**. Mũi tên chuyển từng video; checkbox và nút chuyển dùng cho nhiều dòng. Lựa chọn lưu tự động.
3. Nhập thư mục lưu trên máy, mặc định `~/Music/Auralytica`. Bấm **Tải toàn bộ** để tải mọi video bên Nhạc, kể cả đang ẩn bởi bộ lọc/trang. Checkbox chỉ dùng để chuyển nhóm.
4. Theo dõi trạng thái và lỗi từng video ở bảng tải. File hoàn tất còn hợp lệ được bỏ qua. Khi không còn việc hoặc đang có lượt tải hoạt động, nút tải bị khóa.

**Đóng tab hoặc Ctrl+C dừng server không dừng worker tải nền.** Dùng nút **Dừng / khôi phục** hoặc lệnh `stop`; chờ trạng thái **Đã dừng** trước khi sửa nhóm. Tiếp tục lượt cũ vẫn dùng danh sách và thư mục đã chốt của lượt đó. Muốn dùng danh sách đã sửa, tạo lượt mới bằng **Tải toàn bộ**.

## Dùng CLI

```sh
uv run --no-sync auralytica import '/path/to/Takeout'
uv run --no-sync auralytica list --group music --sort watch_count
uv run --no-sync auralytica list --group rest --search 'cover' --page 1 --page-size 50
uv run --no-sync auralytica move VIDEO_ID_1 VIDEO_ID_2 --to music
uv run --no-sync auralytica move VIDEO_ID_1 --to rest
uv run --no-sync auralytica download --output ~/Music/Auralytica
uv run --no-sync auralytica status
uv run --no-sync auralytica stop 1
uv run --no-sync auralytica resume 1
```

Thay đường dẫn, VIDEO_ID và `1` bằng dữ liệu thật. `download`/`resume` trả batch ID ngay sau khi khởi động worker nền; lệnh thành công chưa có nghĩa audio đã tải xong. Xem `status [id] --page 1 --page-size 50` hoặc giao diện để biết kết quả cuối. Không truyền ID thì status ưu tiên lượt đang hoạt động, sau đó lượt mới nhất. Web hiển thị 50 lượt gần đây, CLI theo ID truy cập được lượt cũ hơn.

Import tự chạy gợi ý và chỉ đối chiếu library với video có trong lịch sử. Khi nhiều nguồn, thêm `--history 'history/watch-history.json'` là đường dẫn tương đối trong folder. `classify` chạy lại gợi ý nhưng giữ sửa tay. `list` hỗ trợ `--channel`, `--reason` và `--sort`; chuyển tối đa 1.000 ID/lần. Chuyển về Còn lại không xóa file audio.

## Dữ liệu và khôi phục

Database mặc định: `~/.local/share/auralytica/library.sqlite3`. Mọi lệnh đều nhận `--database '/path/to/library.sqlite3'`; dùng **cùng đường dẫn** cho CLI và server nếu chọn database riêng. Ví dụ:

```sh
uv run --no-sync auralytica serve --database '/path/to/library.sqlite3' --port 8765
uv run --no-sync auralytica status --database '/path/to/library.sqlite3'
```

Audio lưu trong thư mục đích, tên chứa video ID. File dở nằm dưới `.auralytica/` trong thư mục đích để tiếp tục; giữ thư mục này nếu còn lượt chưa hoàn tất. Khi sao lưu, dừng worker trước và giữ cả database lẫn thư mục audio. Việc bỏ qua file dựa trên đường dẫn/kích thước đã lưu, chưa dùng checksum.

| Tình huống | Cách xử lý |
| --- | --- |
| Thiếu `sqlite3` | Kiểm tra `uv run --no-sync python -c "import sqlite3; print(sqlite3.sqlite_version)"`. Chọn interpreter có SQLite rồi tạo lại môi trường; không dùng `pip install sqlite3`. Lỗi cũ chưa tái hiện trong kiểm chứng. |
| Không có lịch sử JSON | Kiểm tra folder đã giải nén và export có lịch sử dạng JSON. HTML chưa hỗ trợ. |
| Upload quá lớn | Web giới hạn request 64 MiB; dùng CLI import cho nguồn lớn hơn, rồi mở server với cùng database. |
| Video unavailable/private/xóa | Xem lỗi riêng của video; phần khác tiếp tục. Chỉ thử lại khi video còn truy cập được. Không bảo đảm khôi phục video đã mất. |
| Lỗi mạng hoặc xử lý YouTube | Kiểm tra mạng, `node --version` và lỗi từng video; dùng Tiếp tục để thử lại. Không tự đổi sang một bản nhạc khác. |
| Không ghi được / đầy đĩa | Kiểm tra quyền và dung lượng thư mục đích rồi tiếp tục. Muốn đổi đích: dừng, chọn thư mục mới và tạo lượt mới. |
| Lượt còn running sau sự cố | Dùng Dừng / khôi phục hoặc `stop ID`. Chỉ khôi phục khi worker cũ đã nhả khóa, rồi `resume ID`. |
| Cổng đang được dùng | Thêm `--port 8766`, mở đúng địa chỉ/cổng mới. Server chỉ nghe loopback. |

## Giới hạn

Chỉ lấy video có nội dung chính là nhạc, không trích BGM từ video nói chuyện/game. “Audio gốc” là stream tốt nhất truy cập được của video trên YouTube, không phải file master người đăng. AMV/cover/OST/remix/unofficial không có nhãn Music có thể cần chuyển tay. Chưa đo precision/recall; không tuyên bố tự nhận đủ mọi nhạc hoặc xác nhận Shorts chỉ từ duration/hashtag.

Hiện hỗ trợ Linux và một export JSON đang xem; chưa hỗ trợ HTML, merge nhiều export đồng thời hoặc đóng gói Windows/macOS. Dashboard phân tích trong app nằm ngoài MVP này. [PROJECT_DASHBOARD.md](PROJECT_DASHBOARD.md) là tài liệu theo dõi phát triển.

## Kiểm thử và phát triển

```sh
uv sync --locked --no-default-groups --group test
uv run --no-sync python -m unittest discover -s tests -v

uv sync --locked --no-default-groups --group test --group browser
uv run --no-sync python -m playwright install chromium
uv run --no-sync python -m unittest discover -s tests/browser -v
```

Playwright/Chromium chỉ cần cho test. Dependencies notebook ở group `notebook`; thêm `--group notebook` khi sync nếu muốn giữ chúng. Sync có thể gỡ package không thuộc nhóm đã chọn.

Để kiểm tra trong môi trường riêng, giữ `.venv` hiện tại:

```sh
UV_PROJECT_ENVIRONMENT=/tmp/auralytica-check uv sync --locked --no-default-groups --no-editable --group test
/tmp/auralytica-check/bin/python -m unittest discover -s tests -v
```

[Hướng dẫn kiểm chứng sạch](docs/ai/testing/QUICKSTART.md) có lệnh smoke offline/một video thật. Smoke mạng chỉ chạy khi được chủ động gọi; bộ test tự động dùng dữ liệu tổng hợp.

## HTTP API local

`GET /api/videos` dùng group/search/channel/reason/sort/page/page_size như CLI. `POST /api/videos/move` nhận `{"video_ids":["abcdefghijk"],"to_group":"music"}`. `POST /api/imports` nhận multipart `files`: một watch-history.json và tối đa một music library songs.csv cùng export.

API tải: `GET /api/downloads/preview?output_dir=...`, `GET /api/downloads`, `GET /api/downloads/{id}?page=1&page_size=20`; `POST /api/downloads` nhận `{"output_dir":"/path/to/audio"}`, `POST /api/downloads/{id}/stop` và `/resume`.

POST phải có Origin khớp Host/port local, ví dụ `Origin: http://127.0.0.1:8765`. Title/kênh là dữ liệu văn bản, không render trực tiếp thành HTML. API không cần key bên ngoài và không mở CORS rộng.
