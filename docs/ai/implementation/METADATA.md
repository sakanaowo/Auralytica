# FE02 — Collector metadata, cache và audit

Triển khai **2026-09-11**, dựa trên [pilot YouTube Music](../../references/youtube-music-identification.md). Collector cung cấp bằng chứng cho FE03; rules-v1 vẫn quyết định như trước. Không có tự động gọi mạng lúc import/classify hoặc tự chuyển nhóm từ metadata mới.

## Dữ liệu

SQLite nâng **v1 → v2 trong một transaction**, giữ các bảng và dữ liệu cũ. Thêm:

| Bảng | Vai trò |
| --- | --- |
| audit_runs | Lượt classification/metadata, import/source hash, version/config, status và thời điểm |
| audit_events | Event nối tiếp với run/video, payload và thời điểm; app không cập nhật/xóa event cũ |
| metadata_items | Snapshot ID, thứ tự, pending/done/failed và observation được dùng |
| metadata_cache | Index provider key + video ID tới observation gốc và thời điểm lấy |

Không nhập ngược lịch sử audit cho quyết định đã xảy ra trước v2. Mở bằng code v1 sau migration sẽ bị từ chối do schema mới hơn; dùng code hiện hành. Khởi động lại server để dùng code ghi audit mới.

## Collector và khôi phục

`metadata.py` tạo snapshot từ import đang chọn. Trên trang Explore, người dùng chọn phạm vi/giới hạn rồi bấm **Lấy metadata**; đây là thao tác gọi mạng rõ ràng. Thu thập tuần tự qua `ytmusicapi==1.12.2`, `get_song`, không đăng nhập. Provider key gồm version thư viện, parser `player-v1`, language `en`, location `VN`.

Mỗi observation giữ requested/returned ID, exact match, status, source path từng field, missing fields, playability, category, title/author/channel, duration/live flag, elapsed time, HTTP status cuối và attempt. Không giữ response thô, cookies, headers, playbackTracking, feedback token hoặc signed media URL; không lưu `str(exception)`.

Cache chỉ dùng observation có response đúng ID, kể cả type thiếu hoặc UNPLAYABLE. Thiếu type là giá trị missing, không phải non-music. Cache mặc định 7 ngày; không dùng cache tương lai/hết hạn, khác provider key, hoặc khi refresh. Lỗi/missing response/sai ID không ghi vào cache. Queue type không làm fallback cho player type; collector không gọi queue.

Timeout connect/read là 5/15 giây. Mỗi item tối đa 3 attempts/lần collect; retry lỗi kết nối/timeout, HTTP 429/5xx, backoff 1/2/4 giây; các lỗi khác được giữ để kiểm tra rồi tiếp tục item kế. Nghỉ tối thiểu 250 ms giữa request. Chưa phải xử lý rate limit thích nghi hoặc timeout tổng tuyệt đối cho run.

`<database>.metadata.lock` dùng flock Linux, chỉ một collector cho một DB; khóa này tách worker audio vì collector không thay nhóm/download snapshot. Mỗi observation và cập nhật item/cache nằm trong transaction ngắn, không giữ khóa SQLite trong lúc gọi mạng.

Ctrl+C/exception ngoài provider ghi paused; kill đột ngột có thể để running nhưng flock được nhả khi tiến trình chết. Resume cùng run bỏ qua item done, thử lại failed/pending, giữ snapshot/config cũ kể cả import thay đổi. Mỗi lần resume có ngân sách retry mới, attempt trong log vẫn tăng. Run toàn bộ done là completed; có failed là partial. Status done nghĩa đã ghi được observation đúng ID, không đồng nghĩa là nhạc hay tải được.

## Audit phân loại và sửa tay

`classification.py` ghi run mới cho mỗi import/classify và `classification_decided` cho từng video. Payload có toàn bộ input của rules-v1 (title/channel/metadata/personal watch_count/channel decision), rule version, evidence, nhóm/lý do trước và sau, user override, nhóm hiệu lực. Chưa dùng observation YTM trong classifier nên chưa có liên kết YTM → classification ở FE02; sẽ bổ sung khi FE03/FE04 dùng những feature đó.

`storage.set_video_group` ghi `review_changed` trong cùng transaction với sửa nhóm, liên kết decision tự động gần nhất nếu có. Thao tác web dùng chung service này; có before/after effective group và user group, kể cả reset override. Chưa có ô nhập lý do sửa tay trong UI.

`audit.export_events` xuất snapshot đọc nhất quán, chứa run manifests và observation gốc của cache kể cả đến từ run khác. Lọc theo run/video; không ghi đè file có sẵn. Audit trong SQLite là nguồn chính, file JSONL là bản xuất theo yêu cầu. File xuất chứa lịch sử cá nhân, giữ local. Chưa có retention/rotation hoặc chống sửa database bằng công cụ ngoài; export hiện nạp tập event được chọn vào bộ nhớ.

## Kiểm chứng

**82 core/API + 6 Chromium đạt**, wheel build đạt; [báo cáo testing](../testing/README.md) ghi lệnh/bằng chứng. TestClient có cảnh báo deprecation hiện hữu, không làm test fail.

- Test SQLite thật: migration giữ review/download, decision và review audit, cache hit/expiry/refresh/version, ID mismatch, missing/type lạ, UNPLAYABLE, retry/permanent error, Ctrl+C/resume qua import khác, process lock và kill recovery, export dependency/no overwrite.
- Kiểm thử collector → cache → status → export dùng provider fixture để không gửi ID test ra mạng.
- Smoke runtime thật trên bản sao DB, **đúng 18 ID đã được người dùng cho phép**: lần đầu 18 calls, lần hai **0 calls/18 cache hits**, mọi row video không đổi; hai lượt tổng 9,6 giây. [Summary local](../../../artifacts/metadata-smoke/fe02-20260911T081317Z/summary.json), [network log](../../../artifacts/metadata-smoke/fe02-20260911T081317Z/network.jsonl), [cache log](../../../artifacts/metadata-smoke/fe02-20260911T081317Z/cache.jsonl). Không suy ra tốc độ hoặc accuracy toàn lịch sử từ mẫu này.

FE03 còn đánh giá residual và ngưỡng trên nhãn độc lập. FE04 mới nối gợi ý YTM/feature và phần xem lý do mới vào hai bảng. Không chạy model audio trong FE02.
