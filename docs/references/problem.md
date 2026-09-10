Vấn đề hiện tại là:

Bạn muốn **export toàn bộ nhạc đã từng nghe trên YouTube thường**, không phải YouTube Music, và phải bao gồm cả những video mà YouTube **không gắn nhãn là Music**.

Khó ở chỗ lịch sử YouTube chỉ cho biết bạn đã xem video nào; còn việc xác định “video này có phải nhạc không” thì không thể chỉ dựa vào category/metadata, vì nhiều OST, cover, AMV, remix, reupload, live, BGM… có thể nằm trong `Entertainment`, `People & Blogs`, `Gaming`, v.v.

Hiện tại chưa thấy project GitHub nào làm trọn vẹn toàn bộ pipeline này. Cách khả thi nhất là ghép:

- `Google Takeout` hoặc `yt-dlp` để lấy toàn bộ watch history.
- `yt-dlp` để lấy metadata/audio.
- `YAMNet` hoặc model audio classification để xác định video có nhạc thật sự.
- Có thể dùng `Demucs + Shazam/ACRCloud/AcoustID` nếu muốn nhận diện luôn tên bài trong video có speech/voice-over.

Repo gần nhất với phần quan trọng là `Notalle/tracklist-extractor`, vì nó đã có:

```text
YouTube URL
→ yt-dlp
→ audio
→ YAMNet
→ music probability
```

Phần còn thiếu chủ yếu là nối nó với `watch-history.json` và chạy hàng loạt trên toàn bộ lịch sử.

Nói ngắn gọn, pipeline cần làm là:

```text
YouTube Watch History
        ↓
deduplicate video IDs
        ↓
metadata filter nhanh
        ↓
audio classifier cho các case không rõ
        ↓
music_history.csv / SQLite
```
