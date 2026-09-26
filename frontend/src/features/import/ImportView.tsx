import React, { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  UploadCloud,
  CheckCircle2,
  Trash2,
  ArrowRight,
  Clock,
  Music2,
  Layers,
  AlertTriangle,
  Plus,
  RefreshCw,
  FolderArchive,
  Database,
} from 'lucide-react';
import { api } from '../../api/client';
import { ImportSession } from '../../api/types';

interface ImportViewProps {
  onImportSuccess: () => void;
  batchLocked: boolean;
  onNavigateExplore?: () => void;
  onRefreshWorkflow?: () => void;
}

interface FileCandidate {
  file: File;
  path: string;
}

export const ImportView: React.FC<ImportViewProps> = ({
  onImportSuccess,
  batchLocked,
  onNavigateExplore,
  onRefreshWorkflow,
}) => {
  const queryClient = useQueryClient();

  // Sessions query
  const {
    data: sessionsData,
    isLoading: sessionsLoading,
    refetch: refetchSessions,
  } = useQuery({
    queryKey: ['importSessions'],
    queryFn: () => api.getImports(),
  });

  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // New import toggle
  const [showNewImport, setShowNewImport] = useState(false);

  // Candidates for import dialog
  const [candidates, setCandidates] = useState<FileCandidate[]>([]);
  const [showSourceDialog, setShowSourceDialog] = useState(false);
  const [selectedHistoryIndex, setSelectedHistoryIndex] = useState<number>(0);
  const [selectedLibraryIndex, setSelectedLibraryIndex] = useState<number | null>(null);

  // Delete modal state
  const [sessionToDelete, setSessionToDelete] = useState<ImportSession | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Mutations
  const activateMutation = useMutation({
    mutationFn: (importId: number) => api.activateImport(importId),
    onSuccess: (_, importId) => {
      queryClient.invalidateQueries({ queryKey: ['importSessions'] });
      queryClient.invalidateQueries({ queryKey: ['workflow'] });
      queryClient.invalidateQueries({ queryKey: ['videos'] });
      queryClient.invalidateQueries({ queryKey: ['exploreSummary'] });
      onRefreshWorkflow?.();
      setSuccessMessage(`Đã chuyển thành công sang phiên #${importId}`);
      setTimeout(() => setSuccessMessage(null), 4000);
    },
    onError: (err: any) => {
      setError(err.message || 'Không thể kích hoạt phiên.');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (importId: number) => api.deleteImport(importId),
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ['importSessions'] });
      queryClient.invalidateQueries({ queryKey: ['workflow'] });
      onRefreshWorkflow?.();
      setSessionToDelete(null);
      setSuccessMessage(`Đã xóa thành công phiên #${deletedId}`);
      setTimeout(() => setSuccessMessage(null), 4000);
    },
    onError: (err: any) => {
      setError(err.message || 'Không thể xóa phiên.');
      setSessionToDelete(null);
    },
  });

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
      await queryClient.invalidateQueries({ queryKey: ['importSessions'] });
      await queryClient.invalidateQueries({ queryKey: ['workflow'] });
      onRefreshWorkflow?.();
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

  const sessions = sessionsData?.items || sessionsData?.sessions || [];
  const activeSession = sessions.find((s) => s.is_active);
  const otherSessions = sessions.filter((s) => !s.is_active);
  const isLockActive = batchLocked || !!sessionsData?.batch_locked;

  const formatDate = (isoString?: string) => {
    if (!isoString) return '';
    try {
      const d = new Date(isoString);
      return d.toLocaleString('vi-VN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-10 px-4 space-y-8">
      {/* Header section */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-zinc-100 flex items-center gap-2">
            <Database className="w-5 h-5 text-emerald-400" />
            01 · Nhập & Quản lý phiên Takeout
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Quản lý các phiên lịch sử YouTube Takeout đã nạp, chuyển đổi linh hoạt hoặc nạp thêm phiên mới.
          </p>
        </div>

        {sessions.length > 0 && (
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => refetchSessions()}
              className="p-2 text-xs rounded-lg glass-input text-zinc-300 hover:text-white transition-all"
              title="Làm mới danh sách phiên"
            >
              <RefreshCw className={`w-4 h-4 ${sessionsLoading ? 'animate-spin' : ''}`} />
            </button>
            <button
              type="button"
              onClick={() => setShowNewImport((prev) => !prev)}
              disabled={isLockActive}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-all shadow-sm ${
                showNewImport
                  ? 'bg-zinc-800 text-zinc-200 hover:bg-zinc-700'
                  : 'bg-zinc-100 text-zinc-900 hover:bg-white'
              } ${isLockActive ? 'opacity-40 cursor-not-allowed' : ''}`}
            >
              <Plus className="w-4 h-4" />
              {showNewImport ? 'Thu gọn khung nạp' : 'Nạp phiên mới'}
            </button>
          </div>
        )}
      </div>

      {/* Lock alert banner */}
      {isLockActive && (
        <div className="flex items-center gap-3 p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs">
          <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400" />
          <span>
            Đang có đợt tải video chạy ngầm. Để đảm bảo an toàn dữ liệu, tính năng chuyển đổi phiên, xóa phiên và nạp mới tạm thời bị khóa cho đến khi tiến trình hoàn tất.
          </span>
        </div>
      )}

      {/* Status alerts */}
      {error && (
        <div className="flex items-center justify-between p-3.5 rounded-xl bg-red-950/40 border border-red-800/40 text-red-300 text-xs">
          <span>{error}</span>
          <button
            type="button"
            onClick={() => setError(null)}
            className="text-red-400 hover:text-red-200 text-sm ml-2"
          >
            ✕
          </button>
        </div>
      )}

      {successMessage && (
        <div className="flex items-center gap-2 p-3.5 rounded-xl bg-emerald-950/40 border border-emerald-800/40 text-emerald-300 text-xs">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
          <span>{successMessage}</span>
        </div>
      )}

      {/* ACTIVE SESSION CARD */}
      {activeSession && (
        <div className="relative overflow-hidden rounded-2xl border border-emerald-500/30 bg-emerald-950/15 p-6 space-y-5 shadow-lg shadow-emerald-950/20">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                Đang hoạt động
              </span>
              <span className="text-xs font-mono text-zinc-400">Phiên #{activeSession.id}</span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-zinc-400">
              <Clock className="w-3.5 h-3.5" />
              <span>Nạp lúc {formatDate(activeSession.created_at || activeSession.imported_at)}</span>
            </div>
          </div>

          <div className="text-xs text-zinc-300">
            <span className="text-zinc-500">Nguồn: </span>
            <span className="font-mono bg-zinc-900/60 px-2 py-0.5 rounded border border-white/5 text-zinc-300">
              {activeSession.source_name || activeSession.source_path || 'Thư mục Takeout'}
            </span>
          </div>

          {/* Stats summary pills */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="rounded-xl bg-zinc-900/40 border border-white/5 p-3">
              <div className="text-xs text-zinc-400 flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-zinc-400" />
                Tổng video
              </div>
              <div className="text-lg font-bold text-zinc-100 mt-1">
                {(
                  activeSession.counts.total ??
                  activeSession.counts.music + activeSession.counts.rest
                ).toLocaleString()}
              </div>
            </div>

            <div className="rounded-xl bg-zinc-900/40 border border-white/5 p-3">
              <div className="text-xs text-emerald-400/90 flex items-center gap-1.5">
                <Music2 className="w-3.5 h-3.5 text-emerald-400" />
                Video Nhạc
              </div>
              <div className="text-lg font-bold text-emerald-400 mt-1">
                {activeSession.counts.music.toLocaleString()}
              </div>
            </div>

            <div className="rounded-xl bg-zinc-900/40 border border-white/5 p-3">
              <div className="text-xs text-zinc-400">Còn lại (Other)</div>
              <div className="text-lg font-bold text-zinc-300 mt-1">
                {activeSession.counts.rest.toLocaleString()}
              </div>
            </div>

            <div className="rounded-xl bg-zinc-900/40 border border-white/5 p-3">
              <div className="text-xs text-zinc-400">Lượt xem parsed</div>
              <div className="text-lg font-bold text-zinc-300 mt-1">
                {(
                  activeSession.statistics.parsed_events ??
                  activeSession.statistics.raw_events ??
                  0
                ).toLocaleString()}
              </div>
            </div>
          </div>

          {/* Call to action for active session */}
          <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-3 border-t border-emerald-500/20">
            <span className="text-xs text-zinc-400">
              Tiến trình phân loại và deduplication của phiên này luôn được lưu tự động.
            </span>
            {onNavigateExplore && (
              <button
                type="button"
                onClick={onNavigateExplore}
                className="w-full sm:w-auto flex items-center justify-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 shadow-md shadow-emerald-950/20 transition-all cursor-pointer"
              >
                Tiếp tục xem dữ liệu
                <ArrowRight className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      )}

      {/* SAVED SESSIONS LIST */}
      {otherSessions.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
              <FolderArchive className="w-4 h-4 text-zinc-400" />
              Các phiên lưu trữ khác ({otherSessions.length})
            </h2>
            <span className="text-xs text-zinc-500">
              Chuyển đổi tức thì mà không làm mất dữ liệu phân loại dở
            </span>
          </div>

          <div className="space-y-2">
            {otherSessions.map((session) => (
              <div
                key={session.id}
                className="glass-panel rounded-xl border border-white/5 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:border-white/10 transition-all bg-zinc-900/40"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-xs text-zinc-200">Phiên #{session.id}</span>
                    <span className="text-zinc-600">·</span>
                    <span className="text-xs text-zinc-400 flex items-center gap-1">
                      <Clock className="w-3 h-3 text-zinc-500" />
                      {formatDate(session.created_at || session.imported_at)}
                    </span>
                  </div>
                  <div className="text-xs font-mono text-zinc-400 truncate max-w-lg">
                    {session.source_name || session.source_path || 'Takeout Folder'}
                  </div>
                  <div className="flex items-center gap-3 text-xs text-zinc-400 pt-1">
                    <span>
                      <strong className="text-zinc-200">
                        {(session.counts.total ?? session.counts.music + session.counts.rest).toLocaleString()}
                      </strong>{' '}
                      video
                    </span>
                    <span className="text-zinc-600">·</span>
                    <span className="text-emerald-400/90">
                      <strong>{session.counts.music.toLocaleString()}</strong> nhạc
                    </span>
                    <span className="text-zinc-600">·</span>
                    <span>
                      <strong>{session.counts.rest.toLocaleString()}</strong> khác
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <button
                    type="button"
                    disabled={isLockActive || activateMutation.isPending}
                    onClick={() => activateMutation.mutate(session.id)}
                    title={
                      isLockActive
                        ? 'Không thể đổi phiên khi đang có đợt tải chạy ngầm'
                        : 'Kích hoạt phiên này để tiếp tục phân loại hoặc tải'
                    }
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border transition-all ${
                      isLockActive
                        ? 'border-white/5 text-zinc-600 bg-zinc-900/50 cursor-not-allowed'
                        : 'border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/10 hover:border-emerald-500 bg-emerald-950/20'
                    }`}
                  >
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    Kích hoạt phiên này
                  </button>

                  <button
                    type="button"
                    disabled={isLockActive || deleteMutation.isPending}
                    onClick={() => setSessionToDelete(session)}
                    title={
                      isLockActive
                        ? 'Không thể xóa khi đang có đợt tải chạy ngầm'
                        : 'Xóa vĩnh viễn phiên này khỏi CSDL'
                    }
                    className={`p-2 rounded-lg border border-white/5 transition-all text-zinc-400 hover:text-red-400 hover:border-red-500/30 hover:bg-red-950/20 ${
                      isLockActive ? 'opacity-30 cursor-not-allowed' : ''
                    }`}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* NEW IMPORT DROPZONE */}
      {(sessions.length === 0 || showNewImport) && (
        <div className="space-y-4 pt-2">
          {sessions.length > 0 && (
            <div className="flex items-center justify-between border-t border-white/5 pt-4">
              <h2 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
                <Plus className="w-4 h-4 text-emerald-400" />
                Nạp phiên Takeout mới
              </h2>
              <span className="text-xs text-zinc-500">
                Phiên mới sẽ được lưu riêng biệt, không làm ghi đè phiên cũ
              </span>
            </div>
          )}

          <div
            onDragOver={(e) => {
              e.preventDefault();
              if (!isLockActive && !loading) setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            className={`glass-panel rounded-2xl border-2 border-dashed p-10 text-center transition-all ${
              isDragging
                ? 'border-emerald-400 bg-emerald-950/20'
                : 'border-white/10 hover:border-white/20 bg-zinc-900/40'
            } ${isLockActive ? 'opacity-40 pointer-events-none' : ''}`}
          >
            <div className="space-y-4">
              <div className="flex justify-center">
                <div className="w-12 h-12 rounded-2xl bg-zinc-800/80 border border-white/5 flex items-center justify-center text-zinc-300 shadow-inner">
                  <UploadCloud className="w-6 h-6 text-zinc-300" />
                </div>
              </div>

              <div>
                <div className="text-zinc-200 font-semibold text-sm">
                  Kéo thả folder Google Takeout vào đây
                </div>
                <p className="text-xs text-zinc-400 max-w-md mx-auto leading-relaxed mt-1">
                  Folder Takeout đã giải nén chứa <span className="font-mono text-zinc-300">watch-history.json</span> (và tùy chọn <span className="font-mono text-zinc-300">music library songs.csv</span>).
                </p>
              </div>

              <div className="pt-2">
                <button
                  type="button"
                  disabled={loading || isLockActive}
                  onClick={() => fileInputRef.current?.click()}
                  className="px-5 py-2 text-xs font-semibold rounded-lg bg-zinc-100 text-zinc-900 hover:bg-white border border-white transition-all shadow-md cursor-pointer disabled:opacity-50"
                >
                  {loading ? 'Đang xử lý...' : 'Chọn folder Takeout'}
                </button>
                <input
                  id="folder-input"
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

      {/* Delete Confirmation Modal */}
      {sessionToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md">
          <div className="w-full max-w-md glass-panel rounded-2xl border border-red-500/20 p-6 space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-red-500/10 border border-red-500/30 flex items-center justify-center text-red-400">
                <Trash2 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-zinc-100">
                  Xác nhận xóa phiên #{sessionToDelete.id}?
                </h3>
                <p className="text-xs text-zinc-400 mt-0.5">
                  Nạp lúc {formatDate(sessionToDelete.created_at || sessionToDelete.imported_at)}
                </p>
              </div>
            </div>

            <p className="text-xs text-zinc-300 leading-relaxed">
              Toàn bộ dữ liệu lịch sử xem (
              {(
                sessionToDelete.counts.total ??
                sessionToDelete.counts.music + sessionToDelete.counts.rest
              ).toLocaleString()}{' '}
              video) và tiến trình phân loại liên quan đến phiên này sẽ bị xóa khỏi cơ sở dữ liệu.
              <br />
              <span className="text-zinc-400 text-[11px] block mt-2">
                * Các file nhạc đã tải trên ổ đĩa của bạn sẽ được giữ nguyên, không bị ảnh hưởng.
              </span>
            </p>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                disabled={deleteMutation.isPending}
                onClick={() => setSessionToDelete(null)}
                className="px-3.5 py-1.5 text-xs rounded-lg bg-zinc-800 text-zinc-300 hover:text-white"
              >
                Hủy
              </button>
              <button
                type="button"
                disabled={deleteMutation.isPending}
                onClick={() => deleteMutation.mutate(sessionToDelete.id)}
                className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-red-600 hover:bg-red-500 text-white transition-all shadow-md"
              >
                {deleteMutation.isPending ? 'Đang xóa...' : 'Xác nhận xóa'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
