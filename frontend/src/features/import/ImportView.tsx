import React, { useState, useRef } from 'react';
import { api } from '../../api/client';

interface ImportViewProps {
  onImportSuccess: () => void;
  batchLocked: boolean;
}

interface FileCandidate {
  file: File;
  path: string;
}

export const ImportView: React.FC<ImportViewProps> = ({ onImportSuccess, batchLocked }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<FileCandidate[]>([]);
  const [showSourceDialog, setShowSourceDialog] = useState(false);
  const [selectedHistoryIndex, setSelectedHistoryIndex] = useState<number>(0);
  const [selectedLibraryIndex, setSelectedLibraryIndex] = useState<number | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleImport = async (history: FileCandidate, library?: FileCandidate) => {
    setLoading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append('files', history.file, 'watch-history.json');
      if (library) {
        formData.append('files', library.file, 'music library songs.csv');
      }

      if (history.file.size + (library?.file.size || 0) > 63 * 1024 * 1024) {
        throw new Error('Dữ liệu vượt giới hạn upload 63 MiB của bản local hiện tại.');
      }

      await api.importUpload(formData);
      onImportSuccess();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const processFiles = (files: FileCandidate[]) => {
    if (batchLocked) return;
    const filtered = files.filter((item) =>
      ['watch-history.json', 'music library songs.csv'].includes(item.file.name)
    );
    const histories = filtered.filter((item) => item.file.name === 'watch-history.json');

    if (histories.length === 0) {
      setError('Không tìm thấy watch-history.json. Hãy chọn folder Takeout đã giải nén có lịch sử JSON; HTML chưa hỗ trợ.');
      return;
    }

    setCandidates(filtered);

    // If only 1 history file, auto import
    if (histories.length === 1) {
      const history = histories[0];
      const libraries = filtered.filter((item) => item.file.name === 'music library songs.csv');
      handleImport(history, libraries.length === 1 ? libraries[0] : undefined);
      return;
    }

    // Multiple histories found -> show dialog
    setSelectedHistoryIndex(filtered.indexOf(histories[0]));
    setShowSourceDialog(true);
  };

  const readEntry = async (entry: any): Promise<FileCandidate[]> => {
    if (entry.isFile) {
      if (!['watch-history.json', 'music library songs.csv'].includes(entry.name)) return [];
      const file: File = await new Promise((resolve, reject) => entry.file(resolve, reject));
      return [{ file, path: entry.fullPath.replace(/^\//, '') }];
    }
    const reader = entry.createReader();
    const files: FileCandidate[] = [];
    while (true) {
      const entries: any[] = await new Promise((resolve, reject) => reader.readEntries(resolve, reject));
      if (!entries.length) break;
      for (const child of entries) {
        files.push(...(await readEntry(child)));
      }
    }
    return files;
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (batchLocked || loading) return;

    try {
      const items = Array.from(e.dataTransfer.items)
        .map((item) => item.webkitGetAsEntry?.())
        .filter(Boolean);

      const files: FileCandidate[] = [];
      if (items.length > 0) {
        for (const item of items) {
          files.push(...(await readEntry(item)));
        }
      } else {
        const rawFiles = Array.from(e.dataTransfer.files);
        files.push(...rawFiles.map((file) => ({ file, path: file.name })));
      }
      processFiles(files);
    } catch (err: any) {
      setError(`Không đọc được folder: ${err.message}. Thử nút Chọn folder.`);
    }
  };

  return (
    <div className="max-w-3xl mx-auto py-12 px-4 space-y-6">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-zinc-100">01 · Nhập dữ liệu Google Takeout</h1>
        <p className="text-xs text-zinc-400 mt-1">
          Chọn folder Google Takeout đã giải nén có file lịch sử xem dạng JSON để bắt đầu.
        </p>
      </div>

      {/* Drop Zone */}
      <div
        onDragOver={(e) => {
          e.preventDefault();
          if (!batchLocked && !loading) setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={`glass-panel rounded-2xl border-2 border-dashed p-12 text-center transition-all ${
          isDragging
            ? 'border-zinc-400 bg-zinc-800/40'
            : 'border-white/10 hover:border-white/20 bg-zinc-900/40'
        } ${batchLocked ? 'opacity-40 pointer-events-none' : ''}`}
      >
        <div className="space-y-4">
          <div className="text-zinc-300 font-medium text-sm">
            Kéo thả folder Google Takeout vào đây
          </div>
          <p className="text-xs text-zinc-500 max-w-md mx-auto leading-relaxed">
            Folder đã giải nén · Lịch sử JSON (<span className="font-mono text-zinc-400">watch-history.json</span>) · Toàn bộ xử lý diễn ra trực tiếp trên máy của bạn.
          </p>

          <div className="pt-2">
            <button
              type="button"
              disabled={loading || batchLocked}
              onClick={() => fileInputRef.current?.click()}
              className="px-5 py-2 text-xs font-semibold rounded-lg bg-zinc-100 text-zinc-900 hover:bg-white border border-white transition-all shadow-md"
            >
              {loading ? 'Đang xử lý...' : 'Chọn folder Takeout'}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              /* @ts-ignore */
              webkitdirectory=""
              multiple
              className="hidden"
              onChange={(e) => {
                const files = Array.from(e.target.files || []).map((file) => ({
                  file,
                  path: file.webkitRelativePath || file.name,
                }));
                processFiles(files);
              }}
            />
          </div>
        </div>
      </div>

      {error && (
        <div className="p-3.5 rounded-xl bg-red-950/40 border border-red-800/40 text-red-300 text-xs">
          {error}
        </div>
      )}

      {/* Source Selection Dialog */}
      {showSourceDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md">
          <div className="w-full max-w-md glass-panel rounded-2xl border border-white/10 p-6 space-y-4">
            <h3 className="text-sm font-semibold text-zinc-100">Chọn nguồn lịch sử xem</h3>
            <p className="text-xs text-zinc-400">
              Folder có nhiều nguồn lịch sử. Vui lòng chọn lịch sử xem và music library tương ứng.
            </p>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-zinc-400 mb-1">Lịch sử xem (watch-history.json)</label>
                <select
                  value={selectedHistoryIndex}
                  onChange={(e) => setSelectedHistoryIndex(Number(e.target.value))}
                  className="w-full px-3 py-1.5 rounded-lg glass-input text-zinc-200"
                >
                  {candidates
                    .filter((c) => c.file.name === 'watch-history.json')
                    .map((c) => (
                      <option key={c.path} value={candidates.indexOf(c)}>
                        {c.path}
                      </option>
                    ))}
                </select>
              </div>

              <div>
                <label className="block text-zinc-400 mb-1">Music Library (tùy chọn)</label>
                <select
                  value={selectedLibraryIndex ?? ''}
                  onChange={(e) =>
                    setSelectedLibraryIndex(e.target.value === '' ? null : Number(e.target.value))
                  }
                  className="w-full px-3 py-1.5 rounded-lg glass-input text-zinc-200"
                >
                  <option value="">Không dùng music library</option>
                  {candidates
                    .filter((c) => c.file.name === 'music library songs.csv')
                    .map((c) => (
                      <option key={c.path} value={candidates.indexOf(c)}>
                        {c.path}
                      </option>
                    ))}
                </select>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowSourceDialog(false)}
                className="px-3 py-1.5 text-xs rounded-lg bg-zinc-800 text-zinc-300 hover:text-white"
              >
                Hủy
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowSourceDialog(false);
                  const history = candidates[selectedHistoryIndex];
                  const library =
                    selectedLibraryIndex !== null ? candidates[selectedLibraryIndex] : undefined;
                  handleImport(history, library);
                }}
                className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-zinc-100 text-zinc-900 hover:bg-white"
              >
                Tiếp tục
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
