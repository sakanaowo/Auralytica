import React, { useState, useEffect } from 'react';
import { PlayerTrack } from '../../api/types';
import { api } from '../../api/client';
import { useAudioPlayer } from '../../context/AudioPlayerContext';
import { X, Image as ImageIcon, Music, Save, Loader2, Check } from 'lucide-react';

interface MetadataEditModalProps {
  track: PlayerTrack | null;
  onClose: () => void;
  onSaved: (updatedTrack: PlayerTrack) => void;
}

export const MetadataEditModal: React.FC<MetadataEditModalProps> = ({
  track,
  onClose,
  onSaved,
}) => {
  const { updateTrackInState } = useAudioPlayer();

  const [title, setTitle] = useState('');
  const [artist, setArtist] = useState('');
  const [album, setAlbum] = useState('');
  const [genre, setGenre] = useState('');
  const [year, setYear] = useState('');
  const [renameFile, setRenameFile] = useState(false);
  const [coverFile, setCoverFile] = useState<File | null>(null);
  const [coverPreview, setCoverPreview] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (track) {
      setTitle(track.title || '');
      setArtist(track.artist || '');
      setAlbum(track.album || '');
      setGenre(track.genre || '');
      setYear(track.year || '');
      setRenameFile(false);
      setCoverFile(null);
      setCoverPreview(track.has_cover_art ? api.getPlayerArtUrl(track.path, track.mtime_ns) : null);
      setError(null);
      setSuccess(false);
    }
  }, [track]);

  if (!track) return null;

  const handleCoverSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setCoverFile(file);
      const url = URL.createObjectURL(file);
      setCoverPreview(url);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError('Tiêu đề bài hát không được để trống.');
      return;
    }

    setIsSaving(true);
    setError(null);

    try {
      const updated = await api.updateTrackMetadata({
        path: track.path,
        title: title.trim(),
        artist: artist.trim(),
        album: album.trim() || undefined,
        genre: genre.trim() || undefined,
        year: year.trim() || undefined,
        rename_file: renameFile,
        cover_file: coverFile,
      });

      updateTrackInState(updated, track.path);
      onSaved(updated);
      setSuccess(true);
      setTimeout(() => {
        onClose();
      }, 700);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Có lỗi khi lưu metadata vào file.');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="w-full max-w-lg bg-zinc-900 border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-white/10 flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-zinc-100">Chỉnh sửa thông tin bài hát</h3>
            <p className="text-xs text-zinc-400 mt-0.5">
              Ghi thẻ vật lý trực tiếp vào file âm thanh (Mutagen Tag Writer)
            </p>
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
        <form onSubmit={handleSave} className="p-5 space-y-4 overflow-y-auto max-h-[75vh]">
          {error && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
              {error}
            </div>
          )}

          {/* Cover Art & File info */}
          <div className="flex gap-4 items-start">
            <div className="relative group w-28 h-28 shrink-0 rounded-xl overflow-hidden bg-zinc-950 border border-white/10 flex items-center justify-center">
              {coverPreview ? (
                <img
                  src={coverPreview}
                  alt="Cover Preview"
                  className="w-full h-full object-cover"
                />
              ) : (
                <Music className="w-8 h-8 text-zinc-600" />
              )}
              <label className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 flex flex-col items-center justify-center cursor-pointer transition-opacity text-white text-[11px] gap-1">
                <ImageIcon className="w-4 h-4" />
                <span>Đổi ảnh</span>
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={handleCoverSelect}
                  className="hidden"
                />
              </label>
            </div>

            <div className="flex-1 min-w-0 space-y-1 text-xs">
              <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-500">
                Đường dẫn file
              </span>
              <p
                className="font-mono text-zinc-300 break-all text-[11px] bg-zinc-950/60 p-2 rounded-lg border border-white/5"
                title={track.path}
              >
                {track.path}
              </p>
              <p className="text-[11px] text-zinc-500">
                Kích thước: {(track.file_size / (1024 * 1024)).toFixed(2)} MB
              </p>
            </div>
          </div>

          {/* Fields */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
            <div className="space-y-1 md:col-span-2">
              <label className="text-xs font-medium text-zinc-300">Tiêu đề (Title) *</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
                className="w-full px-3 py-1.5 text-xs rounded-lg bg-zinc-950 border border-white/10 text-zinc-100 focus:outline-none focus:border-zinc-400"
                placeholder="Ví dụ: Nơi Này Có Anh"
              />
            </div>

            <div className="space-y-1 md:col-span-2">
              <label className="text-xs font-medium text-zinc-300">Nghệ sĩ (Artist)</label>
              <input
                type="text"
                value={artist}
                onChange={(e) => setArtist(e.target.value)}
                className="w-full px-3 py-1.5 text-xs rounded-lg bg-zinc-950 border border-white/10 text-zinc-100 focus:outline-none focus:border-zinc-400"
                placeholder="Ví dụ: Sơn Tùng M-TP"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-medium text-zinc-300">Album</label>
              <input
                type="text"
                value={album}
                onChange={(e) => setAlbum(e.target.value)}
                className="w-full px-3 py-1.5 text-xs rounded-lg bg-zinc-950 border border-white/10 text-zinc-100 focus:outline-none focus:border-zinc-400"
                placeholder="Tên Album"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-medium text-zinc-300">Thể loại (Genre)</label>
              <input
                type="text"
                value={genre}
                onChange={(e) => setGenre(e.target.value)}
                className="w-full px-3 py-1.5 text-xs rounded-lg bg-zinc-950 border border-white/10 text-zinc-100 focus:outline-none focus:border-zinc-400"
                placeholder="Pop, Ballad, EDM..."
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-medium text-zinc-300">Năm (Year)</label>
              <input
                type="text"
                value={year}
                onChange={(e) => setYear(e.target.value)}
                className="w-full px-3 py-1.5 text-xs rounded-lg bg-zinc-950 border border-white/10 text-zinc-100 focus:outline-none focus:border-zinc-400"
                placeholder="2024"
              />
            </div>
          </div>

          {/* Rename File Option */}
          <div className="pt-2">
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={renameFile}
                onChange={(e) => setRenameFile(e.target.checked)}
                className="rounded border-zinc-700 bg-zinc-950 text-emerald-500 focus:ring-0"
              />
              <span className="text-xs text-zinc-300">
                Đổi tên file theo định dạng chuẩn:{' '}
                <span className="font-mono text-zinc-400">Nghệ sĩ - Tiêu đề.ext</span>
              </span>
            </label>
          </div>

          {/* Actions */}
          <div className="pt-4 border-t border-white/10 flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-1.5 text-xs font-medium rounded-lg text-zinc-300 hover:text-white hover:bg-white/10 transition-colors"
            >
              Hủy
            </button>
            <button
              type="submit"
              disabled={isSaving || success}
              className="px-4 py-1.5 text-xs font-medium rounded-lg bg-emerald-500 text-zinc-950 hover:bg-emerald-400 disabled:opacity-50 transition-colors flex items-center gap-1.5 shadow-sm"
            >
              {isSaving ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Đang ghi thẻ...</span>
                </>
              ) : success ? (
                <>
                  <Check className="w-3.5 h-3.5" />
                  <span>Đã lưu!</span>
                </>
              ) : (
                <>
                  <Save className="w-3.5 h-3.5" />
                  <span>Lưu thông tin</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
