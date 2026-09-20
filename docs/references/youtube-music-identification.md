# YouTube Music làm tầng nhận diện trước bộ lọc

Ngày kiểm chứng: **2026-09-11**. Đã chạy mẫu cố định **18 video được người dùng cho phép**, đối chiếu metadata và ghi log. Chưa thay classifier hoặc nhóm video trong ứng dụng.

[Notebook 04](../../notebooks/04_ytmusic_metadata_audit.ipynb) · [Notebook đã chạy](../../artifacts/notebook-runs/04_ytmusic_metadata_audit.executed.ipynb) · [Manifest](../../artifacts/ytmusic-pilot/20260911T041238Z/manifest.json) · [Log JSONL](../../artifacts/ytmusic-pilot/20260911T041238Z/events.jsonl) · [Summary](../../artifacts/ytmusic-pilot/20260911T041238Z/summary.json).

Các link artifacts chứa dữ liệu cá nhân, chỉ có trên máy local và không commit. Notebook nguồn không có output cá nhân, chỉ đọc log offline.

## Câu hỏi và phương pháp

Có thể dùng YouTube Music để nhận trước nhạc trong lịch sử, rồi chỉ áp dụng feature engineering cho phần còn lại. Tuy nhiên, phải xác minh **đúng ID video và nguồn field**; tìm được một bài cùng tên hoặc có trong queue không đủ.

Thử bằng ytmusicapi **1.12.2**, không đăng nhập, language `en`, location `VN`, không gửi lượt xem/timestamp cá nhân, không phát hoặc tải audio. Mỗi ID gọi một lần `get_song` và một lần `get_watch_playlist(limit=1, radio=False)`. `limit` là mức tối thiểu; queue có thể trả thêm nhiều video, chỉ lấy entry khớp ID yêu cầu. Mẫu được đọc từ manifest đã duyệt, không chọn lại từ DB khi chạy.

Nguồn sơ cấp: [ytmusicapi](https://ytmusicapi.readthedocs.io/en/stable/) là client không chính thức; [get_song](https://ytmusicapi.readthedocs.io/en/stable/reference/browsing.html#ytmusicapi.YTMusic.get_song) cung cấp metadata video; [get_watch_playlist](https://ytmusicapi.readthedocs.io/en/stable/reference/watch.html) cung cấp queue có video type/counterpart; [FAQ](https://ytmusicapi.readthedocs.io/en/stable/faq.html#which-videotypes-exist-and-what-do-they-mean) mô tả ATV, OMV, UGC và OFFICIAL_SOURCE_MUSIC. [Library API](https://ytmusicapi.readthedocs.io/en/stable/reference/library.html) cũng có podcast; việc xuất hiện trên YouTube Music không đồng nghĩa nội dung chính là nhạc.

Không dùng history/library tài khoản online trong pilot. Music library trong Takeout là nguồn offline sẵn có: đã khảo sát 142 dòng, 58 ID trùng lịch sử. Đây là tập con, không phải danh sách đầy đủ mọi nhạc đã xem.

## Kết quả quan sát

**36/36 lời gọi phương thức trả về đúng ID**, 37 HTTP request gồm khởi tạo client đều trả 200, không có exception trong lượt chạy này. `observed` có nghĩa tìm thấy đúng ID trong phản hồi; không có nghĩa video được phân loại là nhạc.

| Nhóm mẫu | Số video | Type trong metadata trực tiếp của player | Type trong queue |
| --- | ---: | --- | --- |
| Nhạc người dùng xác nhận đang bị bỏ sót | 5 | 1 OMV, 1 OFFICIAL_SOURCE_MUSIC, 3 UGC | Tương ứng với player |
| Topic proxy | 3 | ATV | ATV |
| Library proxy | 2 | ATV; cả hai cũng là Topic | ATV |
| Ca tiêu đề gameplay | 3 | Không có musicVideoType | UGC |
| Ca kênh giải trí người dùng muốn loại | 3 | Không có musicVideoType | UGC |
| Ca tiêu đề có #shorts | 2 | Không có musicVideoType | UGC |

**Không gộp `player.musicVideoType` và `queue.videoType` thành một field fallback.** Cả 8 ca đối chứng đều có UGC trong queue nhưng không có type ở player. Thử nghiệm công khai trước đó cũng quan sát điều này với video không phải nhạc. Queue UGC mô tả nội dung người dùng đăng, không đủ để tự chọn nhạc.

Một trong 5 ca nhạc đã xác nhận có category **Gaming** và player UGC. Vì vậy, category Music không được làm điều kiện bắt buộc; category Gaming/Entertainment cũng không được làm điều kiện loại tuyệt đối.

| Giả thuyết chỉ để so độ phủ | Khớp trong 18 mẫu | Khớp trong 5 ca nhạc bị bỏ sót |
| --- | ---: | ---: |
| Baseline rules-v1 tự chọn Nhạc | 5 | 0 |
| Queue có video type | 18 | 5 |
| Player type thuộc ATV/OMV/OFFICIAL_SOURCE_MUSIC | 7 | 2 |
| Player có musicVideoType bất kỳ | 10 | 5 |
| Player category Music | 9 | 4 |

Player type là feature có ích trong mẫu này, **chưa chứng minh mọi player UGC đều là music-primary**. Ba ca nhạc còn lại sau strong gate đều là UGC, có 16–17 lượt xem cá nhân. Cần kết hợp nội dung và recurrence, kiểm chứng trên phản ví dụ có BGM/podcast trước khi tự chọn rộng hơn.

## Thời gian và độ tin cậy

| Phương thức | Số lần | Trung vị | Khoảng quan sát |
| --- | ---: | ---: | ---: |
| get_song | 18 | 358 ms | 105–1.381 ms |
| get_watch_playlist | 18 | 597,5 ms | 265–1.173 ms |

Wall time **27,79 giây** cho 36 lần gọi, gồm nghỉ 250 ms giữa các lần, không gồm khởi tạo client. Cache tắt, một attempt/phương thức. Kết quả này không phải SLA cho hàng nghìn video; chưa thử rate limit hoặc retry/resume. Production nên ưu tiên một lần get_song mỗi ID chưa có cache; queue chỉ bổ sung khi có lý do cụ thể.

Trong mẫu công khai trước đó, một ATV có `UNPLAYABLE` nhưng vẫn có metadata nhạc. Do đó, phải tách nhãn nội dung, trạng thái truy vấn, playability của YTM và khả năng tải bằng yt-dlp. Không dùng lỗi/thiếu metadata/UNPLAYABLE làm nhãn non-music.

## Cách tổ chức tầng nhận diện tiếp theo

1. Lịch sử Takeout quyết định tập ID; dùng Topic/library có sẵn làm seed. Giữ override cấp video cao nhất.
2. Tra metadata trực tiếp theo ID, lưu evidence có đường dẫn nguồn. ATV/OMV/OFFICIAL_SOURCE_MUSIC là nhóm bằng chứng mạnh để đánh giá, kết hợp kiểm tra Shorts/podcast/xung đột.
3. Player UGC, field thiếu, type lạ hoặc lỗi đi vào phần còn lại. Kết hợp tiêu đề đa ngôn ngữ, kênh, metadata, số lượt cá nhân, ngày/phiên quay lại. Category không phải hard gate; lượt xem không quyết định một mình.
4. Giao diện vẫn hai bảng. Phân biệt tự chọn Nhạc với ưu tiên duyệt; các lần sửa nhóm được ghi làm phản hồi. Không thêm bản thu khác hoặc video gợi ý ngoài lịch sử.

Đây là thiết kế cần kiểm chứng tiếp, chưa phải classifier mới. Chưa cần model audio trong bước này.

## Log cho vòng cải thiện

Pilot hiện có `manifest.json` (mẫu/baseline/source hash/phiên bản/cấu hình/hash script), `events.jsonl` (HTTP và observation), `summary.json`, và bản `probe.py` đã chạy. Notebook xuất `video_audit.csv`, `hypothesis_matches.csv`, `hypothesis_coverage.csv`, `latency.csv`, `review.csv`, `analysis_summary.json` dưới `artifacts/notebook-runs/04_ytmusic_audit/<run>/<analysis>/`. Mỗi lần phân tích tạo folder mới, giữ review cũ.

**Cập nhật FE02:** collector/cache, audit classification/review và xuất JSONL đã triển khai trong [runtime](../ai/implementation/METADATA.md). `videos.evidence_json` vẫn giữ bằng chứng mới nhất, audit_events giữ lịch sử mới từ khi nâng cấp. Bảng dưới là thiết kế vòng cải thiện; liên kết YTM vào decision và ghi lý do user nhập còn thuộc FE03/FE04:

| Sự kiện | Trường cần lưu và mục đích |
| --- | --- |
| run_started / run_finished | run_id, source_hash/import_id, code/rule/feature/provider version, cấu hình, thời điểm, tổng từng tầng; cho phép so hai lần chạy |
| metadata_observed / metadata_failed | requested/returned ID, exact_match, provider/method/source path, giá trị type/category, playability, missing fields, fetched_at, cache age/hit, attempt, HTTP/error code, latency; phân biệt lỗi với tín hiệu nội dung |
| classification_decided | decision_id, run_id, video_id, observation refs, feature snapshot kể cả missing, các rule khớp/xung đột, nhóm và lý do trước/sau, override; tái hiện được quyết định |
| review_changed | video_id, decision_id liên quan, nhóm trước/sau, nguồn user và thời điểm, lý do nếu có; tìm các rule thường bị sửa |

Lưu sự kiện nối tiếp, không ghi đè audit bằng `evidence_json`. Có thể dùng SQLite audit làm nguồn chính và xuất JSONL theo run; vị trí log gắn với đường dẫn DB người dùng chọn. Cache metadata tách khỏi quyết định để chạy lại rules không cần gọi mạng. Không lưu cookies, Authorization, token phản hồi hoặc URL media có chữ ký. Raw response nếu cần phải lọc trường trước; pilot chỉ giữ phản hồi rút gọn.

## Giới hạn và bước còn thiếu

- 18 mẫu thiên lệch theo vấn đề đã thấy, không đại diện toàn lịch sử; không công bố precision/recall tổng thể.
- Chưa có podcast thật trong mẫu: nhánh lấy theo từ khóa thực tế chọn ba video gameplay. Cần sửa cách phân tầng ở thử nghiệm sau, không coi nhóm này đã kiểm chứng podcast.
- Ba ca giải trí cùng một kênh; hai library proxy đều trùng tín hiệu Topic. Chưa đo tính tổng quát theo kênh.
- Chưa xác minh Shorts qua metadata chuyên biệt; không suy ra Shorts từ duration hoặc hashtag một mình. Mẫu thiếu music Shorts, music-in-background, nhạc chưa được YTM nhận, mất video/chặn vùng.
- 5 nhãn xác nhận có trước pilot là discovery/regression, không đưa vào holdout để đo sau khi tune. Các proxy không tự biến thành ground truth; notebook để trống nhãn còn lại.
- Collector/cache/audit đã có ở FE02; bước tiếp theo là bổ sung bộ phản ví dụ có nhãn rồi so strong gate và tầng UGC/residual trước khi nối quyết định vào hai bảng. Các thử nghiệm thực tế tới FE02 vẫn chỉ dùng mẫu 18 ID đã duyệt.
