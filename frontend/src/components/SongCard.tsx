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
      {/* 1:1 Square Squircle Album Cover (56x56px) */}
      <div className="relative w-14 h-14 shrink-0 rounded-xl overflow-hidden bg-zinc-900 border border-white/5 flex items-center justify-center shadow-sm">
        {!thumbError ? (
          <img
            src={`https://i.ytimg.com/vi/${item.id}/mqdefault.jpg`}
            alt=""
            loading="lazy"
            referrerPolicy="no-referrer"
            onError={() => setThumbError(true)}
            className="w-full h-full object-cover scale-105"
          />
        ) : (
          <div className="flex items-center justify-center w-full h-full text-zinc-600 bg-zinc-900/80">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
            </svg>
          </div>
        )}

        {/* Selected badge overlay */}
        {selected && (
          <div className="absolute inset-0 bg-sky-500/20 backdrop-blur-[1px] flex items-center justify-center">
            <span className="w-6 h-6 rounded-full bg-sky-500 text-white text-xs font-bold flex items-center justify-center shadow-md">
              ✓
            </span>
          </div>
        )}
      </div>

      {/* Track info */}
      <div className="flex-1 min-w-0 pr-14">
        <a
          href={`https://www.youtube.com/watch?v=${encodeURIComponent(item.id)}`}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="text-sm font-medium text-zinc-100 hover:text-white line-clamp-1 leading-snug transition-colors"
          title={item.title || item.id}
        >
          {item.title || item.id}
        </a>

        <div className="flex items-center gap-2 text-xs text-zinc-400 mt-1 truncate">
          <span className="truncate max-w-[220px] font-normal">{item.channel_name || 'Chưa rõ nghệ sĩ'}</span>
          <span className="text-zinc-600">·</span>
          <span className="tabular-nums font-mono text-zinc-500 text-xs">
            {item.watch_count.toLocaleString('vi-VN')} lượt
          </span>
        </div>
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
          className="text-xs font-medium px-2.5 py-1.5 rounded-lg bg-zinc-800/90 hover:bg-zinc-700 text-zinc-200 hover:text-white border border-white/10 transition-colors shadow-sm"
        >
          {direction === 'to_rest' ? 'Chuyển →' : '← Thêm'}
        </button>
      </div>
    </div>
  );
};

