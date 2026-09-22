import React from 'react';
import { VideoListResponse } from '../api/types';
import { SongCard } from './SongCard';

interface ColumnPaneProps {
  title: string;
  group: 'music' | 'rest';
  data?: VideoListResponse;
  isLoading: boolean;
  selectedIds: Set<string>;
  onToggleSelect: (id: string) => void;
  onSelectAllPage: (ids: string[], checked: boolean) => void;
  onMove: (ids: string[], toGroup: 'music' | 'rest') => void;
  disabled?: boolean;
  search: string;
  reason: string;
  sort: string;
  page: number;
  pageSize: number;
  onUpdateFilters: (updates: {
    search?: string;
    reason?: string;
    sort?: 'watch_count' | 'title' | 'channel';
    page?: number;
    pageSize?: number;
  }) => void;
  onPageSizeChange?: (size: number) => void;
}

export const ColumnPane: React.FC<ColumnPaneProps> = ({
  title,
  group,
  data,
  isLoading,
  selectedIds,
  onToggleSelect,
  onSelectAllPage,
  onMove,
  disabled = false,
  search,
  reason,
  sort,
  page,
  pageSize,
  onUpdateFilters,
  onPageSizeChange,
}) => {
  const items = data?.items || [];
  const totalItems = data?.filtered_count || 0;
  const groupTotal = data?.group_totals[group] || 0;
  const maxPage = Math.max(1, Math.ceil(totalItems / pageSize));

  const pageIds = items.map((i) => i.id);
  const selectedOnPageCount = pageIds.filter((id) => selectedIds.has(id)).length;
  const allPageSelected = pageIds.length > 0 && selectedOnPageCount === pageIds.length;
  const isIndeterminate = selectedOnPageCount > 0 && !allPageSelected;

  const targetGroup = group === 'music' ? 'rest' : 'music';
  const bulkButtonText =
    group === 'music'
      ? selectedIds.size > 0
        ? `Chuyển sang Còn lại (${selectedIds.size}) →`
        : 'Chuyển sang Còn lại'
      : selectedIds.size > 0
        ? `← Thêm vào Nhạc (${selectedIds.size})`
        : 'Thêm vào Nhạc';

  return (
    <section className="flex flex-col flex-1 min-w-0 glass-panel rounded-2xl overflow-hidden border border-white/[0.08] shadow-2xl">
      {/* Compact Pane Header */}
      <div className="p-3.5 border-b border-white/[0.06] bg-zinc-950/40 flex flex-col gap-2.5">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-xs font-semibold tracking-wider text-zinc-300 uppercase flex items-center gap-2">
            <span>{title}</span>
            <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-zinc-800/80 border border-white/10 text-zinc-300">
              {groupTotal.toLocaleString('vi-VN')}
            </span>
          </h2>
          <span className="text-xs text-zinc-500 font-mono">
            {totalItems.toLocaleString('vi-VN')} bài
          </span>
        </div>

        {/* Unified Search & Filters Row */}
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <svg
              className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-500 pointer-events-none"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              placeholder="Tìm bài hát, nghệ sĩ..."
              value={search}
              onChange={(e) => onUpdateFilters({ search: e.target.value, page: 1 })}
              className="w-full pl-8 pr-3 py-1.5 text-xs rounded-lg glass-input text-zinc-200 placeholder-zinc-500"
            />
          </div>

          <select
            value={reason}
            onChange={(e) => onUpdateFilters({ reason: e.target.value, page: 1 })}
            className="w-32 px-2.5 py-1.5 text-xs rounded-lg glass-input text-zinc-300 cursor-pointer"
          >
            <option value="">Lý do: Tất cả</option>
            {group === 'music' ? (
              <>
                <option value="manual">Đã chuyển tay</option>
                <option value="topic_channel">Kênh Topic</option>
                <option value="music_library">Music library</option>
                <option value="ytmusic_strong">Metadata YouTube Music</option>
                <option value="ytmusic_ugc_recurrence">YTM · xem lại</option>
              </>
            ) : (
              <>
                <option value="unknown">Chưa rõ</option>
                <option value="music_hint">Dấu hiệu nhạc</option>
                <option value="talk_context">Ngữ cảnh podcast</option>
                <option value="conflicting_evidence">Mâu thuẫn</option>
                <option value="shorts_url">Shorts</option>
                <option value="channel_decision">Nhãn kênh</option>
              </>
            )}
          </select>

          <select
            value={sort}
            onChange={(e) => onUpdateFilters({ sort: e.target.value as any, page: 1 })}
            className="w-32 px-2.5 py-1.5 text-xs rounded-lg glass-input text-zinc-300 cursor-pointer"
          >
            <option value="watch_count">Xem nhiều</option>
            <option value="title">Tên A–Z</option>
            <option value="channel">Kênh A–Z</option>
          </select>
        </div>
      </div>

      {/* Action & Navigation Top Bar */}
      <div className="px-3.5 py-1.5 border-b border-white/[0.04] bg-zinc-900/40 flex items-center justify-between gap-2 text-xs">
        {/* Left: Select all page + Page size selector */}
        <div className="flex items-center gap-2.5">
          <label className="flex items-center gap-1.5 cursor-pointer select-none text-zinc-300 hover:text-white">
            <input
              type="checkbox"
              checked={allPageSelected}
              ref={(input) => {
                if (input) input.indeterminate = isIndeterminate;
              }}
              onChange={(e) => onSelectAllPage(pageIds, e.target.checked)}
              disabled={disabled || items.length === 0}
              className="rounded border-zinc-700 bg-zinc-900 text-sky-500 focus:ring-0 focus:ring-offset-0 cursor-pointer"
            />
            <span className="font-medium">Trang ({items.length})</span>
          </label>

          {onPageSizeChange && (
            <div className="flex items-center p-0.5 rounded-lg bg-zinc-900/80 border border-white/5 font-mono">
              {[10, 15, 25, 50].map((sz) => (
                <button
                  key={sz}
                  type="button"
                  onClick={() => onPageSizeChange(sz)}
                  className={`px-1.5 py-0.5 rounded text-xs transition-colors ${
                    pageSize === sz
                      ? 'bg-zinc-800 text-zinc-100 font-semibold shadow-xs'
                      : 'text-zinc-500 hover:text-zinc-300'
                  }`}
                  title={`${sz} bài mỗi trang`}
                >
                  {sz}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Right: Capsule Pagination Pill & Bulk Move Button */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-0.5 p-0.5 rounded-lg bg-zinc-900/80 border border-white/5 font-mono">
            <button
              type="button"
              disabled={page <= 1 || disabled}
              onClick={() => onUpdateFilters({ page: page - 1 })}
              className="w-6 h-6 rounded flex items-center justify-center text-zinc-400 hover:text-white hover:bg-white/5 disabled:opacity-30 disabled:pointer-events-none transition-colors"
              title="Trang trước"
            >
              ←
            </button>
            <span className="px-1.5 text-xs tabular-nums text-zinc-300">
              {page}/{maxPage}
            </span>
            <button
              type="button"
              disabled={page >= maxPage || disabled}
              onClick={() => onUpdateFilters({ page: page + 1 })}
              className="w-6 h-6 rounded flex items-center justify-center text-zinc-400 hover:text-white hover:bg-white/5 disabled:opacity-30 disabled:pointer-events-none transition-colors"
              title="Trang sau"
            >
              →
            </button>
          </div>

          <button
            type="button"
            disabled={disabled || selectedIds.size === 0}
            onClick={() => onMove(Array.from(selectedIds), targetGroup)}
            className={`px-2.5 py-1 text-xs font-medium rounded-lg border transition-all ${
              selectedIds.size > 0 && !disabled
                ? 'bg-sky-500 hover:bg-sky-400 text-white border-sky-400/30 shadow-md shadow-sky-500/20'
                : 'bg-zinc-900/80 text-zinc-600 border-zinc-800/80 cursor-not-allowed'
            }`}
          >
            {bulkButtonText}
          </button>
        </div>
      </div>

      {/* Songs Scrollable List */}
      <div className="flex-1 overflow-y-auto p-2.5 space-y-1 min-h-0">
        {isLoading ? (
          <div className="flex items-center justify-center h-48 text-zinc-500 text-xs font-mono">
            Đang tải danh sách...
          </div>
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-center text-zinc-500 text-xs px-6">
            <p>Không có video nào phù hợp với bộ lọc.</p>
            <p className="text-xs text-zinc-600 mt-1">Thử đổi từ khóa tìm kiếm hoặc chọn lý do khác.</p>
          </div>
        ) : (
          items.map((item) => (
            <SongCard
              key={item.id}
              item={item}
              selected={selectedIds.has(item.id)}
              onToggle={onToggleSelect}
              onQuickMove={(id) => onMove([id], targetGroup)}
              direction={group === 'music' ? 'to_rest' : 'to_music'}
              disabled={disabled}
            />
          ))
        )}
      </div>
    </section>
  );
};
