# Auralytica

Auralytica là ứng dụng web chạy trên máy để lấy danh sách video từ Google Takeout, tìm video nhạc, so các video có thể cùng bài và tải audio của những bản bạn giữ. Ứng dụng còn có chế độ tải nhanh từ link YouTube và một trình phát nhạc local.

Thanh trên cùng có ba chế độ:

| Chế độ | Đường dẫn | Dùng khi |
| --- | --- | --- |
| **Takeout Studio** | `/import`, `/explore`, `/deduplicate`, `/download` | Xử lý toàn bộ lịch sử xem theo luồng **Import → Explore → Deduplicate → Download** |
| **Tải nhanh** | `/quick-download` | Tải ngay vài link hoặc một playlist, không cần Takeout |
| **Music Player** | `/player` | Nghe, sắp xếp và sửa tag thư viện đã tải |

Mọi nghiệp vụ đều nằm trên web; không cần truyền CSV hoặc chạy lệnh riêng giữa các bước.

## Cài đặt và mở ứng dụng

Cần Linux, Python **≥3.11 có sqlite3**, [uv](https://docs.astral.sh/uv/), Node.js và `ffmpeg` trong `PATH`. Node.js được yt-dlp dùng khi xử lý YouTube. `ffmpeg` dùng để chuyển sang ALAC/AAC/MP3, nhúng ảnh bìa và để Player phát file ALAC. Ứng dụng không cần API key, Spotify, model audio hoặc notebook.

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

## Takeout Studio

1. **Import:** kéo folder Takeout đã giải nén hoặc bấm **Chọn folder**. Cần `watch-history.json`; nếu có nhiều nguồn, chọn một history và music library thuộc cùng export.
2. **Explore:** xem nhóm Nhạc và thống kê lượt xem của bạn. Mở **Còn lại** khi muốn bổ sung hoặc sửa video. Metadata, preview và apply đều chạy tại đây, có phạm vi, tiến độ và log.
3. **Deduplicate:** quét nhóm nghi cùng bài, xem tiêu đề/kênh/evidence và bỏ chọn các video không muốn tải. Mọi bản được giữ mặc định; có thể bỏ qua bước này.
4. **Download:** chọn thư mục lưu rồi tải toàn bộ bản được giữ, kể cả video ở trang khác hoặc đang bị bộ lọc ẩn. Trang này tách số bị loại bởi dedup, file đã có và file cần tải.

Audio là stream tốt nhất truy cập được của đúng video đã chọn, giữ codec nguồn và không chuyển sang MP3. Lỗi một video không chặn video khác. Bảng tải cho phép dừng, tiếp tục và thử lại; batch cũ luôn giữ danh sách đã chốt lúc tạo.

Đóng tab hoặc dừng server không tự dừng worker audio nền. Mở lại Auralytica để xem trạng thái. Nếu cần sửa Nhạc hoặc lựa chọn dedup, hãy dừng batch đang chạy trước.

Trang Download còn có tuỳ chọn định dạng (giữ nguyên, ALAC, AAC 256, MP3 320), làm sạch tên file, nhúng metadata và số luồng tải song song (1–8).

## Tải nhanh

1. Dán một hoặc nhiều link (watch, `youtu.be`, shorts, playlist hoặc ID 11 ký tự), mỗi dòng một link, rồi bấm phân tích.
2. Sửa Title/Artist của từng bài nếu cần. Tên file dự kiến là `Artist - Title.ext`.
3. Chọn thư mục lưu (mặc định `~/Music/Auralytica`), định dạng và số luồng, rồi bắt đầu tải.
4. Theo dõi, dừng/tiếp tục, thử lại hoặc bỏ qua bài lỗi ngay trên trang. Bài tải xong xuất hiện luôn trong Music Player.

Lưu ý:

- Link watch có cả `v=` và `list=` chỉ tải một video. Muốn tải cả playlist, dùng link `youtube.com/playlist?list=...`.
- Video private, đã xoá hoặc không lấy được thông tin bị bỏ khỏi danh sách và được liệt kê riêng kèm lý do. Lỗi mạng tạm thời cũng rơi vào đây; bấm phân tích lại.
- Mỗi lượt tối đa 1000 bài.
- Ứng dụng chỉ chạy một lượt tải tại một thời điểm. Khi đang có lượt tải (Takeout hoặc Tải nhanh), nút bắt đầu bị khoá cho tới khi lượt đó xong hoặc được tạm dừng.
- Lượt Tải nhanh không khoá Import/Explore/Deduplicate. Title/Artist sửa ở đây chỉ dùng cho file tải về, không thay đổi dữ liệu Takeout.

## Music Player

- Quét một thư mục nhạc local và hiển thị dạng bảng hoặc lưới. Kết quả quét được cache trong database.
- Playlist, yêu thích, hàng đợi, nhập/xuất M3U.
- Sửa tag và ảnh bìa ghi thẳng vào file audio.
- Lời bài hát: lấy theo thứ tự file `.lrc` cạnh bài, lời nhúng trong file, rồi LRCLIB. Lời sửa tay chỉ lưu trong database, không ghi vào file.
- Sidebar trái/phải kéo được độ rộng. Bấm `?` để xem phím tắt (`Space`, `←`/`→`, `Shift+←/→`, `M`, `S`, `R`, `Q`, `I`). Phím tắt có tác dụng ở mọi chế độ, trừ khi đang gõ trong ô nhập.

## Dữ liệu, log và khôi phục

Database mặc định nằm tại `~/.local/share/auralytica/library.sqlite3`. Lựa chọn thủ công, metadata, dedup, batch và log quyết định cùng nằm trong database này. Explore hiển thị log metadata gần đây; Download hiển thị lỗi theo video. Ứng dụng không tự tạo file log phiên bên ngoài.

Không có telemetry hoặc analytics. Import, phân loại và dedup chạy local. Ứng dụng chỉ kết nối ra ngoài trong các trường hợp sau:

| Dịch vụ | Khi nào |
| --- | --- |
| `i.ytimg.com` | Trình duyệt hiển thị thumbnail video |
| YouTube Music | Bạn bắt đầu lấy metadata trong Explore |
| YouTube qua yt-dlp | Bạn bấm phân tích link trong Tải nhanh, hoặc bắt đầu tải audio |
| [LRCLIB](https://lrclib.net) | Bài đang phát đổi trong Music Player mà chưa có lời trong cache, `.lrc` hoặc tag. Tên bài, nghệ sĩ và thời lượng được gửi đi. Kết quả, kể cả "không tìm thấy", được cache. |

Log lỗi không lưu exception thô, signed URL hoặc token từ provider.

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
uv run --no-sync playwright install chromium   # lần đầu, cho test trình duyệt
uv run --no-sync python -m unittest discover -s tests -v
uv run --no-sync python -m unittest discover -s tests/browser -v
```

Thiếu nhóm `test` thì các test dùng FastAPI `TestClient` lỗi ngay lúc import (`requires the httpx2 package`).

Frontend (React + Vite) nằm trong `frontend/`. Sau khi sửa UI, build lại để cập nhật `src/auralytica/static/`:

```sh
npm --prefix frontend ci
npm --prefix frontend run build
```

`npm --prefix frontend run dev` chạy Vite ở cổng 5173 và proxy `/api` tới `127.0.0.1:8765`.

Xem [dashboard dự án](PROJECT_DASHBOARD.md), [requirements web workflow](docs/ai/requirements/2026-09-20-feature-web-workflow.md), [kịch bản nghiệm thu](docs/ai/testing/2026-09-20-feature-web-workflow.md) và [review cuối WFT09](docs/ai/testing/WFT09_FINAL_REVIEW.md).
