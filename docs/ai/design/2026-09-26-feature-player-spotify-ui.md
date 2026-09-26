# Design: Player Spotify-Style Resizable Layout & Global Keyboard Shortcuts

## 1. Architecture Overview

```mermaid
graph TD
    subgraph AudioPlayerContext
        State[Player State: currentTrack, isPlaying, queue, etc.]
        PanelState[rightPanelTab: 'now-playing' | 'queue' | null]
        ShortcutsModalState[isShortcutsOpen: boolean]
        Controls[togglePlay, nextTrack, previousTrack, seek, toggleRightPanel, etc.]
    end

    subgraph PlayerWorkspace
        LS[PlayerSidebar - Resizable Width 180-420px]
        ResizerL[Splitter Drag Handle Left]
        Center[Center Content: PlayerHeader + TrackTable/Grid]
        ResizerR[Splitter Drag Handle Right]
        RS[PlayerRightSidebar - Resizable Width 240-480px]
        RS_NP[Now Playing Tab: Cover, Track Info, Specs, Fav, Edit]
        RS_Q[Queue Tab: Current, Upcoming, Clear, Remove]
    end

    subgraph Shortcuts
        Hook[usePlayerShortcuts: Window Keydown Listener]
        Guard[Input & ContentEditable Guard]
    end

    subgraph PersistentPlayerBar
        TrackInfo[Cover Thumbnail + Title & Artist -> opens Now Playing]
        Playback[Play/Pause, Prev, Next, Progress Bar]
        RightTools[Volume, Now Playing Toggle, Queue Toggle, Shortcuts Toggle]
    end

    Hook --> Guard
    Guard --> Controls
    AudioPlayerContext --> PlayerWorkspace
    AudioPlayerContext --> PersistentPlayerBar
    PlayerWorkspace --> RS
```

## 2. Component Design & Responsibilities

### 2.1 `AudioPlayerContext`
- Expanded state:
  - `rightPanelTab: 'now-playing' | 'queue' | null`
  - `setRightPanelTab: (tab: 'now-playing' | 'queue' | null) => void`
  - `toggleRightPanel: (tab: 'now-playing' | 'queue') => void`
  - `isShortcutsOpen: boolean`
  - `setIsShortcutsOpen: (open: boolean) => void`
- Existing `isQueueOpen` / `toggleQueueOpen` bridged seamlessly to `rightPanelTab === 'queue'`.

### 2.2 Resizable Splitters
- Mouse drag handlers on vertical divider lines (`onMouseDown` -> attach `mousemove` and `mouseup` to `window`).
- Dynamic style width applied via inline `style={{ width: `${width}px` }}`.
- Constraints enforced via Math.min / Math.max clamping.
- Persisted to `localStorage` (`auralytica_player_left_width` and `auralytica_player_right_width`).
- Double-click on handle resets to sensible default (240px for left, 320px for right).

### 2.3 `PlayerRightSidebar`
- Docked flex column on the right edge of `PlayerWorkspace`.
- Tab bar at top:
  - Button "Đang phát" (with Disc icon)
  - Button "Hàng đợi" (with ListMusic icon and badge count)
  - Close button `X` (collapses panel, setting `rightPanelTab = null`)
- **Now Playing View**:
  - Full-width rounded cover image (with fallback).
  - Title and Artist.
  - Action buttons: Toggle Favorite, Edit Metadata.
  - Detailed metadata card: Duration, Bitrate/Size, File Format, Genre, Year, File Path (with Copy button).
- **Queue View**:
  - Clear queue button.
  - Now playing track item.
  - Scrollable list of upcoming tracks, click-to-play, remove button.

### 2.4 Keyboard Shortcuts Hook (`usePlayerShortcuts`)
- Attaches to `window.addEventListener('keydown')`.
- Strictly checks if `e.target` is an input element:
  ```ts
  const target = e.target as HTMLElement | null;
  if (!target) return;
  const isInput =
    target.tagName === 'INPUT' ||
    target.tagName === 'TEXTAREA' ||
    target.tagName === 'SELECT' ||
    target.isContentEditable;
  if (isInput) return;
  ```
- Maps keys:
  - `Space`: `togglePlay()`
  - `ArrowRight`: `Shift` -> `seek(+5s)`, else `nextTrack()`
  - `ArrowLeft`: `Shift` -> `seek(-5s)`, else `previousTrack()`
  - `KeyM`: `toggleMute()`
  - `KeyS`: `toggleShuffle()`
  - `KeyR`: `toggleRepeat()`
  - `KeyQ`: `toggleRightPanel('queue')`
  - `KeyI`: `toggleRightPanel('now-playing')`
  - `?`: `setIsShortcutsOpen(true)`

### 2.5 `ShortcutsModal`
- Clean dialog showing categorized shortcuts with styled `<kbd>` chips.
