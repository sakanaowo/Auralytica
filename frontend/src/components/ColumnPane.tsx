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
      {/* Pane Header */}
      <div className="p-4 border-b border-white/[0.06] bg-zinc-950/40">
        <div className="flex items-center justify-between gap-3 mb-3">
          <h2 className="text-xs font-semibold tracking-wider text-zinc-300 uppercase flex items-center gap-2">
            <span>{title}</span>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-zinc-800/80 border border-white/10 text-zinc-400">
              {groupTotal.toLocaleString('vi-VN')}
            </span>
          </h2>
          <span className="text-[11px] text-zinc-500 font-mono">
            {totalItems.toLocaleString('vi-VN')} khớp bộ lọc
          </span>
        </div>

        {/* Filters Row */}
        <div className="grid grid-cols-1 sm:grid-cols-12 gap-2">
          <input
            type="text"
            placeholder="Tìm kiếm tiêu đề hoặc kênh..."
            value={search}
            onChange={(e) => onUpdateFilters({ search: e.target.value, page: 1 })}
            className="sm:col-span-6 px-3 py-1.5 text-xs rounded-lg glass-input text-zinc-200 placeholder-zinc-500"
          />

          <select
            value={reason}
            onChange={(e) => onUpdateFilters({ reason: e.target.value, page: 1 })}
            className="sm:col-span-3 px-2 py-1.5 text-xs rounded-lg glass-input text-zinc-300 cursor-pointer"
          >
            <option value="">Mọi lý do</option>
            {group === 'music' ? (
              <>
                <option value="manual">Đã chuyển tay</option>
                <option value="topic_channel">Kênh Topic</option>
                <option value="music_library">Music library</option>
                <option value="ytmusic_strong">Metadata YouTube Music</option>
                <option value="ytmusic_ugc_recurrence">YTM · xem lại nhiều ngày</option>
              </>
            ) : (
              <>
                <option value="unknown">Chưa rõ</option>
                <option value="music_hint">Có dấu hiệu nhạc</option>
                <option value="talk_context">Ngữ cảnh nói chuyện</option>
                <option value="conflicting_evidence">Bằng chứng mâu thuẫn</option>
                <option value="shorts_url">YouTube Shorts</option>
                <option value="channel_decision">Nhãn kênh</option>
              </>
            )}
          </select>

          <select
            value={sort}
            onChange={(e) => onUpdateFilters({ sort: e.target.value as any, page: 1 })}
            className="sm:col-span-3 px-2 py-1.5 text-xs rounded-lg glass-input text-zinc-300 cursor-pointer"
          >
            <option value="watch_count">Xem nhiều nhất</option>
            <option value="title">Tiêu đề A–Z</option>
            <option value="channel">Kênh A–Z</option>
          </select>
        </div>
      </div>

      {/* Action Row */}
      <div className="px-4 py-2.5 border-b border-white/[0.04] bg-zinc-900/30 flex items-center justify-between gap-3 text-xs">
        <label className="flex items-center gap-2 cursor-pointer select-none text-zinc-300 hover:text-white">
          <input
            type="checkbox"
            checked={allPageSelected}
            ref={(input) => {
              if (input) input.indeterminate = isIndeterminate;
            }}
            onChange={(e) => onSelectAllPage(pageIds, e.target.checked)}
            disabled={disabled || items.length === 0}
            className="rounded border-zinc-700 bg-zinc-900 text-zinc-100 focus:ring-0 focus:ring-offset-0 cursor-pointer"
          />
          <span>Chọn cả trang ({items.length})</span>
        </label>

        <button
          type="button"
          disabled={disabled || selectedIds.size === 0}
          onClick={() => onMove(Array.from(selectedIds), targetGroup)}
          className={`px-3 py-1 text-xs font-medium rounded-lg border transition-all ${
            selectedIds.size > 0 && !disabled
              ? 'bg-zinc-100 text-zinc-900 hover:bg-white border-white shadow-md'
              : 'bg-zinc-900 text-zinc-600 border-zinc-800 cursor-not-allowed'
          }`}
        >
          {bulkButtonText}
        </button>
      </div>

      {/* Songs Scrollable List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2 min-h-[460px] max-h-[calc(100vh-290px)]">
        {isLoading ? (
          <div className="flex items-center justify-center h-48 text-zinc-500 text-xs font-mono">
            Đang tải danh sách...
          </div>
        ) : items.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-center text-zinc-500 text-xs px-6">
            <p>Không có video nào phù hợp với bộ lọc.</p>
            <p className="text-[11px] text-zinc-600 mt-1">Thử đổi từ khóa tìm kiếm hoặc chọn lý do khác.</p>
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

      {/* Pagination Footer */}
      <div className="p-3 border-t border-white/[0.06] bg-zinc-950/40 flex items-center justify-between text-xs text-zinc-400">
        <div className="flex items-center gap-2">
          <span>Hiện</span>
          <select
            value={pageSize}
            onChange={(e) => onUpdateFilters({ pageSize: Number(e.target.value), page: 1 })}
            className="px-2 py-1 text-xs rounded glass-input text-zinc-300 cursor-pointer"
          >
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
          <span>bài/trang</span>
        </div>

        <div className="flex items-center gap-3">
          <span className="tabular-nums font-mono text-[11px]">
            {page} / {maxPage}
          </span>
          <div className="flex items-center gap-1">
            <button
              type="button"
              disabled={page <= 1 || disabled}
              onClick={() => onUpdateFilters({ page: page - 1 })}
              className="px-2.5 py-1 rounded bg-zinc-900 border border-white/5 text-zinc-300 hover:text-white disabled:opacity-40 disabled:pointer-events-none transition-colors"
            >
              ←
            </button>
            <button
              type="button"
              disabled={page >= maxPage || disabled}
              onClick={() => onUpdateFilters({ page: page + 1 })}
              className="px-2.5 py-1 rounded bg-zinc-900 border border-white/5 text-zinc-300 hover:text-white disabled:opacity-40 disabled:pointer-events-none transition-colors"
            >
              →
            </button>
          </div>
        </div>
      </div>
    </section>
  );
};
