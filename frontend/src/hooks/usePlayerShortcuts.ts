import { useEffect } from 'react';
import { useAudioPlayer } from '../context/AudioPlayerContext';

export function usePlayerShortcuts() {
  const {
    currentTrack,
    currentTime,
    duration,
    togglePlay,
    nextTrack,
    previousTrack,
    seek,
    toggleMute,
    toggleShuffle,
    toggleRepeat,
    toggleRightPanel,
    setIsShortcutsOpen,
  } = useAudioPlayer();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // 1. Safeguard against typing in input/textarea/select/contenteditable
      const target = e.target as HTMLElement | null;
      if (!target) return;
      const isInput =
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.tagName === 'SELECT' ||
        target.isContentEditable ||
        target.getAttribute('role') === 'textbox';

      if (isInput) return;

      // 2. Ignore if Ctrl / Meta / Alt are pressed
      if (e.ctrlKey || e.metaKey || e.altKey) return;

      // 3. Match shortcut keys
      switch (e.code) {
        case 'Space': {
          e.preventDefault();
          if (currentTrack) {
            togglePlay();
          }
          break;
        }

        case 'ArrowRight': {
          e.preventDefault();
          if (e.shiftKey) {
            seek(Math.min((duration || currentTime) + 5, currentTime + 5));
          } else {
            nextTrack();
          }
          break;
        }

        case 'ArrowLeft': {
          e.preventDefault();
          if (e.shiftKey) {
            seek(Math.max(0, currentTime - 5));
          } else {
            previousTrack();
          }
          break;
        }

        case 'KeyM': {
          e.preventDefault();
          toggleMute();
          break;
        }

        case 'KeyS': {
          e.preventDefault();
          toggleShuffle();
          break;
        }

        case 'KeyR': {
          e.preventDefault();
          toggleRepeat();
          break;
        }

        case 'KeyQ': {
          e.preventDefault();
          toggleRightPanel('queue');
          break;
        }

        case 'KeyI': {
          e.preventDefault();
          toggleRightPanel('now-playing');
          break;
        }

        case 'Slash': {
          if (e.shiftKey || e.key === '?') {
            e.preventDefault();
            setIsShortcutsOpen(true);
          }
          break;
        }

        default:
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [
    currentTrack,
    currentTime,
    duration,
    togglePlay,
    nextTrack,
    previousTrack,
    seek,
    toggleMute,
    toggleShuffle,
    toggleRepeat,
    toggleRightPanel,
    setIsShortcutsOpen,
  ]);
}
