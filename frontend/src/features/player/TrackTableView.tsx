import React, { useState } from 'react';
import { PlayerTrack, PlayerPlaylist } from '../../api/types';
import { useAudioPlayer } from '../../context/AudioPlayerContext';
import { api } from '../../api/client';
import {
  Play,
  Pause,
  Heart,
  MoreHorizontal,
  Music,
  Plus,
  Edit,
  Trash2,
  Volume2,
  ListPlus,
  Clock,
} from 'lucide-react';

interface TrackTableViewProps {
  tracks: PlayerTrack[];
  playlists: PlayerPlaylist[];
  onEditTrack: (track: PlayerTrack) => void;
  onAddToPlaylist: (playlistId: number, trackPath: string) => void;
  onRemoveFromPlaylist?: (trackPath: string) => void;
  isPlaylistView?: boolean;
}

export const TrackTableView: React.FC<TrackTableViewProps> = ({
  tracks,
  playlists,
  onEditTrack,
  onAddToPlaylist,
  onRemoveFromPlaylist,
  isPlaylistView = false,
}) => {
  const { currentTrack, isPlaying, playTrack, togglePlay, addToQueue, toggleFavorite } =
    useAudioPlayer();

  const [activeMenuTrackPath, setActiveMenuTrackPath] = useState<string | null>(null);
  const [showPlaylistSubmenu, setShowPlaylistSubmenu] = useState(false);

  const formatDuration = (seconds?: number) => {
    if (!seconds || isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleRowClick = (track: PlayerTrack) => {
    if (currentTrack?.path === track.path) {
      togglePlay();
    } else {
      playTrack(track, tracks);
    }
  };

  return (
    <div className="flex-1 min-h-0 overflow-y-auto px-4 pb-6 select-none">
      <table className="w-full text-left border-collapse table-fixed">
        {/* Table Header */}
        <thead className="sticky top-0 z-20 bg-[#09090b]/95 backdrop-blur-md border-b border-white/10 text-[11px] font-mono uppercase tracking-wider text-zinc-400">
          <tr>
            <th className="w-12 py-3 px-2 text-center font-medium">#</th>
            <th className="py-3 px-3 font-medium">Tiêu đề</th>
            <th className="w-1/4 py-3 px-3 hidden md:table-cell font-medium">Album</th>
            <th className="w-20 py-3 px-3 text-right font-medium">
              <Clock className="w-4 h-4 ml-auto text-zinc-400" />
            </th>
            <th className="w-20 py-3 pr-4 text-right font-medium">
              <span className="sr-only">Thao tác</span>
            </th>
          </tr>
        </thead>

        {/* Table Body */}
        <tbody className="divide-y divide-white/[0.04] text-xs">
          {tracks.map((track, idx) => {
            const isCurrent = currentTrack?.path === track.path;
            const isMenuOpen = activeMenuTrackPath === track.path;

            return (
              <tr
                key={track.path}
                onClick={() => handleRowClick(track)}
                className={`group transition-colors cursor-pointer ${
                  isCurrent
                    ? 'bg-white/[0.08] text-white font-medium'
                    : 'hover:bg-white/[0.04] text-zinc-300'
                }`}
              >
                {/* Index / Play Button */}
                <td className="w-12 py-2 px-2 text-center align-middle relative">
                  <div className="flex items-center justify-center">
                    {isCurrent && isPlaying ? (
                      <Volume2 className="w-4 h-4 text-emerald-400 group-hover:hidden" />
                    ) : (
                      <span className="font-mono text-[11px] text-zinc-500 group-hover:hidden">
                        {idx + 1}
                      </span>
                    )}
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRowClick(track);
                      }}
                      className="hidden group-hover:flex items-center justify-center w-6 h-6 rounded-full bg-white text-zinc-950 hover:scale-105 transition-transform"
                    >
                      {isCurrent && isPlaying ? (
                        <Pause className="w-3 h-3 fill-current" />
                      ) : (
                        <Play className="w-3 h-3 fill-current ml-0.5" />
                      )}
                    </button>
                  </div>
                </td>

                {/* Title & Artist & Artwork */}
                <td className="py-2 px-3 align-middle">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-10 h-10 shrink-0 rounded-lg overflow-hidden bg-zinc-900 border border-white/10 flex items-center justify-center">
                      {track.has_cover_art ? (
                        <img
                          src={api.getPlayerArtUrl(track.path, track.mtime_ns)}
                          alt={track.title}
                          className="w-full h-full object-cover"
                          loading="lazy"
                        />
                      ) : (
                        <Music className="w-4 h-4 text-zinc-600" />
                      )}
                    </div>

                    <div className="min-w-0 flex-1">
                      <p
                        className={`truncate text-xs ${
                          isCurrent ? 'text-emerald-400 font-semibold' : 'text-zinc-100'
                        }`}
                        title={track.title || track.filename}
                      >
                        {track.title || track.filename}
                      </p>
                      <p
                        className="truncate text-[11px] text-zinc-400"
                        title={track.artist || 'Không rõ nghệ sĩ'}
                      >
                        {track.artist || 'Không rõ nghệ sĩ'}
                      </p>
                    </div>
                  </div>
                </td>

                {/* Album */}
                <td className="py-2 px-3 hidden md:table-cell align-middle">
                  <p
                    className="truncate text-xs text-zinc-400"
                    title={track.album || '—'}
                  >
                    {track.album || '—'}
                  </p>
                </td>

                {/* Duration */}
                <td className="w-20 py-2 px-3 text-right font-mono text-[11px] text-zinc-400 align-middle whitespace-nowrap">
                  {formatDuration(track.duration)}
                </td>

                {/* Actions & Heart */}
                <td className="w-20 py-2 pr-4 text-right align-middle relative">
                  <div className="flex items-center justify-end gap-1">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleFavorite(track.path);
                      }}
                      className={`p-1.5 rounded-full hover:bg-white/10 transition-all ${
                        track.is_favorite
                          ? 'opacity-100'
                          : 'opacity-0 group-hover:opacity-100'
                      }`}
                      title={track.is_favorite ? 'Bỏ thích' : 'Yêu thích'}
                    >
                      <Heart
                        className={`w-3.5 h-3.5 transition-colors ${
                          track.is_favorite
                            ? 'text-rose-500 fill-rose-500'
                            : 'text-zinc-400 hover:text-white'
                        }`}
                      />
                    </button>

                    <div className="relative">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveMenuTrackPath(isMenuOpen ? null : track.path);
                          setShowPlaylistSubmenu(false);
                        }}
                        className={`p-1.5 rounded-full text-zinc-400 hover:text-white hover:bg-white/10 transition-all ${
                          isMenuOpen ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
                        }`}
                        title="Tùy chọn khác"
                      >
                        <MoreHorizontal className="w-3.5 h-3.5" />
                      </button>

                      {/* Dropdown Menu */}
                      {isMenuOpen && (
                        <>
                          <div
                            className="fixed inset-0 z-40"
                            onClick={(e) => {
                              e.stopPropagation();
                              setActiveMenuTrackPath(null);
                            }}
                          />
                          <div className="absolute right-0 top-8 z-50 w-52 bg-zinc-900 border border-white/10 rounded-xl shadow-2xl py-1 text-xs text-zinc-200 text-left">
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                addToQueue(track);
                                setActiveMenuTrackPath(null);
                              }}
                              className="w-full px-3 py-2 hover:bg-white/10 flex items-center gap-2.5 transition-colors"
                            >
                              <ListPlus className="w-3.5 h-3.5 text-zinc-400" />
                              <span>Thêm vào hàng đợi</span>
                            </button>

                            {/* Add to Playlist Submenu Trigger */}
                            <div className="relative">
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setShowPlaylistSubmenu(!showPlaylistSubmenu);
                                }}
                                className="w-full px-3 py-2 hover:bg-white/10 flex items-center justify-between transition-colors"
                              >
                                <div className="flex items-center gap-2.5">
                                  <Plus className="w-3.5 h-3.5 text-zinc-400" />
                                  <span>Thêm vào playlist...</span>
                                </div>
                                <span className="text-[10px] text-zinc-500">▶</span>
                              </button>

                              {showPlaylistSubmenu && (
                                <div className="absolute left-full top-0 ml-1 w-44 bg-zinc-900 border border-white/10 rounded-xl shadow-2xl py-1 z-50 max-h-48 overflow-y-auto">
                                  {playlists.length === 0 ? (
                                    <div className="px-3 py-2 text-zinc-500 text-[11px]">
                                      Chưa có playlist
                                    </div>
                                  ) : (
                                    playlists.map((pl) => (
                                      <button
                                        key={pl.id}
                                        type="button"
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          onAddToPlaylist(pl.id, track.path);
                                          setActiveMenuTrackPath(null);
                                        }}
                                        className="w-full px-3 py-1.5 text-left hover:bg-white/10 truncate transition-colors text-zinc-300"
                                      >
                                        {pl.name}
                                      </button>
                                    ))
                                  )}
                                </div>
                              )}
                            </div>

                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                onEditTrack(track);
                                setActiveMenuTrackPath(null);
                              }}
                              className="w-full px-3 py-2 hover:bg-white/10 flex items-center gap-2.5 transition-colors"
                            >
                              <Edit className="w-3.5 h-3.5 text-zinc-400" />
                              <span>Sửa thông tin file...</span>
                            </button>

                            {isPlaylistView && onRemoveFromPlaylist && (
                              <>
                                <div className="h-px bg-white/10 my-1" />
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    onRemoveFromPlaylist(track.path);
                                    setActiveMenuTrackPath(null);
                                  }}
                                  className="w-full px-3 py-2 hover:bg-rose-500/10 text-rose-400 flex items-center gap-2.5 transition-colors"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                  <span>Xóa khỏi playlist</span>
                                </button>
                              </>
                            )}
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
