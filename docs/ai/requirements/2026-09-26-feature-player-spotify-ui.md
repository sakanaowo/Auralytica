# Requirements: Player Spotify-Style Resizable Layout & Global Keyboard Shortcuts

## 1. Problem Statement
The current local Music Player workspace (`/player`) has a fixed-width left navigation sidebar and an overlay drawer for the play queue that obscures the main track table. Users cannot resize navigation panes to match their display width, and lack a dedicated docked "Now Playing" view to inspect high-resolution album art, rich tags, and local track file specs alongside the library. Additionally, playback lacks desktop-grade keyboard shortcuts (`Space` to play/pause, `Left`/`Right` arrows to switch tracks, seek, and an options/shortcuts cheatsheet modal).

## 2. Goals & Non-Goals
### Goals
- Implement a 3-column Spotify-style layout for `/player`:
  - **Left Sidebar**: Resizable navigation & playlist pane (`min: 180px`, `max: 420px`, `default: 240px`) with draggable splitter, saved in `localStorage`.
  - **Center View**: Fluid main content table/grid (`flex-1 min-w-0`).
  - **Right Sidebar**: Docked, resizable panel (`min: 240px`, `max: 480px`, `default: 320px`) with draggable splitter, saved in `localStorage`, supporting two tabs:
    - **Now Playing View**: Large cover art, track/artist/album details, technical specs (duration, format, file size, genre, year, path), quick favorite toggle, and metadata edit button.
    - **Queue View**: Active song indicator, queued upcoming songs, remove/play actions, clear queue.
- Implement global keyboard shortcuts with input-safety guards (ignored when typing in inputs/textareas/contenteditable):
  - `Space`: Toggle Play/Pause.
  - `ArrowRight`: Skip to next track.
  - `ArrowLeft`: Skip to previous track (or replay if played > 3s).
  - `Shift + ArrowRight` / `Shift + ArrowLeft`: Seek +5s / -5s.
  - `M`: Toggle mute.
  - `S`: Toggle shuffle.
  - `R`: Toggle repeat mode.
  - `Q`: Toggle Queue tab in Right Sidebar.
  - `I`: Toggle Now Playing tab in Right Sidebar.
  - `?`: Toggle Keyboard Shortcuts modal ("Tùy chọn phím tắt").
- Provide an Options / Shortcuts Modal (`ShortcutsModal`) triggerable via `?`, player bar, or header button.

### Non-Goals
- Altering the Takeout Studio workflow layout (steps 01-04 remain as-is).
- Cloud sync of player widths (local storage is sufficient for desktop use).

## 3. User Stories
1. **As a user**, I want to drag the borders of the left and right sidebars so I can balance viewing my playlists, track table, and now-playing details for my screen size.
2. **As a user**, I want my customized sidebar widths and open/closed state remembered across browser refreshes.
3. **As a user**, I want to press `Space` to pause/play and `Left`/`Right` arrow keys to change songs without reaching for the mouse, without triggering accidentally when typing in search bars.
4. **As a user**, I want an options/shortcuts dialog so I can see all available keyboard controls.

## 4. Success Criteria
- [x] Left sidebar in `/player` is resizable and persists width to `localStorage`.
- [x] Right sidebar in `/player` is docked, resizable, tabbed (Now Playing & Queue), collapsible, and persists state to `localStorage`.
- [x] PersistentPlayerBar contains Now Playing toggle, Queue toggle, and Shortcuts modal button.
- [x] Global keyboard shortcuts work as specified and are strictly ignored inside text inputs.
- [x] Frontend builds cleanly with zero TypeScript errors.
