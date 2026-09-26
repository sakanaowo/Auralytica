import React, { useState } from 'react';
import { PlayerTrack, PlayerPlaylist } from '../../api/types';
import { useAudioPlayer } from '../../context/AudioPlayerContext';
import { api } from '../../api/client';
import {
  Play,
  Pause,
  Heart,
  MoreVertical,
  Music,
  Plus,
  Edit,
  Trash2,
  Volume2,
  ListPlus,
} from 'lucide-react';

interface TrackGridViewProps {
  tracks: PlayerTrack[];
  playlists: PlayerPlaylist[];
  onEditTrack: (track: PlayerTrack) => void;
  onAddToPlaylist: (playlistId: number, trackPath: string) => void;
  onRemoveFromPlaylist?: (trackPath: string) => void;
  isPlaylistView?: boolean;
}

export const TrackGridView: React.FC<TrackGridViewProps> = ({
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

  const handleCardPlay = (track: PlayerTrack) => {
    if (currentTrack?.path === track.path) {
      togglePlay();
    } else {
      playTrack(track, tracks);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 pb-28 select-none">
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
        {tracks.map((track) => {
          const isCurrent = currentTrack?.path === track.path;
          const isMenuOpen = activeMenuTrackPath === track.path;

          return (
            <div
              key={track.path}
              onClick={() => handleCardPlay(track)}
              className="group flex flex-col p-3 rounded-2xl bg-white/[0.02] hover:bg-white/[0.06] border border-white/5 hover:border-white/10 transition-all cursor-pointer"
            >
              {/* Cover Art Container */}
              <div className="relative aspect-square w-full rounded-xl overflow-hidden bg-zinc-900 border border-white/10 shadow-md">
                {track.has_cover_art ? (
                  <img
                    src={api.getPlayerArtUrl(track.path)}
                    alt={track.title}
                    className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                    loading="lazy"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <Music className="w-10 h-10 text-zinc-600" />
                  </div>
                )}

                {/* Overlay on hover or active */}
                <div
                  className={`absolute inset-0 bg-black/40 backdrop-blur-[2px] flex items-center justify-center transition-opacity duration-200 ${
                    isCurrent || isMenuOpen ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
                  }`}
                >
                  {/* Center Play/Pause button */}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleCardPlay(track);
                    }}
                    className="w-12 h-12 rounded-full bg-white text-zinc-950 flex items-center justify-center shadow-xl hover:scale-110 active:scale-95 transition-all"
                  >
                    {isCurrent && isPlaying ? (
                      <Pause className="w-5 h-5 fill-current" />
                    ) : (
                      <Play className="w-5 h-5 fill-current ml-0.5" />
                    )}
                  </button>

                  {/* Top-Right Favorite button */}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleFavorite(track.path);
                    }}
                    className="absolute top-2 right-2 p-1.5 rounded-full bg-black/40 hover:bg-black/60 text-white transition-colors"
                  >
                    <Heart
                      className={`w-4 h-4 transition-colors ${
                        track.is_favorite ? 'text-rose-500 fill-rose-500' : 'text-zinc-300'
                      }`}
                    />
                  </button>

                  {/* Bottom-Right Menu button */}
                  <div className="absolute bottom-2 right-2">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setActiveMenuTrackPath(isMenuOpen ? null : track.path);
                        setShowPlaylistSubmenu(false);
                      }}
                      className="p-1.5 rounded-full bg-black/40 hover:bg-black/60 text-white transition-colors"
                    >
                      <MoreVertical className="w-4 h-4" />
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
                        <div className="absolute right-0 bottom-8 z-50 w-52 bg-zinc-900 border border-white/10 rounded-xl shadow-2xl py-1 text-xs text-zinc-200 text-left">
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

                          {/* Add to Playlist Submenu */}
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

                {/* Now Playing indicator on Card */}
                {isCurrent && isPlaying && (
                  <div className="absolute top-2 left-2 px-2 py-0.5 rounded-full bg-emerald-500/90 text-zinc-950 font-mono text-[10px] font-bold flex items-center gap-1 shadow-md">
                    <Volume2 className="w-3 h-3" />
                    <span>Đang phát</span>
                  </div>
                )}
              </div>

              {/* Text Info */}
              <div className="pt-2.5 space-y-0.5">
                <p
                  className={`text-xs font-semibold truncate ${
                    isCurrent ? 'text-emerald-400' : 'text-zinc-100 group-hover:text-white'
                  }`}
                  title={track.title || track.filename}
                >
                  {track.title || track.filename}
                </p>
                <p
                  className="text-[11px] text-zinc-400 truncate"
                  title={track.artist || 'Không rõ nghệ sĩ'}
                >
                  {track.artist || 'Không rõ nghệ sĩ'}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
