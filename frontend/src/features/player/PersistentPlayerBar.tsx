import React, { useState } from 'react';
import { useAudioPlayer } from '../../context/AudioPlayerContext';
import { api } from '../../api/client';
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Shuffle,
  Repeat,
  Repeat1,
  Volume2,
  VolumeX,
  Heart,
  ListMusic,
  Music,
  Disc,
  Keyboard,
} from 'lucide-react';

export const PersistentPlayerBar: React.FC<{ onEditTrack?: (trackPath: string) => void }> = ({
  onEditTrack,
}) => {
  const {
    currentTrack,
    isPlaying,
    currentTime,
    duration,
    volume,
    isMuted,
    repeatMode,
    isShuffled,
    queue,
    togglePlay,
    seek,
    setVolume,
    toggleMute,
    toggleShuffle,
    toggleRepeat,
    nextTrack,
    previousTrack,
    toggleFavorite,
    rightPanelTab,
    toggleRightPanel,
    setRightPanelTab,
    setIsShortcutsOpen,
  } = useAudioPlayer();

  const [isSeeking, setIsSeeking] = useState(false);
  const [seekValue, setSeekValue] = useState(0);

  const formatTime = (secs: number) => {
    if (!secs || isNaN(secs)) return '0:00';
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const handleSeekChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSeekValue(Number(e.target.value));
  };

  const handleSeekStart = () => {
    setIsSeeking(true);
    setSeekValue(currentTime);
  };

  const handleSeekEnd = () => {
    seek(seekValue);
    setIsSeeking(false);
  };

  const effectiveTime = isSeeking ? seekValue : currentTime;
  const progressPercent = duration > 0 ? (effectiveTime / duration) * 100 : 0;

  return (
    <footer className="h-20 shrink-0 z-50 bg-[#09090b]/95 backdrop-blur-2xl border-t border-white/10 px-4 md:px-6 flex items-center justify-between gap-4 select-none">
      {/* Left: Track Information & Favorite */}
      <div className="flex items-center gap-3 w-1/4 min-w-[200px] max-w-[320px]">
        {currentTrack ? (
          <>
            <div
              className="relative w-12 h-12 shrink-0 rounded-lg overflow-hidden bg-zinc-900 border border-white/10 cursor-pointer group"
              onClick={() => (onEditTrack ? onEditTrack(currentTrack.path) : setRightPanelTab('now-playing'))}
              title="Nhấn để xem thông tin bài hát (I)"
            >
              {currentTrack.has_cover_art ? (
                <img
                  src={api.getPlayerArtUrl(currentTrack.path, currentTrack.mtime_ns)}
                  alt={currentTrack.title}
                  className="w-full h-full object-cover transition-transform group-hover:scale-105"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <Music className="w-5 h-5 text-zinc-500" />
                </div>
              )}
            </div>

            <div className="min-w-0 flex-1">
              <p
                className="text-xs font-semibold text-zinc-100 truncate hover:underline cursor-pointer"
                title={currentTrack.title || currentTrack.filename}
                onClick={() => (onEditTrack ? onEditTrack(currentTrack.path) : setRightPanelTab('now-playing'))}
              >
                {currentTrack.title || currentTrack.filename}
              </p>
              <p
                className="text-[11px] text-zinc-400 truncate"
                title={currentTrack.artist || 'Không rõ nghệ sĩ'}
              >
                {currentTrack.artist || 'Không rõ nghệ sĩ'}
              </p>
            </div>

            <button
              type="button"
              onClick={() => toggleFavorite(currentTrack.path)}
              className="p-1.5 rounded-full hover:bg-white/10 transition-colors text-zinc-400 hover:text-white"
              title={currentTrack.is_favorite ? 'Bỏ thích' : 'Yêu thích'}
            >
              <Heart
                className={`w-4 h-4 transition-colors ${
                  currentTrack.is_favorite
                    ? 'text-rose-500 fill-rose-500'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              />
            </button>
          </>
        ) : (
          <div className="flex items-center gap-3 text-zinc-500 text-xs">
            <div className="w-12 h-12 rounded-lg bg-zinc-900 border border-white/5 flex items-center justify-center">
              <Music className="w-5 h-5 opacity-40" />
            </div>
            <span>Chưa chọn bài hát nào</span>
          </div>
        )}
      </div>

      {/* Center: Playback Controls & Progress Bar */}
      <div className="flex flex-col items-center gap-1.5 flex-1 max-w-[640px]">
        {/* Buttons */}
        <div className="flex items-center gap-4">
          {/* Shuffle */}
          <button
            type="button"
            onClick={toggleShuffle}
            disabled={!currentTrack}
            className={`p-1.5 rounded-full transition-colors ${
              isShuffled
                ? 'text-emerald-400 hover:text-emerald-300'
                : 'text-zinc-400 hover:text-zinc-200 disabled:opacity-30'
            }`}
            title={isShuffled ? 'Tắt phát ngẫu nhiên' : 'Bật phát ngẫu nhiên'}
          >
            <Shuffle className="w-4 h-4" />
          </button>

          {/* Previous */}
          <button
            type="button"
            onClick={previousTrack}
            disabled={!currentTrack}
            className="p-1.5 rounded-full text-zinc-300 hover:text-white disabled:opacity-30 transition-colors"
            title="Bài trước"
          >
            <SkipBack className="w-5 h-5 fill-current" />
          </button>

          {/* Play/Pause Main Button */}
          <button
            type="button"
            onClick={togglePlay}
            disabled={!currentTrack}
            className="w-9 h-9 rounded-full bg-white text-zinc-950 hover:bg-zinc-200 flex items-center justify-center shadow-lg transition-transform active:scale-95 disabled:opacity-40"
            title={isPlaying ? 'Tạm dừng' : 'Phát'}
          >
            {isPlaying ? (
              <Pause className="w-4 h-4 fill-current" />
            ) : (
              <Play className="w-4 h-4 fill-current ml-0.5" />
            )}
          </button>

          {/* Next */}
          <button
            type="button"
            onClick={nextTrack}
            disabled={!currentTrack}
            className="p-1.5 rounded-full text-zinc-300 hover:text-white disabled:opacity-30 transition-colors"
            title="Bài tiếp theo"
          >
            <SkipForward className="w-5 h-5 fill-current" />
          </button>

          {/* Repeat */}
          <button
            type="button"
            onClick={toggleRepeat}
            disabled={!currentTrack}
            className={`p-1.5 rounded-full transition-colors ${
              repeatMode !== 'off'
                ? 'text-emerald-400 hover:text-emerald-300'
                : 'text-zinc-400 hover:text-zinc-200 disabled:opacity-30'
            }`}
            title={
              repeatMode === 'off'
                ? 'Lặp lại toàn bộ'
                : repeatMode === 'all'
                ? 'Lặp lại 1 bài'
                : 'Tắt lặp lại'
            }
          >
            {repeatMode === 'one' ? (
              <Repeat1 className="w-4 h-4" />
            ) : (
              <Repeat className="w-4 h-4" />
            )}
          </button>
        </div>

        {/* Progress Bar & Timestamps */}
        <div className="w-full flex items-center gap-3 text-[11px] font-mono text-zinc-400">
          <span className="w-9 text-right shrink-0">{formatTime(effectiveTime)}</span>

          <div className="relative flex-1 flex items-center group h-3">
            {/* Custom Background Bar */}
            <div className="w-full h-1 bg-zinc-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-zinc-300 group-hover:bg-emerald-400 transition-colors"
                style={{ width: `${progressPercent}%` }}
              />
            </div>

            {/* Native Slider on Top */}
            <input
              type="range"
              min={0}
              max={duration || 100}
              step={0.1}
              value={effectiveTime}
              disabled={!currentTrack}
              onChange={handleSeekChange}
              onMouseDown={handleSeekStart}
              onMouseUp={handleSeekEnd}
              onTouchStart={handleSeekStart}
              onTouchEnd={handleSeekEnd}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer disabled:cursor-default"
            />
          </div>

          <span className="w-9 text-left shrink-0">{formatTime(duration)}</span>
        </div>
      </div>

      {/* Right: Volume & Queue */}
      <div className="flex items-center justify-end gap-3 w-1/4 min-w-[200px] max-w-[320px]">
        {/* Volume */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={toggleMute}
            className="p-1.5 rounded-full text-zinc-400 hover:text-white transition-colors"
            title={isMuted ? 'Bật âm lượng' : 'Tắt tiếng'}
          >
            {isMuted || volume === 0 ? (
              <VolumeX className="w-4 h-4 text-rose-400" />
            ) : (
              <Volume2 className="w-4 h-4" />
            )}
          </button>

          <div className="w-20 md:w-24 relative flex items-center group h-3">
            <div className="w-full h-1 bg-zinc-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-zinc-300 group-hover:bg-emerald-400 transition-colors"
                style={{ width: `${(isMuted ? 0 : volume) * 100}%` }}
              />
            </div>
            <input
              type="range"
              min={0}
              max={1}
              step={0.01}
              value={isMuted ? 0 : volume}
              onChange={(e) => setVolume(Number(e.target.value))}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
          </div>
        </div>

        {/* Now Playing View Toggle */}
        <button
          type="button"
          onClick={() => toggleRightPanel('now-playing')}
          className={`relative p-2 rounded-lg transition-colors ${
            rightPanelTab === 'now-playing'
              ? 'text-emerald-400 bg-white/10 shadow-sm'
              : 'text-zinc-400 hover:text-white hover:bg-white/10'
          }`}
          title="Xem thông tin bài đang phát (I)"
        >
          <Disc className="w-4 h-4" />
        </button>

        {/* Queue Toggle */}
        <button
          type="button"
          onClick={() => toggleRightPanel('queue')}
          className={`relative p-2 rounded-lg transition-colors ${
            rightPanelTab === 'queue'
              ? 'text-emerald-400 bg-white/10 shadow-sm'
              : 'text-zinc-400 hover:text-white hover:bg-white/10'
          }`}
          title="Mở danh sách hàng đợi (Q)"
        >
          <ListMusic className="w-4 h-4" />
          {queue.length > 0 && (
            <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-emerald-400" />
          )}
        </button>

        {/* Shortcuts Trigger */}
        <button
          type="button"
          onClick={() => setIsShortcutsOpen(true)}
          className="p-2 rounded-lg text-zinc-400 hover:text-white hover:bg-white/10 transition-colors"
          title="Phím tắt điều khiển (?)"
        >
          <Keyboard className="w-4 h-4" />
        </button>
      </div>
    </footer>
  );
};
