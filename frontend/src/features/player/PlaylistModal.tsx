import React, { useState, useEffect } from 'react';
import { PlayerPlaylist } from '../../api/types';
import { api } from '../../api/client';
import { X, ListMusic, Upload, Loader2, Save } from 'lucide-react';

interface PlaylistModalProps {
  mode: 'create' | 'edit' | 'import';
  playlist?: PlayerPlaylist | null;
  onClose: () => void;
  onSaved: (playlist: PlayerPlaylist) => void;
}

export const PlaylistModal: React.FC<PlaylistModalProps> = ({
  mode,
  playlist,
  onClose,
  onSaved,
}) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [m3uText, setM3uText] = useState('');
  const [fileName, setFileName] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (mode === 'edit' && playlist) {
      setName(playlist.name);
      setDescription(playlist.description || '');
    } else {
      setName('');
      setDescription('');
      setM3uText('');
      setFileName('');
    }
    setError(null);
  }, [mode, playlist]);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setFileName(file.name);
      if (!name) {
        // Default name to file name without extension
        setName(file.name.replace(/\.[^/.]+$/, ''));
      }
      const reader = new FileReader();
      reader.onload = (ev) => {
        setM3uText((ev.target?.result as string) || '');
      };
      reader.readAsText(file);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Vui lòng nhập tên Playlist.');
      return;
    }

    if (mode === 'import' && !m3uText.trim()) {
      setError('Vui lòng chọn file M3U hoặc dán nội dung M3U.');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      let result: PlayerPlaylist;
      if (mode === 'edit' && playlist) {
        result = await api.updatePlayerPlaylist(playlist.id, name.trim(), description.trim());
      } else if (mode === 'import') {
        result = await api.importPlayerPlaylistM3U(name.trim(), m3uText);
      } else {
        result = await api.createPlayerPlaylist(name.trim(), description.trim());
      }
      onSaved(result);
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Có lỗi xảy ra.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="w-full max-w-md bg-zinc-900 border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-white/5 border border-white/10 text-zinc-300">
              {mode === 'import' ? <Upload className="w-4 h-4" /> : <ListMusic className="w-4 h-4" />}
            </div>
            <div>
              <h3 className="text-sm font-semibold text-zinc-100">
                {mode === 'create'
                  ? 'Tạo danh sách phát mới'
                  : mode === 'edit'
                  ? 'Chỉnh sửa playlist'
                  : 'Import danh sách phát M3U'}
              </h3>
              <p className="text-[11px] text-zinc-400">
                {mode === 'import'
                  ? 'Nhập file .m3u / .m3u8 từ máy tính hoặc ứng dụng khác'
                  : 'Quản lý bài hát theo chủ đề hoặc cảm xúc'}
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 text-zinc-400 hover:text-zinc-100 hover:bg-white/10 rounded-lg transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
              {error}
            </div>
          )}

          <div className="space-y-1">
            <label className="text-xs font-medium text-zinc-300">Tên Playlist *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              autoFocus
              className="w-full px-3 py-1.5 text-xs rounded-lg bg-zinc-950 border border-white/10 text-zinc-100 focus:outline-none focus:border-zinc-400"
              placeholder="Ví dụ: Chill Vibe, Nhạc chạy bộ..."
            />
          </div>

          {mode !== 'import' && (
            <div className="space-y-1">
              <label className="text-xs font-medium text-zinc-300">Mô tả (tùy chọn)</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
                className="w-full px-3 py-1.5 text-xs rounded-lg bg-zinc-950 border border-white/10 text-zinc-100 focus:outline-none focus:border-zinc-400 resize-none"
                placeholder="Mô tả về danh sách bài hát..."
              />
            </div>
          )}

          {mode === 'import' && (
            <div className="space-y-3 pt-1">
              <label className="block">
                <span className="text-xs font-medium text-zinc-300">Chọn file .m3u hoặc .m3u8</span>
                <div className="mt-1 flex items-center justify-center px-4 py-4 border-2 border-dashed border-white/10 hover:border-white/20 rounded-xl cursor-pointer bg-zinc-950/50">
                  <div className="text-center space-y-1">
                    <Upload className="w-6 h-6 mx-auto text-zinc-500" />
                    <p className="text-xs text-zinc-300">
                      {fileName ? fileName : 'Bấm để chọn file M3U từ máy tính'}
                    </p>
                    <p className="text-[10px] text-zinc-500">Định dạng file .m3u, .m3u8 (UTF-8)</p>
                  </div>
                  <input
                    type="file"
                    accept=".m3u,.m3u8,text/plain"
                    onChange={handleFileUpload}
                    className="hidden"
                  />
                </div>
              </label>

              <div className="space-y-1">
                <label className="text-xs font-medium text-zinc-400">
                  Hoặc dán nội dung M3U vào đây:
                </label>
                <textarea
                  value={m3uText}
                  onChange={(e) => setM3uText(e.target.value)}
                  rows={4}
                  className="w-full px-3 py-1.5 text-[11px] font-mono rounded-lg bg-zinc-950 border border-white/10 text-zinc-300 focus:outline-none focus:border-zinc-400 resize-none"
                  placeholder="#EXTM3U&#10;/path/to/song.mp3&#10;..."
                />
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="pt-3 border-t border-white/10 flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-1.5 text-xs font-medium rounded-lg text-zinc-300 hover:text-white hover:bg-white/10 transition-colors"
            >
              Hủy
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-1.5 text-xs font-medium rounded-lg bg-zinc-100 text-zinc-900 hover:bg-white disabled:opacity-50 transition-colors flex items-center gap-1.5 shadow-sm"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Đang xử lý...</span>
                </>
              ) : (
                <>
                  <Save className="w-3.5 h-3.5" />
                  <span>
                    {mode === 'create' ? 'Tạo Playlist' : mode === 'edit' ? 'Lưu thay đổi' : 'Import'}
                  </span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
