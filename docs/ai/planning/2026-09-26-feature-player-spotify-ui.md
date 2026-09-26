# Implementation Plan: Player Spotify-Style Resizable Layout & Global Keyboard Shortcuts

## Tasks

- [ ] Task 1: Update `AudioPlayerContext` with right panel tab management (`now-playing`, `queue`), shortcuts modal visibility state, and bridge legacy queue state.
- [ ] Task 2: Create `usePlayerShortcuts` hook with comprehensive input guard and keyboard bindings (`Space`, `ArrowRight`/`ArrowLeft`, `Shift + ArrowRight/Left`, `M`, `S`, `R`, `Q`, `I`, `?`).
- [ ] Task 3: Create `ShortcutsModal` component to display keyboard controls cleanly.
- [ ] Task 4: Create `PlayerRightSidebar` component supporting resizable width, Now Playing tab (large art, rich tags, format/size, path copy, edit action) and Queue tab.
- [ ] Task 5: Update `PlayerSidebar` to support resizable width via draggable splitter handle and persistence.
- [ ] Task 6: Update `PlayerWorkspace` to dock the left and right sidebars with drag handles, persist widths in `localStorage`, and wire up shortcuts hook.
- [ ] Task 7: Update `PersistentPlayerBar` to add Now Playing toggle button, Queue toggle button, and Shortcuts modal trigger.
- [ ] Task 8: Run type check, build frontend, and verify all functionality.
