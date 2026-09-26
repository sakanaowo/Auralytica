import React from 'react';
import { useAudioPlayer } from '../../context/AudioPlayerContext';
import { api } from '../../api/client';
import { X, Trash2, Music, Play, Volume2 } from 'lucide-react';

export const QueueDrawer: React.FC = () => {
  const {
    isQueueOpen,
    setIsQueueOpen,
    currentTrack,
    isPlaying,
    queue,
    removeFromQueue,
    clearQueue,
    playTrack,
  } = useAudioPlayer();

  if (!isQueueOpen) return null;

  const formatDuration = (seconds?: number) => {
    if (!seconds || isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/40 backdrop-blur-xs z-40 transition-opacity"
        onClick={() => setIsQueueOpen(false)}
      />

      {/* Drawer */}
      <aside className="fixed top-0 bottom-20 right-0 w-80 md:w-96 bg-zinc-950/95 backdrop-blur-2xl border-l border-white/10 z-50 flex flex-col shadow-2xl animate-in slide-in-from-right duration-200">
        {/* Drawer Header */}
        <div className="p-4 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-zinc-100">Hàng đợi phát</h3>
            <span className="text-xs px-2 py-0.5 rounded-full bg-white/10 text-zinc-300 font-mono">
              {queue.length}
            </span>
          </div>

          <div className="flex items-center gap-1">
            {queue.length > 0 && (
              <button
                type="button"
                onClick={clearQueue}
                className="px-2 py-1 text-xs text-zinc-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-md transition-colors flex items-center gap-1"
                title="Xóa tất cả trong hàng đợi"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Xóa hết</span>
              </button>
            )}
            <button
              type="button"
              onClick={() => setIsQueueOpen(false)}
              className="p-1.5 text-zinc-400 hover:text-zinc-100 hover:bg-white/10 rounded-md transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {/* Now Playing Section */}
          {currentTrack && (
            <div className="space-y-2">
              <span className="text-[11px] font-mono tracking-wider uppercase text-zinc-400">
                Đang phát
              </span>
              <div className="flex items-center gap-3 p-2.5 rounded-xl bg-white/[0.04] border border-white/10">
                <div className="relative w-11 h-11 shrink-0 rounded-lg overflow-hidden bg-zinc-900 border border-white/10 flex items-center justify-center">
                  {currentTrack.has_cover_art ? (
                    <img
                      src={api.getPlayerArtUrl(currentTrack.path)}
                      alt={currentTrack.title}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <Music className="w-5 h-5 text-zinc-500" />
                  )}
                  {isPlaying && (
                    <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
                      <Volume2 className="w-4 h-4 text-emerald-400 animate-pulse" />
                    </div>
                  )}
                </div>

                <div className="min-w-0 flex-1">
                  <p className="text-xs font-semibold text-zinc-100 truncate">
                    {currentTrack.title || currentTrack.filename}
                  </p>
                  <p className="text-[11px] text-zinc-400 truncate">
                    {currentTrack.artist || 'Không rõ nghệ sĩ'}
                  </p>
                </div>

                <span className="text-[11px] font-mono text-zinc-500 shrink-0">
                  {formatDuration(currentTrack.duration)}
                </span>
              </div>
            </div>
          )}

          {/* Up Next Section */}
          <div className="space-y-2">
            <span className="text-[11px] font-mono tracking-wider uppercase text-zinc-400">
              Tiếp theo trong hàng đợi
            </span>

            {queue.length === 0 ? (
              <div className="py-12 text-center text-zinc-500 space-y-2">
                <Music className="w-8 h-8 mx-auto stroke-1 opacity-50" />
                <p className="text-xs">Hàng đợi phát đang trống</p>
                <p className="text-[11px] text-zinc-600">
                  Thêm bài hát vào hàng đợi từ danh sách nhạc để nghe liên tục.
                </p>
              </div>
            ) : (
              <div className="space-y-1">
                {queue.map((track, idx) => (
                  <div
                    key={`${track.path}-${idx}`}
                    className="group flex items-center gap-3 p-2 rounded-lg hover:bg-white/[0.04] transition-colors border border-transparent hover:border-white/5"
                  >
                    <div className="relative w-9 h-9 shrink-0 rounded-md overflow-hidden bg-zinc-900 border border-white/10 flex items-center justify-center">
                      {track.has_cover_art ? (
                        <img
                          src={api.getPlayerArtUrl(track.path)}
                          alt={track.title}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <Music className="w-4 h-4 text-zinc-600" />
                      )}
                      <button
                        type="button"
                        onClick={() => playTrack(track, queue.filter((_, i) => i !== idx))}
                        className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity text-white"
                      >
                        <Play className="w-3.5 h-3.5 fill-white" />
                      </button>
                    </div>

                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-medium text-zinc-200 truncate group-hover:text-white">
                        {track.title || track.filename}
                      </p>
                      <p className="text-[11px] text-zinc-400 truncate">
                        {track.artist || 'Không rõ nghệ sĩ'}
                      </p>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-[11px] font-mono text-zinc-500 group-hover:hidden">
                        {formatDuration(track.duration)}
                      </span>
                      <button
                        type="button"
                        onClick={() => removeFromQueue(idx)}
                        className="hidden group-hover:flex p-1 text-zinc-400 hover:text-rose-400 transition-colors"
                        title="Xóa khỏi hàng đợi"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </aside>
    </>
  );
};
