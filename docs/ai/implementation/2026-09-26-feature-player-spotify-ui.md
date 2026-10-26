---
phase: implementation
title: Implementation Guide
description: Ghi chú triển khai layout 3 cột kiểu Spotify, phím tắt và lời bài hát của Music Player
---

# Implementation: Player Spotify-Style Layout, Shortcuts & Lyrics

Cập nhật: **2026-10-26**. Code đã merge qua PR #6 (`feature-player-spotify-ui`). Phần lời bài hát được thêm sau ở commit `b1961d5` và chưa có requirements riêng.

## 1. Layout 3 cột — [PlayerWorkspace.tsx](../../../frontend/src/features/player/PlayerWorkspace.tsx)

- Sidebar trái kéo được trong khoảng 180–420 px, mặc định 240 px, lưu ở `auralytica_player_left_width`.
- Sidebar phải kéo được trong khoảng 240–500 px (requirements ghi 480), mặc định 320 px, lưu ở `auralytica_player_right_width`.
- Double-click thanh kéo trả về độ rộng mặc định.
- Tab của panel phải (`now-playing` | `queue` | đóng) nằm trong [AudioPlayerContext.tsx](../../../frontend/src/context/AudioPlayerContext.tsx), lưu ở `auralytica_player_right_panel_tab`. `isQueueOpen`/`setQueueOpen` cũ được giữ làm cầu nối.
- [PlayerRightSidebar.tsx](../../../frontend/src/features/player/PlayerRightSidebar.tsx): tab Now Playing (ảnh bìa lớn, tag, định dạng, dung lượng, đường dẫn, yêu thích, sửa metadata, lời bài hát) và tab Queue.
- [PersistentPlayerBar.tsx](../../../frontend/src/features/player/PersistentPlayerBar.tsx) có nút bật Now Playing, Queue và modal phím tắt.

## 2. Phím tắt — [usePlayerShortcuts.ts](../../../frontend/src/hooks/usePlayerShortcuts.ts)

Bỏ qua khi focus đang ở `INPUT`, `TEXTAREA`, `SELECT` hoặc phần tử `contentEditable`. Hook được gắn trong `AppShell`, nên phím tắt hoạt động ở mọi mode, không chỉ `/player`.

| Phím | Hành động |
| --- | --- |
| `Space` | Phát / dừng |
| `→` / `←` | Bài sau / bài trước (hoặc phát lại nếu đã qua 3 giây) |
| `Shift + →` / `Shift + ←` | Tua +5 / −5 giây |
| `M`, `S`, `R` | Tắt tiếng, trộn bài, chế độ lặp |
| `Q`, `I` | Bật tab Queue, Now Playing |
| `?` | Mở [ShortcutsModal](../../../frontend/src/features/player/ShortcutsModal.tsx) |

## 3. Lời bài hát — `player.get_lyrics` / `player.save_lyrics`

API:

- `GET /api/player/lyrics?path=...&refresh=true|false`
- `POST /api/player/lyrics` với `path`, `plain_lyrics`, `synced_lyrics`, `is_instrumental`

Thứ tự tìm khi không có cache (hoặc `refresh=true`):

1. Bảng `player_lyrics_cache`.
2. File `.lrc` cùng tên đặt cạnh file audio.
3. Lời nhúng trong tag của file.
4. **LRCLIB** (`https://lrclib.net/api/get`, rồi `/api/search`), timeout 3,5 giây, dùng title/artist/duration từ `player_track_cache`.
5. Không tìm thấy → lưu kết quả rỗng vào cache để không gọi mạng lại.

- `save_lyrics` chỉ ghi vào cache với `source='manual'`, **không ghi vào file audio**.
- `PlayerRightSidebar` luôn được mount trong `PlayerWorkspace`, nên frontend gọi `getPlayerLyrics` mỗi khi bài đang phát đổi lúc đang ở mode Music Player, kể cả khi panel phải đóng. Bài instrumental hoặc không có lời sẽ tự chuyển sang tab thông số.
- Đây là kết nối mạng ra ngoài mới của ứng dụng (tên bài, nghệ sĩ, thời lượng được gửi tới LRCLIB).
