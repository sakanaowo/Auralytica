import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import { PlayerTrack } from '../api/types';
import { api } from '../api/client';

interface PlayerStorageState {
  currentTrack: PlayerTrack | null;
  currentTime: number;
  volume: number;
  isMuted: boolean;
  repeatMode: 'off' | 'all' | 'one';
  isShuffled: boolean;
  queue: PlayerTrack[];
}

const STORAGE_KEY = 'auralytica_player_state_v1';

interface AudioPlayerContextType {
  currentTrack: PlayerTrack | null;
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  volume: number;
  isMuted: boolean;
  repeatMode: 'off' | 'all' | 'one';
  isShuffled: boolean;
  queue: PlayerTrack[];
  isQueueOpen: boolean;
  playTrack: (track: PlayerTrack, newQueue?: PlayerTrack[]) => void;
  togglePlay: () => void;
  pause: () => void;
  resume: () => void;
  seek: (seconds: number) => void;
  setVolume: (volume: number) => void;
  toggleMute: () => void;
  toggleShuffle: () => void;
  toggleRepeat: () => void;
  nextTrack: () => void;
  previousTrack: () => void;
  addToQueue: (track: PlayerTrack) => void;
  removeFromQueue: (index: number) => void;
  clearQueue: () => void;
  toggleQueueOpen: () => void;
  setIsQueueOpen: (open: boolean) => void;
  toggleFavorite: (trackPath: string) => Promise<void>;
  updateTrackInState: (track: PlayerTrack) => void;
}

const AudioPlayerContext = createContext<AudioPlayerContextType | null>(null);

function loadSavedState(): PlayerStorageState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      return {
        currentTrack: parsed.currentTrack || null,
        currentTime: typeof parsed.currentTime === 'number' ? parsed.currentTime : 0,
        volume: typeof parsed.volume === 'number' ? parsed.volume : 0.8,
        isMuted: Boolean(parsed.isMuted),
        repeatMode: ['off', 'all', 'one'].includes(parsed.repeatMode) ? parsed.repeatMode : 'off',
        isShuffled: Boolean(parsed.isShuffled),
        queue: Array.isArray(parsed.queue) ? parsed.queue : [],
      };
    }
  } catch (err) {
    console.error('Failed to load player state from localStorage', err);
  }
  return {
    currentTrack: null,
    currentTime: 0,
    volume: 0.8,
    isMuted: false,
    repeatMode: 'off',
    isShuffled: false,
    queue: [],
  };
}

export const AudioPlayerProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [initialState] = useState<PlayerStorageState>(loadSavedState);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [currentTrack, setCurrentTrack] = useState<PlayerTrack | null>(initialState.currentTrack);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<number>(initialState.currentTime);
  const [duration, setDuration] = useState<number>(initialState.currentTrack?.duration || 0);
  const [volume, setVolumeState] = useState<number>(initialState.volume);
  const [isMuted, setIsMuted] = useState<boolean>(initialState.isMuted);
  const [repeatMode, setRepeatMode] = useState<'off' | 'all' | 'one'>(initialState.repeatMode);
  const [isShuffled, setIsShuffled] = useState<boolean>(initialState.isShuffled);
  const [queue, setQueue] = useState<PlayerTrack[]>(initialState.queue);
  const [isQueueOpen, setIsQueueOpen] = useState<boolean>(false);

  // Play history for back button tracking
  const historyRef = useRef<PlayerTrack[]>([]);

  // Initialize audio element once
  useEffect(() => {
    const audio = new Audio();
    audio.preload = 'metadata';
    audioRef.current = audio;

    audio.volume = initialState.isMuted ? 0 : initialState.volume;

    if (initialState.currentTrack) {
      audio.src = api.getPlayerStreamUrl(initialState.currentTrack.path);
      if (initialState.currentTime > 0) {
        audio.currentTime = initialState.currentTime;
      }
    }

    const onPlay = () => setIsPlaying(true);
    const onPause = () => setIsPlaying(false);
    const onTimeUpdate = () => {
      if (audioRef.current) {
        setCurrentTime(audioRef.current.currentTime);
      }
    };
    const onLoadedMetadata = () => {
      if (audioRef.current) {
        setDuration(audioRef.current.duration || 0);
      }
    };
    const onError = (e: Event) => {
      console.warn('Audio playback error:', e);
      setIsPlaying(false);
    };

    audio.addEventListener('play', onPlay);
    audio.addEventListener('pause', onPause);
    audio.addEventListener('timeupdate', onTimeUpdate);
    audio.addEventListener('loadedmetadata', onLoadedMetadata);
    audio.addEventListener('error', onError);

    return () => {
      audio.pause();
      audio.removeEventListener('play', onPlay);
      audio.removeEventListener('pause', onPause);
      audio.removeEventListener('timeupdate', onTimeUpdate);
      audio.removeEventListener('loadedmetadata', onLoadedMetadata);
      audio.removeEventListener('error', onError);
    };
  }, []);

  // Save state to localStorage periodically and on state changes
  useEffect(() => {
    const state: PlayerStorageState = {
      currentTrack,
      currentTime,
      volume,
      isMuted,
      repeatMode,
      isShuffled,
      queue,
    };
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (e) {
      console.warn('Error saving player state to localStorage', e);
    }
  }, [currentTrack, currentTime, volume, isMuted, repeatMode, isShuffled, queue]);

  const resume = useCallback(() => {
    if (!audioRef.current || !currentTrack) return;
    audioRef.current.play().catch((err) => {
      console.warn('Audio resume interrupted:', err);
    });
  }, [currentTrack]);

  const pause = useCallback(() => {
    if (!audioRef.current) return;
    audioRef.current.pause();
  }, []);

  const togglePlay = useCallback(() => {
    if (isPlaying) {
      pause();
    } else {
      resume();
    }
  }, [isPlaying, pause, resume]);

  const seek = useCallback((seconds: number) => {
    if (!audioRef.current) return;
    const clamped = Math.max(0, Math.min(seconds, duration || seconds));
    audioRef.current.currentTime = clamped;
    setCurrentTime(clamped);
  }, [duration]);

  const setVolume = useCallback((val: number) => {
    const clamped = Math.max(0, Math.min(1, val));
    setVolumeState(clamped);
    if (audioRef.current) {
      audioRef.current.volume = isMuted ? 0 : clamped;
    }
    if (clamped > 0 && isMuted) {
      setIsMuted(false);
    }
  }, [isMuted]);

  const toggleMute = useCallback(() => {
    setIsMuted((prev) => {
      const next = !prev;
      if (audioRef.current) {
        audioRef.current.volume = next ? 0 : volume;
      }
      return next;
    });
  }, [volume]);

  const toggleShuffle = useCallback(() => {
    setIsShuffled((prev) => !prev);
  }, []);

  const toggleRepeat = useCallback(() => {
    setRepeatMode((prev) => {
      if (prev === 'off') return 'all';
      if (prev === 'all') return 'one';
      return 'off';
    });
  }, []);

  const playTrack = useCallback((track: PlayerTrack, newQueue?: PlayerTrack[]) => {
    if (currentTrack) {
      historyRef.current.push(currentTrack);
    }
    setCurrentTrack(track);
    setDuration(track.duration || 0);
    setCurrentTime(0);

    if (newQueue) {
      // Filter out the selected track from newQueue
      const filtered = newQueue.filter((t) => t.path !== track.path);
      setQueue(filtered);
    }

    if (audioRef.current) {
      audioRef.current.src = api.getPlayerStreamUrl(track.path);
      audioRef.current.currentTime = 0;
      audioRef.current.play().catch((err) => {
        console.warn('Playback error playing track:', err);
      });
    }
  }, [currentTrack]);

  const nextTrack = useCallback(() => {
    if (queue.length > 0) {
      let nextIndex = 0;
      if (isShuffled && queue.length > 1) {
        nextIndex = Math.floor(Math.random() * queue.length);
      }
      const next = queue[nextIndex];
      const remaining = queue.filter((_, i) => i !== nextIndex);
      setQueue(remaining);
      playTrack(next);
    } else if (repeatMode === 'all' && historyRef.current.length > 0) {
      // Loop history
      const next = historyRef.current[0];
      historyRef.current = historyRef.current.slice(1);
      playTrack(next);
    } else {
      pause();
    }
  }, [queue, isShuffled, repeatMode, playTrack, pause]);

  const previousTrack = useCallback(() => {
    if (audioRef.current && audioRef.current.currentTime > 3) {
      // If played more than 3 seconds, replay from beginning
      seek(0);
      return;
    }
    if (historyRef.current.length > 0) {
      const prev = historyRef.current.pop()!;
      // Put current track back to top of queue
      if (currentTrack) {
        setQueue((q) => [currentTrack, ...q]);
      }
      playTrack(prev);
    } else {
      seek(0);
    }
  }, [currentTrack, playTrack, seek]);

  // Handle track ended
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const onEnded = () => {
      if (repeatMode === 'one') {
        audio.currentTime = 0;
        audio.play().catch(console.warn);
      } else {
        nextTrack();
      }
    };

    audio.addEventListener('ended', onEnded);
    return () => audio.removeEventListener('ended', onEnded);
  }, [repeatMode, nextTrack]);

  const addToQueue = useCallback((track: PlayerTrack) => {
    setQueue((prev) => [...prev, track]);
  }, []);

  const removeFromQueue = useCallback((index: number) => {
    setQueue((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const clearQueue = useCallback(() => {
    setQueue([]);
  }, []);

  const toggleQueueOpen = useCallback(() => {
    setIsQueueOpen((prev) => !prev);
  }, []);

  const toggleFavorite = useCallback(async (trackPath: string) => {
    try {
      const res = await api.togglePlayerFavorite(trackPath);
      // Update in currentTrack
      setCurrentTrack((prev) => {
        if (prev && prev.path === trackPath) {
          return { ...prev, is_favorite: res.is_favorite };
        }
        return prev;
      });
      // Update in queue
      setQueue((prev) =>
        prev.map((t) => (t.path === trackPath ? { ...t, is_favorite: res.is_favorite } : t))
      );
    } catch (e) {
      console.error('Failed to toggle favorite', e);
    }
  }, []);

  const updateTrackInState = useCallback((track: PlayerTrack) => {
    setCurrentTrack((prev) => (prev && prev.path === track.path ? track : prev));
    setQueue((prev) => prev.map((t) => (t.path === track.path ? track : t)));
  }, []);

  return (
    <AudioPlayerContext.Provider
      value={{
        currentTrack,
        isPlaying,
        currentTime,
        duration,
        volume,
        isMuted,
        repeatMode,
        isShuffled,
        queue,
        isQueueOpen,
        playTrack,
        togglePlay,
        pause,
        resume,
        seek,
        setVolume,
        toggleMute,
        toggleShuffle,
        toggleRepeat,
        nextTrack,
        previousTrack,
        addToQueue,
        removeFromQueue,
        clearQueue,
        toggleQueueOpen,
        setIsQueueOpen,
        toggleFavorite,
        updateTrackInState,
      }}
    >
      {children}
    </AudioPlayerContext.Provider>
  );
};

export const useAudioPlayer = () => {
  const ctx = useContext(AudioPlayerContext);
  if (!ctx) {
    throw new Error('useAudioPlayer must be used within an AudioPlayerProvider');
  }
  return ctx;
};
