import React, { useState } from 'react';
import { useAudioPlayer } from '../../context/AudioPlayerContext';
import { PlayerTrack, PlayerPlaylist } from '../../api/types';
import { api } from '../../api/client';
import {
  X,
  Disc,
  ListMusic,
  Heart,
  Edit2,
  Trash2,
  Music,
  Play,
  Copy,
  Check,
  Volume2,
  FileAudio,
  Calendar,
  Clock,
  HardDrive,
  FolderOpen,
} from 'lucide-react';

interface PlayerRightSidebarProps {
  width: number;
  onEditTrack?: (track: PlayerTrack) => void;
  playlists?: PlayerPlaylist[];
  onAddToPlaylist?: (playlistId: number, trackPath: string) => void;
}

export const PlayerRightSidebar: React.FC<PlayerRightSidebarProps> = ({
  width,
  onEditTrack,
}) => {
  const {
    rightPanelTab,
    setRightPanelTab,
    currentTrack,
    isPlaying,
    queue,
    removeFromQueue,
    clearQueue,
    playTrack,
    toggleFavorite,
  } = useAudioPlayer();

  const [copiedPath, setCopiedPath] = useState(false);

  if (!rightPanelTab) return null;

  const formatDuration = (secs?: number) => {
    if (!secs || isNaN(secs)) return '0:00';
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes || bytes <= 0) return 'Không rõ';
    const mb = bytes / (1024 * 1024);
    if (mb >= 1) return `${mb.toFixed(1)} MB`;
    const kb = bytes / 1024;
    return `${kb.toFixed(0)} KB`;
  };

  const handleCopyPath = () => {
    if (!currentTrack?.path) return;
    navigator.clipboard.writeText(currentTrack.path);
    setCopiedPath(true);
    setTimeout(() => setCopiedPath(false), 2000);
  };

  return (
    <aside
      style={{ width: `${width}px` }}
      className="shrink-0 bg-[#09090b]/95 border-l border-white/10 flex flex-col h-full select-none text-zinc-300 transition-[width] duration-75 overflow-hidden z-20"
    >
      {/* Top Header & Tab Switcher */}
      <div className="h-12 px-3 border-b border-white/10 flex items-center justify-between gap-2 shrink-0 bg-white/[0.02]">
        <div className="flex items-center gap-1 p-0.5 rounded-lg bg-zinc-900 border border-white/10">
          <button
            type="button"
            onClick={() => setRightPanelTab('now-playing')}
            className={`px-2.5 py-1 text-xs rounded-md font-medium flex items-center gap-1.5 transition-all ${
              rightPanelTab === 'now-playing'
                ? 'bg-zinc-800 text-emerald-400 shadow-sm'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <Disc className="w-3.5 h-3.5" />
            <span>Đang phát</span>
          </button>

          <button
            type="button"
            onClick={() => setRightPanelTab('queue')}
            className={`px-2.5 py-1 text-xs rounded-md font-medium flex items-center gap-1.5 transition-all ${
              rightPanelTab === 'queue'
                ? 'bg-zinc-800 text-emerald-400 shadow-sm'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <ListMusic className="w-3.5 h-3.5" />
            <span>Hàng đợi</span>
            {queue.length > 0 && (
              <span className="text-[10px] font-mono px-1 rounded-full bg-emerald-500/20 text-emerald-300">
                {queue.length}
              </span>
            )}
          </button>
        </div>

        <div className="flex items-center gap-1">
          {rightPanelTab === 'queue' && queue.length > 0 && (
            <button
              type="button"
              onClick={clearQueue}
              className="p-1.5 text-zinc-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors"
              title="Xóa toàn bộ hàng đợi"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}

          <button
            type="button"
            onClick={() => setRightPanelTab(null)}
            className="p-1.5 text-zinc-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
            title="Thu gọn bảng (Esc)"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Panel Body */}
      <div className="flex-1 overflow-y-auto min-h-0 p-4 space-y-5">
        {rightPanelTab === 'now-playing' ? (
          currentTrack ? (
            <div className="space-y-5 animate-in fade-in duration-150">
              {/* Large Cover Art */}
              <div className="relative aspect-square w-full rounded-2xl overflow-hidden bg-zinc-900 border border-white/10 shadow-2xl group flex items-center justify-center">
                {currentTrack.has_cover_art ? (
                  <img
                    src={api.getPlayerArtUrl(currentTrack.path)}
                    alt={currentTrack.title}
                    className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                  />
                ) : (
                  <div className="flex flex-col items-center justify-center text-zinc-600 gap-2">
                    <Music className="w-16 h-16 opacity-30" />
                    <span className="text-[11px]">Không có ảnh bìa nhúng</span>
                  </div>
                )}

                {/* Playing floating badge */}
                {isPlaying && (
                  <div className="absolute top-3 left-3 px-2 py-0.5 rounded-full bg-black/60 backdrop-blur-md border border-white/10 flex items-center gap-1.5 text-[10px] font-medium text-emerald-400 shadow-md">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    <span>Đang phát</span>
                  </div>
                )}
              </div>

              {/* Title & Artist & Quick Actions */}
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <h2
                      className="text-base font-bold text-zinc-100 hover:text-emerald-400 transition-colors cursor-pointer break-words leading-snug"
                      onClick={() => onEditTrack?.(currentTrack)}
                      title="Nhấn để sửa thông tin bài hát"
                    >
                      {currentTrack.title || currentTrack.filename}
                    </h2>
                    <p className="text-xs text-zinc-400 mt-0.5 break-words">
                      {currentTrack.artist || 'Không rõ nghệ sĩ'}
                    </p>
                    {currentTrack.album && (
                      <p className="text-[11px] text-zinc-500 mt-0.5 truncate">
                        Album: {currentTrack.album}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-1 shrink-0">
                    <button
                      type="button"
                      onClick={() => toggleFavorite(currentTrack.path)}
                      className={`p-2 rounded-xl border transition-all ${
                        currentTrack.is_favorite
                          ? 'bg-rose-500/10 border-rose-500/20 text-rose-500 shadow-sm'
                          : 'bg-white/[0.04] border-white/10 text-zinc-400 hover:text-white'
                      }`}
                      title={currentTrack.is_favorite ? 'Bỏ thích' : 'Yêu thích'}
                    >
                      <Heart
                        className={`w-4 h-4 ${
                          currentTrack.is_favorite ? 'fill-rose-500' : ''
                        }`}
                      />
                    </button>

                    <button
                      type="button"
                      onClick={() => onEditTrack?.(currentTrack)}
                      className="p-2 rounded-xl bg-white/[0.04] border border-white/10 text-zinc-400 hover:text-white hover:bg-white/[0.08] transition-all"
                      title="Chỉnh sửa thông tin thẻ (ID3/Metadata)"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>

              {/* Technical Details Breakdown */}
              <div className="rounded-2xl bg-white/[0.03] border border-white/10 p-3.5 space-y-3">
                <span className="text-[10px] font-mono tracking-wider uppercase text-zinc-500 block">
                  Thông số tệp âm thanh
                </span>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="flex items-center gap-2 p-2 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                    <Clock className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <div className="min-w-0">
                      <span className="text-[10px] text-zinc-500 block">Thời lượng</span>
                      <span className="font-mono text-zinc-200">
                        {formatDuration(currentTrack.duration)}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 p-2 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                    <HardDrive className="w-3.5 h-3.5 text-blue-400 shrink-0" />
                    <div className="min-w-0">
                      <span className="text-[10px] text-zinc-500 block">Dung lượng</span>
                      <span className="font-mono text-zinc-200">
                        {formatFileSize(currentTrack.file_size)}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 p-2 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                    <FileAudio className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                    <div className="min-w-0">
                      <span className="text-[10px] text-zinc-500 block">Định dạng</span>
                      <span className="font-mono uppercase text-zinc-200">
                        {currentTrack.filename.split('.').pop() || 'AUDIO'}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 p-2 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                    <Calendar className="w-3.5 h-3.5 text-purple-400 shrink-0" />
                    <div className="min-w-0">
                      <span className="text-[10px] text-zinc-500 block">Năm / Thể loại</span>
                      <span className="text-zinc-200 truncate block">
                        {currentTrack.year || currentTrack.genre || 'Chưa đặt'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Path copy */}
                <div className="pt-1">
                  <div className="flex items-center justify-between text-[10px] text-zinc-500 mb-1">
                    <span className="flex items-center gap-1">
                      <FolderOpen className="w-3 h-3" />
                      <span>Đường dẫn tệp cục bộ</span>
                    </span>
                    <button
                      type="button"
                      onClick={handleCopyPath}
                      className="text-emerald-400 hover:underline flex items-center gap-1 cursor-pointer"
                    >
                      {copiedPath ? (
                        <>
                          <Check className="w-3 h-3 text-emerald-400" />
                          <span>Đã chép</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" />
                          <span>Sao chép</span>
                        </>
                      )}
                    </button>
                  </div>
                  <div
                    className="p-2 rounded-lg bg-zinc-950/80 border border-white/5 font-mono text-[10px] text-zinc-400 break-all select-all hover:text-zinc-200 transition-colors"
                    title={currentTrack.path}
                  >
                    {currentTrack.path}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="h-64 flex flex-col items-center justify-center text-center p-6 text-zinc-500 space-y-3">
              <Disc className="w-12 h-12 opacity-30 text-zinc-400" />
              <p className="text-xs font-medium text-zinc-300">Chưa có bài hát nào đang phát</p>
              <p className="text-[11px] text-zinc-500">
                Chọn một bài hát từ danh sách để bắt đầu nghe và xem thông tin chi tiết.
              </p>
            </div>
          )
        ) : (
          /* Queue Tab */
          <div className="space-y-4 animate-in fade-in duration-150">
            {/* Active song in Queue */}
            {currentTrack && (
              <div className="space-y-1.5">
                <span className="text-[10px] font-mono tracking-wider uppercase text-zinc-500">
                  Đang phát
                </span>
                <div className="flex items-center gap-2.5 p-2 rounded-xl bg-white/[0.04] border border-white/10">
                  <div className="w-9 h-9 rounded-lg overflow-hidden bg-zinc-900 shrink-0 border border-white/10 flex items-center justify-center">
                    {currentTrack.has_cover_art ? (
                      <img
                        src={api.getPlayerArtUrl(currentTrack.path)}
                        alt={currentTrack.title}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <Music className="w-4 h-4 text-zinc-500" />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-semibold text-emerald-400 truncate">
                      {currentTrack.title || currentTrack.filename}
                    </p>
                    <p className="text-[10px] text-zinc-400 truncate">
                      {currentTrack.artist || 'Không rõ nghệ sĩ'}
                    </p>
                  </div>
                  {isPlaying ? (
                    <Volume2 className="w-3.5 h-3.5 text-emerald-400 animate-pulse shrink-0" />
                  ) : (
                    <span className="text-[10px] text-zinc-500 font-mono">
                      {formatDuration(currentTrack.duration)}
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Upcoming Queue */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono tracking-wider uppercase text-zinc-500">
                  Tiếp theo trong hàng đợi ({queue.length})
                </span>
              </div>

              {queue.length === 0 ? (
                <div className="py-10 text-center text-zinc-500 space-y-2">
                  <ListMusic className="w-8 h-8 opacity-30 mx-auto" />
                  <p className="text-xs font-medium text-zinc-400">Hàng đợi đang trống</p>
                  <p className="text-[11px] text-zinc-600 max-w-[200px] mx-auto">
                    Chọn "Thêm vào hàng đợi" từ menu bài hát bất kỳ để đưa bài hát vào đây.
                  </p>
                </div>
              ) : (
                <div className="space-y-1">
                  {queue.map((track, idx) => (
                    <div
                      key={`${track.path}-${idx}`}
                      className="group flex items-center gap-2 p-2 rounded-xl hover:bg-white/[0.04] transition-colors border border-transparent hover:border-white/5"
                    >
                      <button
                        type="button"
                        onClick={() => playTrack(track)}
                        className="w-8 h-8 rounded-lg bg-zinc-900 shrink-0 border border-white/10 flex items-center justify-center relative overflow-hidden group-hover:border-white/20"
                        title="Phát ngay"
                      >
                        {track.has_cover_art ? (
                          <img
                            src={api.getPlayerArtUrl(track.path)}
                            alt={track.title}
                            className="w-full h-full object-cover group-hover:opacity-40"
                          />
                        ) : (
                          <Music className="w-3.5 h-3.5 text-zinc-500 group-hover:opacity-0" />
                        )}
                        <Play className="w-3.5 h-3.5 text-white absolute opacity-0 group-hover:opacity-100 transition-opacity fill-current" />
                      </button>

                      <div
                        className="min-w-0 flex-1 cursor-pointer"
                        onClick={() => playTrack(track)}
                      >
                        <p className="text-xs font-medium text-zinc-200 group-hover:text-emerald-400 transition-colors truncate">
                          {track.title || track.filename}
                        </p>
                        <p className="text-[10px] text-zinc-400 truncate">
                          {track.artist || 'Không rõ nghệ sĩ'}
                        </p>
                      </div>

                      <div className="flex items-center gap-1.5 shrink-0">
                        <span className="text-[10px] font-mono text-zinc-500 group-hover:hidden">
                          {formatDuration(track.duration)}
                        </span>
                        <button
                          type="button"
                          onClick={() => removeFromQueue(idx)}
                          className="p-1 rounded-md text-zinc-500 hover:text-rose-400 hover:bg-rose-500/10 opacity-0 group-hover:opacity-100 transition-all"
                          title="Xóa khỏi hàng đợi"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};
