import React from 'react';
import { PlayerPlaylist } from '../../api/types';
import {
  Music,
  Heart,
  Plus,
  Upload,
  MoreVertical,
  Download,
  Trash2,
  Edit2,
  ListMusic,
} from 'lucide-react';

export type PlayerNavSection =
  | { type: 'all' }
  | { type: 'favorites' }
  | { type: 'playlist'; id: number; name: string };

interface PlayerSidebarProps {
  currentSection: PlayerNavSection;
  onSelectSection: (section: PlayerNavSection) => void;
  playlists: PlayerPlaylist[];
  onOpenCreatePlaylist: () => void;
  onOpenImportM3U: () => void;
  onEditPlaylist: (playlist: PlayerPlaylist) => void;
  onDeletePlaylist: (id: number) => void;
  onExportM3U: (id: number) => void;
  favoritesCount?: number;
  totalTracksCount?: number;
}

export const PlayerSidebar: React.FC<PlayerSidebarProps> = ({
  currentSection,
  onSelectSection,
  playlists,
  onOpenCreatePlaylist,
  onOpenImportM3U,
  onEditPlaylist,
  onDeletePlaylist,
  onExportM3U,
  favoritesCount = 0,
  totalTracksCount = 0,
}) => {
  const [menuOpenId, setMenuOpenId] = React.useState<number | null>(null);

  return (
    <aside className="w-60 md:w-64 shrink-0 bg-[#09090b]/90 border-r border-white/10 flex flex-col h-full select-none text-zinc-300">
      {/* Main Navigation */}
      <div className="p-3 space-y-1">
        <span className="px-3 text-[10px] font-mono tracking-wider uppercase text-zinc-500">
          Thư viện của bạn
        </span>

        {/* All Tracks */}
        <button
          type="button"
          onClick={() => onSelectSection({ type: 'all' })}
          className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
            currentSection.type === 'all'
              ? 'bg-zinc-800 text-white border border-white/10 shadow-sm'
              : 'hover:bg-white/[0.04] text-zinc-400 hover:text-zinc-200'
          }`}
        >
          <div className="flex items-center gap-2.5">
            <Music className="w-4 h-4 text-emerald-400" />
            <span>Tất cả bài hát</span>
          </div>
          {totalTracksCount > 0 && (
            <span className="text-[11px] font-mono text-zinc-500">{totalTracksCount}</span>
          )}
        </button>

        {/* Favorites */}
        <button
          type="button"
          onClick={() => onSelectSection({ type: 'favorites' })}
          className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
            currentSection.type === 'favorites'
              ? 'bg-zinc-800 text-white border border-white/10 shadow-sm'
              : 'hover:bg-white/[0.04] text-zinc-400 hover:text-zinc-200'
          }`}
        >
          <div className="flex items-center gap-2.5">
            <Heart className="w-4 h-4 text-rose-500 fill-rose-500/20" />
            <span>Yêu thích</span>
          </div>
          {favoritesCount > 0 && (
            <span className="text-[11px] font-mono text-zinc-500">{favoritesCount}</span>
          )}
        </button>
      </div>

      <div className="h-px bg-white/10 mx-3 my-1" />

      {/* Playlists Section */}
      <div className="flex-1 flex flex-col min-h-0 p-3 pt-2">
        <div className="flex items-center justify-between px-3 pb-2">
          <span className="text-[10px] font-mono tracking-wider uppercase text-zinc-500">
            Playlists ({playlists.length})
          </span>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={onOpenImportM3U}
              className="p-1 rounded-md text-zinc-400 hover:text-white hover:bg-white/10 transition-colors"
              title="Import file M3U"
            >
              <Upload className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={onOpenCreatePlaylist}
              className="p-1 rounded-md text-zinc-400 hover:text-white hover:bg-white/10 transition-colors"
              title="Tạo playlist mới"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Playlist Items */}
        <div className="flex-1 overflow-y-auto space-y-0.5 pr-1">
          {playlists.length === 0 ? (
            <div className="p-4 text-center text-zinc-500 text-xs space-y-2">
              <p>Chưa có playlist nào.</p>
              <button
                type="button"
                onClick={onOpenCreatePlaylist}
                className="text-emerald-400 hover:underline text-xs"
              >
                + Tạo playlist đầu tiên
              </button>
            </div>
          ) : (
            playlists.map((pl) => {
              const isActive =
                currentSection.type === 'playlist' && currentSection.id === pl.id;
              const isMenuOpen = menuOpenId === pl.id;

              return (
                <div key={pl.id} className="relative group">
                  <button
                    type="button"
                    onClick={() =>
                      onSelectSection({ type: 'playlist', id: pl.id, name: pl.name })
                    }
                    className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                      isActive
                        ? 'bg-zinc-800 text-white border border-white/10 shadow-sm'
                        : 'hover:bg-white/[0.04] text-zinc-400 hover:text-zinc-200'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 truncate pr-2">
                      <ListMusic className="w-3.5 h-3.5 shrink-0 text-zinc-400 group-hover:text-white" />
                      <span className="truncate">{pl.name}</span>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      <span className="text-[11px] font-mono text-zinc-500">
                        {pl.track_count}
                      </span>
                    </div>
                  </button>

                  {/* Dropdown Menu Trigger on Hover */}
                  <div className="absolute right-1 top-1.5 hidden group-hover:block">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setMenuOpenId(isMenuOpen ? null : pl.id);
                      }}
                      className="p-1 rounded text-zinc-400 hover:text-white hover:bg-zinc-700/80 transition-colors"
                      title="Tùy chọn playlist"
                    >
                      <MoreVertical className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  {/* Dropdown Menu */}
                  {isMenuOpen && (
                    <>
                      <div
                        className="fixed inset-0 z-40"
                        onClick={() => setMenuOpenId(null)}
                      />
                      <div className="absolute right-0 top-8 z-50 w-36 bg-zinc-900 border border-white/10 rounded-lg shadow-xl py-1 text-xs text-zinc-200">
                        <button
                          type="button"
                          onClick={() => {
                            setMenuOpenId(null);
                            onEditPlaylist(pl);
                          }}
                          className="w-full px-3 py-1.5 text-left hover:bg-white/10 flex items-center gap-2 transition-colors"
                        >
                          <Edit2 className="w-3.5 h-3.5 text-zinc-400" />
                          <span>Đổi tên</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setMenuOpenId(null);
                            onExportM3U(pl.id);
                          }}
                          className="w-full px-3 py-1.5 text-left hover:bg-white/10 flex items-center gap-2 transition-colors"
                        >
                          <Download className="w-3.5 h-3.5 text-zinc-400" />
                          <span>Xuất M3U</span>
                        </button>
                        <div className="h-px bg-white/10 my-1" />
                        <button
                          type="button"
                          onClick={() => {
                            setMenuOpenId(null);
                            onDeletePlaylist(pl.id);
                          }}
                          className="w-full px-3 py-1.5 text-left hover:bg-rose-500/10 text-rose-400 flex items-center gap-2 transition-colors"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                          <span>Xóa</span>
                        </button>
                      </div>
                    </>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </aside>
  );
};
