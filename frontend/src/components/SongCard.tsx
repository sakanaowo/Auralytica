import React, { useState } from 'react';
import { VideoItem } from '../api/types';

interface SongCardProps {
  item: VideoItem;
  selected: boolean;
  onToggle: (id: string) => void;
  onQuickMove: (id: string) => void;
  direction: 'to_rest' | 'to_music';
  disabled?: boolean;
}

const REASON_LABELS: Record<string, string> = {
  ytmusic_strong: 'Metadata YouTube Music',
  ytmusic_ugc_recurrence: 'YTM · xem lại nhiều ngày',
  manual: 'Đã chuyển tay',
  topic_channel: 'Kênh Topic',
  music_library: 'Music library',
  music_hint: 'Có dấu hiệu nhạc',
  unknown: 'Chưa rõ',
  talk_context: 'Ngữ cảnh nói chuyện',
  conflicting_evidence: 'Bằng chứng mâu thuẫn',
  shorts_url: 'YouTube Shorts',
  channel_decision: 'Theo nhãn kênh',
};

export const SongCard: React.FC<SongCardProps> = ({
  item,
  selected,
  onToggle,
  onQuickMove,
  direction,
  disabled = false,
}) => {
  const [thumbError, setThumbError] = useState(false);

  return (
    <div
      onClick={() => {
        if (!disabled) onToggle(item.id);
      }}
      className={`group relative flex items-center gap-3.5 p-2.5 rounded-xl cursor-pointer select-none transition-all duration-150 ${
        selected ? 'glass-card-selected' : 'glass-card'
      } ${disabled ? 'opacity-50 pointer-events-none' : ''}`}
    >
      {/* 16:9 Thumbnail preview */}
      <div className="relative w-24 h-14 shrink-0 rounded-lg overflow-hidden bg-zinc-900 border border-white/5 flex items-center justify-center">
        {!thumbError ? (
          <img
            src={`https://i.ytimg.com/vi/${item.id}/mqdefault.jpg`}
            alt=""
            loading="lazy"
            referrerPolicy="no-referrer"
            onError={() => setThumbError(true)}
            className="w-full h-full object-cover"
          />
        ) : (
          <span className="text-zinc-600 text-[10px] tracking-wider uppercase font-mono">No Image</span>
        )}

        {/* Selected badge overlay */}
        {selected && (
          <div className="absolute inset-0 bg-zinc-950/40 flex items-center justify-center backdrop-blur-[2px]">
            <span className="text-xs font-bold text-white bg-zinc-800/90 border border-white/20 w-5 h-5 rounded-full flex items-center justify-center">
              ✓
            </span>
          </div>
        )}
      </div>

      {/* Video metadata */}
      <div className="flex-1 min-w-0 pr-16">
        <a
          href={`https://www.youtube.com/watch?v=${encodeURIComponent(item.id)}`}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="text-[13px] font-medium text-zinc-200 hover:text-white line-clamp-1 leading-snug transition-colors"
          title={item.title || item.id}
        >
          {item.title || item.id}
        </a>

        <div className="flex items-center gap-1.5 text-[11px] text-zinc-400 mt-1 truncate">
          <span className="truncate max-w-[180px]">{item.channel_name || 'Chưa rõ kênh'}</span>
          <span>·</span>
          <span className="tabular-nums">{item.watch_count} lượt</span>
          <span>·</span>
          <span className={item.decision_source === 'user' ? 'text-zinc-300 font-medium' : 'text-zinc-500'}>
            {REASON_LABELS[item.reason] || item.reason}
          </span>
        </div>

        {item.download_status && (
          <div className="text-[10px] text-zinc-500 mt-0.5">Trạng thái tải: {item.download_status}</div>
        )}
      </div>

      {/* Quick Move Action (Visible on hover or when selected) */}
      <div className="absolute right-3 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          type="button"
          disabled={disabled}
          onClick={(e) => {
            e.stopPropagation();
            onQuickMove(item.id);
          }}
          className="text-xs font-medium px-2.5 py-1 rounded-md bg-zinc-800 hover:bg-zinc-700 text-zinc-200 hover:text-white border border-white/10 transition-colors shadow-sm"
        >
          {direction === 'to_rest' ? 'Chuyển →' : '← Thêm'}
        </button>
      </div>
    </div>
  );
};
