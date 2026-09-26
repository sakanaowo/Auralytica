import React from 'react';
import {
  Folder,
  RefreshCw,
  Search,
  LayoutList,
  LayoutGrid,
  ArrowUpDown,
} from 'lucide-react';

export type ViewMode = 'table' | 'grid';
export type SortOption = 'title_asc' | 'title_desc' | 'artist' | 'duration' | 'recent';

interface PlayerHeaderProps {
  currentFolder: string;
  onRescan: () => void;
  isScanning: boolean;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  viewMode: ViewMode;
  onViewModeChange: (m: ViewMode) => void;
  sortOption: SortOption;
  onSortOptionChange: (s: SortOption) => void;
  totalFilteredTracks: number;
}

export const PlayerHeader: React.FC<PlayerHeaderProps> = ({
  currentFolder,
  onRescan,
  isScanning,
  searchQuery,
  onSearchChange,
  viewMode,
  onViewModeChange,
  sortOption,
  onSortOptionChange,
  totalFilteredTracks,
}) => {
  return (
    <header className="shrink-0 p-4 border-b border-white/10 bg-[#09090b]/80 backdrop-blur-md flex flex-wrap items-center justify-between gap-4 select-none">
      {/* Folder Path & Rescan */}
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-zinc-900 border border-white/10 text-xs text-zinc-300 max-w-sm truncate">
          <Folder className="w-3.5 h-3.5 text-amber-400 shrink-0" />
          <span className="truncate font-mono text-[11px]" title={currentFolder}>
            {currentFolder || 'Thư mục nhạc mặc định'}
          </span>
        </div>

        <button
          type="button"
          onClick={onRescan}
          disabled={isScanning}
          className="px-2.5 py-1.5 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 text-zinc-300 hover:text-white text-xs font-medium transition-colors flex items-center gap-1.5 disabled:opacity-50"
          title="Quét lại thư viện nhạc"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isScanning ? 'animate-spin text-emerald-400' : ''}`} />
          <span className="hidden sm:inline">{isScanning ? 'Đang quét...' : 'Quét lại'}</span>
        </button>
      </div>

      {/* Search, Sort & View Mode Switcher */}
      <div className="flex items-center gap-3">
        {/* Search Input */}
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-zinc-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Tìm theo bài, nghệ sĩ, album..."
            className="w-48 sm:w-60 pl-8 pr-3 py-1.5 text-xs rounded-lg bg-zinc-900 border border-white/10 text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-zinc-400 transition-all"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => onSearchChange('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300 text-xs"
            >
              ✕
            </button>
          )}
        </div>

        {/* Sort Select */}
        <div className="flex items-center gap-1 px-2 py-1 rounded-lg bg-zinc-900 border border-white/10 text-xs text-zinc-300">
          <ArrowUpDown className="w-3.5 h-3.5 text-zinc-400" />
          <select
            value={sortOption}
            onChange={(e) => onSortOptionChange(e.target.value as SortOption)}
            className="bg-transparent text-xs text-zinc-300 focus:outline-none cursor-pointer pr-1"
          >
            <option value="title_asc" className="bg-zinc-900 text-zinc-200">
              Tên A → Z
            </option>
            <option value="title_desc" className="bg-zinc-900 text-zinc-200">
              Tên Z → A
            </option>
            <option value="artist" className="bg-zinc-900 text-zinc-200">
              Nghệ sĩ
            </option>
            <option value="duration" className="bg-zinc-900 text-zinc-200">
              Thời lượng
            </option>
            <option value="recent" className="bg-zinc-900 text-zinc-200">
              Mới cập nhật
            </option>
          </select>
        </div>

        {/* View Mode Toggle: Table ⟷ Grid */}
        <div className="flex items-center p-0.5 rounded-lg bg-zinc-900 border border-white/10">
          <button
            type="button"
            onClick={() => onViewModeChange('table')}
            className={`p-1.5 rounded-md transition-colors ${
              viewMode === 'table'
                ? 'bg-zinc-800 text-white shadow-sm'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
            title="Dạng bảng (Spotify)"
          >
            <LayoutList className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={() => onViewModeChange('grid')}
            className={`p-1.5 rounded-md transition-colors ${
              viewMode === 'grid'
                ? 'bg-zinc-800 text-white shadow-sm'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
            title="Dạng lưới thẻ (Apple Music)"
          >
            <LayoutGrid className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Count badge */}
        <span className="text-[11px] font-mono text-zinc-500 hidden md:inline">
          {totalFilteredTracks} bài
        </span>
      </div>
    </header>
  );
};
