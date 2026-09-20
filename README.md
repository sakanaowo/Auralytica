# Auralytica

Auralytica là ứng dụng web chạy trên máy để lấy danh sách video từ Google Takeout, tìm video nhạc, so các video có thể cùng bài và tải audio nguồn của những bản bạn giữ.

Luồng sử dụng duy nhất là **Import → Explore → Deduplicate → Download**. Các nghiệp vụ nhập, phân loại, metadata, chọn bản và điều khiển tải đều nằm trên web; không cần truyền CSV hoặc chạy lệnh riêng giữa các bước.

## Cài đặt và mở ứng dụng

Cần Linux, Python **≥3.11 có sqlite3**, [uv](https://docs.astral.sh/uv/) và Node.js trong `PATH`. Node.js được yt-dlp dùng khi xử lý YouTube. Ứng dụng không cần API key, Spotify, model audio hoặc notebook.

Cài entrypoint vào môi trường người dùng rồi mở ứng dụng:

```sh
uv tool install .
auralytica
```

`auralytica` chạy server tại `http://127.0.0.1:8765` và tự mở trình duyệt. Nếu đúng instance Auralytica với cùng database đã chạy, launcher chỉ mở lại trang đó. Nếu cổng thuộc process khác hoặc instance dùng database khác, launcher báo lỗi; nó không kill hoặc tái sử dụng process chưa xác minh.

Khi phát triển trực tiếp trong repository:

```sh
uv sync --locked --no-default-groups
uv run --no-sync auralytica
```

Các tùy chọn kỹ thuật của launcher:

```sh
auralytica --port 8766
auralytica --database '/path/to/library.sqlite3'
auralytica --no-browser
```

Không còn các subcommand nghiệp vụ cũ như `import`, `metadata`, `download` hoặc `status`.

### Mở từ menu ứng dụng Linux

Sau khi `auralytica` đã được cài bằng `uv tool install`, cài desktop entry một lần:

```sh
install -Dm644 packaging/auralytica.desktop "$HOME/.local/share/applications/auralytica.desktop"
```

Sau đó mở **Auralytica** từ menu ứng dụng. Desktop entry chạy launcher mà không mở terminal.

## Quy trình web

1. **Import:** kéo folder Takeout đã giải nén hoặc bấm **Chọn folder**. Cần `watch-history.json`; nếu có nhiều nguồn, chọn một history và music library thuộc cùng export.
2. **Explore:** xem nhóm Nhạc và thống kê lượt xem của bạn. Mở **Còn lại** khi muốn bổ sung hoặc sửa video. Metadata, preview và apply đều chạy tại đây, có phạm vi, tiến độ và log.
3. **Deduplicate:** quét nhóm nghi cùng bài, xem tiêu đề/kênh/evidence và bỏ chọn các video không muốn tải. Mọi bản được giữ mặc định; có thể bỏ qua bước này.
4. **Download:** chọn thư mục lưu rồi tải toàn bộ bản được giữ, kể cả video ở trang khác hoặc đang bị bộ lọc ẩn. Trang này tách số bị loại bởi dedup, file đã có và file cần tải.

Audio là stream tốt nhất truy cập được của đúng video đã chọn, giữ codec nguồn và không chuyển sang MP3. Lỗi một video không chặn video khác. Bảng tải cho phép dừng, tiếp tục và thử lại; batch cũ luôn giữ danh sách đã chốt lúc tạo.

Đóng tab hoặc dừng server không tự dừng worker audio nền. Mở lại Auralytica để xem trạng thái. Nếu cần sửa Nhạc hoặc lựa chọn dedup, hãy dừng batch đang chạy trước.

## Dữ liệu, log và khôi phục

Database mặc định nằm tại `~/.local/share/auralytica/library.sqlite3`. Lựa chọn thủ công, metadata, dedup, batch và log quyết định cùng nằm trong database này. Explore hiển thị log metadata gần đây; Download hiển thị lỗi theo video. Ứng dụng không tự tạo file log phiên bên ngoài.

Không có telemetry hoặc analytics. Import, phân loại và dedup chạy local. Trình duyệt chỉ lấy thumbnail từ `i.ytimg.com` khi hiển thị video; YouTube Music chỉ được gọi khi bạn bắt đầu lấy metadata; YouTube/yt-dlp chỉ được gọi khi bạn bắt đầu tải audio. Log lỗi không lưu exception thô, signed URL hoặc token từ provider.

Audio nằm trong thư mục đích. File dở nằm dưới `.auralytica/` trong thư mục đó để hỗ trợ tiếp tục; giữ thư mục này khi còn batch chưa hoàn tất. Khi sao lưu, dừng worker rồi giữ cả database và thư mục audio. Việc nhận file đã tải dựa trên đường dẫn/kích thước đã lưu, chưa dùng checksum.

| Tình huống | Cách xử lý |
| --- | --- |
| Không có lịch sử JSON | Chọn folder Takeout đã giải nén có history dạng JSON. HTML chưa hỗ trợ. |
| Upload vượt 63 MiB | Bản local hiện tại từ chối request lớn hơn giới hạn này; tách/chọn export nhỏ hơn trước khi nhập. |
| Video private/xóa | Xem lỗi riêng của video; phần khác tiếp tục. Auralytica không tự đổi sang video khác. |
| Lỗi mạng hoặc YouTube | Kiểm tra mạng và `node --version`, sau đó bấm **Tiếp tục lượt này**. |
| Không ghi được hoặc đầy đĩa | Dừng batch, kiểm tra quyền/dung lượng, rồi tiếp tục. Tạo lượt mới nếu đổi thư mục đích. |
| Cổng đang được dùng | Đóng process đó hoặc mở bằng `auralytica --port 8766`. Launcher không tự kill process. |
| Thiếu `sqlite3` | Chọn Python có SQLite rồi cài lại; không cài package `sqlite3` từ pip. |

Chỉ lấy video có nội dung chính là nhạc, không trích BGM từ video nói chuyện/game. AMV, cover, OST, remix hoặc reupload không có nhãn Music có thể cần sửa tay. Alias đa ngôn ngữ chỉ được dùng khi có evidence/xác nhận; ứng dụng chưa cam kết nhận diện mọi bài hoặc báo precision/recall production.

Hiện hỗ trợ Linux và một export JSON đang hoạt động; chưa hỗ trợ HTML, merge nhiều export, hosted SaaS hoặc đóng gói Windows/macOS.

## Kiểm thử và phát triển

```sh
uv sync --locked --no-default-groups --group test --group browser
uv run --no-sync python -m unittest discover -s tests -v
uv run --no-sync python -m unittest discover -s tests/browser -v
```

Xem [dashboard dự án](PROJECT_DASHBOARD.md), [requirements web workflow](docs/ai/requirements/2026-09-20-feature-web-workflow.md), [kịch bản nghiệm thu](docs/ai/testing/2026-09-20-feature-web-workflow.md) và [review cuối WFT09](docs/ai/testing/WFT09_FINAL_REVIEW.md).
