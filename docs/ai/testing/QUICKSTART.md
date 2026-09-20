# T12 — Kiểm chứng cài đặt và hướng dẫn chạy

> Báo cáo này là bằng chứng lịch sử ngày 2026-09-10. Quickstart hiện hành dùng launcher web-only và nằm trong [README dự án](../../../README.md); các subcommand nghiệp vụ bên dưới đã bị gỡ.

Ngày kiểm chứng: **2026-09-10**. **T12 đạt** trên môi trường Python mới `/tmp/auralytica-t12-clean`, cài package không editable từ lockfile. Môi trường `.venv` đang dùng được giữ nguyên. Đây là môi trường Python sạch trên Linux hiện tại; không phải cài lại hệ điều hành. Node.js, FFmpeg và Chromium đã có trên máy.

## Runtime không cần bộ phát triển

```sh
UV_PROJECT_ENVIRONMENT=/tmp/auralytica-t12-clean uv sync --locked --no-default-groups --no-editable
/tmp/auralytica-t12-clean/bin/python tests/manual/quickstart.py artifacts/acceptance-runs/t12-quickstart
```

Cả hai lệnh **exit 0**. Runtime có 25 package, không có pandas/jupyterlab/httpx/playwright. Python 3.11.16 / SQLite 3.53.1. Script xác nhận module được nạp từ site-packages của môi trường mới và kiểm tra CLI help → import → serve/static assets → chuyển nhóm qua HTTP → đọc lại qua CLI → reimport giữ sửa tay. Server được dừng trong finally.

[Report offline local](../../../artifacts/acceptance-runs/t12-quickstart/validation.json). Script yêu cầu work directory chưa tồn tại để tránh nhầm dữ liệu của lần trước. Khi chạy lại, chọn đường dẫn mới.

## Tải một mẫu thật

```sh
/tmp/auralytica-t12-clean/bin/python tests/manual/smoke_download.py artifacts/download-smoke/t09-worker/input artifacts/acceptance-runs/t12-network
```

**Exit 0**: CLI trả queued rồi worker nền hoàn tất, audio **Opus / 1.430.465 byte**, ffprobe chỉ có audio, ffmpeg giải mã exit 0; lượt tiếp theo skipped=1/queued=0. [Report local](../../../artifacts/acceptance-runs/t12-network/validation.json). Chỉ một video được chủ động dùng làm mẫu; không tải toàn bộ lịch sử.

Điều kiện máy hiện tại: Node.js 24.19.0 trong PATH, FFmpeg 8.0.1 và ffprobe. Không truyền API key, tài khoản Spotify hoặc model audio. Muốn tái lập độc lập, thay đường dẫn input bằng một folder Takeout JSON có **đúng một video nhạc duy nhất**, và chọn work directory mới. Script từ chối bắt đầu tải khi số video khác một.

## Regression trên package đã cài

Sau khi kiểm tra runtime tối thiểu, bổ sung dependency test/browser vào cùng môi trường:

```sh
UV_PROJECT_ENVIRONMENT=/tmp/auralytica-t12-clean uv sync --locked --no-default-groups --no-editable --group test --group browser
/tmp/auralytica-t12-clean/bin/python -m unittest discover -s tests -v
/tmp/auralytica-t12-clean/bin/python -m unittest discover -s tests/browser -v
```

Kết quả **66 test core/API + 6 test Chromium OK, exit 0**. Nếu máy chưa có Chromium cho Playwright, chạy `/tmp/auralytica-t12-clean/bin/python -m playwright install chromium` trước suite browser. Host vẫn cần thư viện hệ thống để Chromium chạy; bài này không kiểm chứng cài các thư viện OS trên một distro mới.

Luồng browser lớn: 6.400 video, sửa hai nhóm, snapshot 255, lỗi có kiểm soát, restart, retry/reimport và file mất tải lại. [Report lượt T12](../../../artifacts/acceptance-runs/t12-browser.json). Audio trong browser là fixture; bằng chứng audio phát được nằm ở mẫu mạng riêng.

## Tài liệu và hạn chế còn lại

[README](../../../README.md) đã đưa quickstart lên đầu, bỏ thông tin cũ “Sắp có”, ghi rõ đường dẫn database chung, worker sống sau khi đóng tab/server, dừng/khôi phục, phần mềm cần có và cách xử lý lỗi. Hướng dẫn API/test nằm sau luồng dùng ứng dụng.

Không thay code production/schema trong T12. Chưa đo accuracy, chưa thử mọi URL/mất điện thật, HTML hoặc Windows/macOS. TestClient vẫn báo deprecation httpx nhưng suite đạt; uv báo fallback copy khi cache và môi trường nằm khác filesystem, việc cài đặt vẫn exit 0. SQLite import/transaction chạy được, lỗi sqlite3 cũ chưa tái hiện.

M1–M4 và T01–T12 hoàn tất trong phạm vi MVP Linux/JSON. [AC01–AC08](ACCEPTANCE.md) có bằng chứng riêng; không suy ra hỗ trợ các phạm vi để sau từ việc hoàn tất này.
