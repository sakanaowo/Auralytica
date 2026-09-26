import React, { useEffect } from 'react';
import { useAudioPlayer } from '../../context/AudioPlayerContext';
import { X, Keyboard, Play, Volume2, LayoutTemplate } from 'lucide-react';

export const ShortcutsModal: React.FC = () => {
  const { isShortcutsOpen, setIsShortcutsOpen } = useAudioPlayer();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isShortcutsOpen) {
        setIsShortcutsOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isShortcutsOpen, setIsShortcutsOpen]);

  if (!isShortcutsOpen) return null;

  const sections = [
    {
      title: 'Điều khiển phát nhạc',
      icon: Play,
      items: [
        { label: 'Phát / Tạm dừng', keys: ['Space'] },
        { label: 'Bài tiếp theo', keys: ['→'] },
        { label: 'Bài trước đó', keys: ['←'] },
        { label: 'Tua tiến 5 giây', keys: ['Shift', '→'] },
        { label: 'Tua lùi 5 giây', keys: ['Shift', '←'] },
      ],
    },
    {
      title: 'Chế độ & Âm lượng',
      icon: Volume2,
      items: [
        { label: 'Bật / Tắt tiếng (Mute)', keys: ['M'] },
        { label: 'Bật / Tắt phát ngẫu nhiên', keys: ['S'] },
        { label: 'Chuyển chế độ lặp lại', keys: ['R'] },
      ],
    },
    {
      title: 'Giao diện & Cửa sổ',
      icon: LayoutTemplate,
      items: [
        { label: 'Bật / Tắt xem Đang phát (Now Playing)', keys: ['I'] },
        { label: 'Bật / Tắt Hàng đợi phát (Queue)', keys: ['Q'] },
        { label: 'Mở bảng phím tắt này', keys: ['?'] },
      ],
    },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm animate-in fade-in duration-150"
        onClick={() => setIsShortcutsOpen(false)}
      />

      {/* Modal Card */}
      <div className="relative w-full max-w-lg rounded-2xl bg-zinc-950 border border-white/10 p-6 shadow-2xl z-10 space-y-6 animate-in zoom-in-95 duration-150 select-none">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-white/10">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-white/[0.06] border border-white/10 text-emerald-400">
              <Keyboard className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-zinc-100">Phím tắt điều khiển</h2>
              <p className="text-[11px] text-zinc-400">Thao tác nhanh bàn phím kiểu Spotify</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setIsShortcutsOpen(false)}
            className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-white/10 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Shortcuts List */}
        <div className="space-y-5 max-h-[60vh] overflow-y-auto pr-1">
          {sections.map((sec) => {
            const Icon = sec.icon;
            return (
              <div key={sec.title} className="space-y-2">
                <div className="flex items-center gap-1.5 text-zinc-400 text-xs font-medium">
                  <Icon className="w-3.5 h-3.5 text-zinc-500" />
                  <span>{sec.title}</span>
                </div>
                <div className="space-y-1.5">
                  {sec.items.map((item) => (
                    <div
                      key={item.label}
                      className="flex items-center justify-between px-3 py-2 rounded-xl bg-white/[0.03] border border-white/[0.06] text-xs"
                    >
                      <span className="text-zinc-300">{item.label}</span>
                      <div className="flex items-center gap-1">
                        {item.keys.map((k) => (
                          <kbd
                            key={k}
                            className="min-w-6 px-2 py-0.5 text-center text-[11px] font-mono font-semibold rounded-md bg-zinc-800 border border-white/10 text-zinc-200 shadow-sm"
                          >
                            {k}
                          </kbd>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer Note */}
        <div className="pt-2 border-t border-white/10 flex items-center justify-between text-[11px] text-zinc-500">
          <span>Phím tắt tự động tắt khi bạn đang gõ trong ô tìm kiếm hoặc form.</span>
          <button
            type="button"
            onClick={() => setIsShortcutsOpen(false)}
            className="px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 font-medium transition-colors"
          >
            Đóng
          </button>
        </div>
      </div>
    </div>
  );
};
