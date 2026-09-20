# Web-only parity — WFT08

Ngày đối chiếu: **2026-09-20**. Bảng này là điều kiện gỡ CLI nghiệp vụ; mỗi hàng chỉ đạt khi có thao tác web và kiểm thử tương ứng.

| Nghiệp vụ | Vị trí web | Backend giữ lại | Bằng chứng |
| --- | --- | --- | --- |
| Nhập Takeout/chọn nguồn | Import | importer + `/api/imports` | API rollback/multi-source; Chromium picker/drop/reimport |
| Xem, lọc, phân trang và sửa Nhạc/Còn lại | Explore | review + `/api/videos` | API validation; Chromium filter/page/bulk/reload |
| Thống kê lịch sử cá nhân | Explore | explore summary | Counts fixture/reimport và benchmark 7.500 video |
| Metadata scope/start/stop/resume/log | Explore | metadata/enrichment worker | API cache/recovery; Chromium metadata fixture |
| Preview/apply phân loại | Explore | classification preview + audit | Snapshot stale/batch lock/rollback; Chromium apply |
| Alias, nhóm nghi trùng, reject/undo | Deduplicate | dedup service | API revision/stale; Chromium Shoujo A / 少女A |
| Chọn bản giữ/loại | Deduplicate | download selections | Revision 409/reimport/default keep/browser reload |
| Preview tập tải và file skip | Download | eligible snapshot | Token/output/file-state tests; counts riêng |
| Tạo/dừng/tiếp tục/thử lại batch | Download | worker/download controls | API + Chromium restart, item lỗi và file mất |
| Xem trạng thái/lỗi từng video | Download | batch status | Phân trang status và browser batch table |
| Mở ứng dụng | Launcher/desktop entry | FastAPI + uvicorn | Unit + subprocess loopback/health/port ownership |

`auralytica` hiện chỉ còn `--port`, `--database` và `--no-browser`. Các subcommand import/classify/list/move/metadata/audit/classification-preview/classification-apply/download/status/stop/resume đã bị gỡ. Module importer, metadata, dedup, downloader, audit và worker vẫn là backend nội bộ được web gọi; chúng không bị nhân đôi hoặc xóa.

Audit JSONL và CSV preview từng là công cụ phát triển cho giai đoạn nghiên cứu. Luồng người dùng hiện xem event/preview trực tiếp trên Explore và không trao đổi file trung gian. Các artifact nghiên cứu cũ được giữ làm bằng chứng lịch sử, không phải bước vận hành hiện hành.

Giới hạn còn lại: request upload web tối đa 63 MiB; desktop entry cần bước cài file `.desktop` sau khi cài package; chưa có installer Windows/macOS. Các giới hạn này được ghi trong README và không có fallback sang CLI nghiệp vụ.
