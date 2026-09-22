import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../api/client';
import { DownloadBatch, DownloadBatchItem, AudioFormat } from '../../api/types';

interface DownloadViewProps {
  batchLocked: boolean;
  onRefreshWorkflow: () => void;
}

const BATCH_STATUS_LABELS: Record<string, string> = {
  queued: 'Đang chờ',
  running: 'Đang tải',
  paused: 'Đã dừng',
  completed: 'Hoàn tất',
  partial: 'Có bài lỗi',
  failed: 'Thất bại',
  skipped: 'Đã có file',
  cancelled: 'Đã hủy',
};

const ERROR_CODE_LABELS: Record<string, { label: string; color: string; desc: string; advice: string }> = {
  unavailable: {
    label: 'Đã xóa / Riêng tư',
    color: 'text-rose-400 bg-rose-500/10 border-rose-500/20',
    desc: 'Video đã bị gỡ bỏ, đặt ở chế độ riêng tư hoặc kênh YouTube đã bị chấm dứt.',
    advice: 'Không thể tải được bài này do nguồn trên YouTube không còn khả dụng.',
  },
  bot_blocked: {
    label: 'Chặn tạm thời (Bot)',
    color: 'text-amber-300 bg-amber-500/10 border-amber-500/20',
    desc: 'YouTube áp dụng cơ chế xác thực bot đối với IP của bạn khi tải liên tục số lượng lớn.',
    advice: 'Hệ thống đã bật fallback đa client (Android/iOS). Bạn có thể bấm [Thử lại] ngay hoặc đợi 1-2 phút.',
  },
  rate_limited: {
    label: 'Giới hạn tần suất (429)',
    color: 'text-amber-300 bg-amber-500/10 border-amber-500/20',
    desc: 'YouTube tạm giới hạn tần suất yêu cầu (HTTP 429 Too Many Requests).',
    advice: 'Hãy chờ 1-3 phút để YouTube reset hạn mức rồi bấm [Thử lại các bài lỗi].',
  },
  age_restricted: {
    label: 'Giới hạn độ tuổi',
    color: 'text-orange-300 bg-orange-500/10 border-orange-500/20',
    desc: 'Video này YouTube yêu cầu phải đăng nhập tài khoản để xác nhận độ tuổi.',
    advice: 'Hãy xuất file cookies.txt từ trình duyệt và đặt vào thư mục lưu trữ hoặc ~/.local/share/auralytica/cookies.txt.',
  },
  geo_restricted: {
    label: 'Chặn vùng quốc gia',
    color: 'text-purple-300 bg-purple-500/10 border-purple-500/20',
    desc: 'Video bị giới hạn vùng địa lý không cho phép phát tại khu vực hiện tại.',
    advice: 'Video này không khả dụng với IP mạng tại vị trí hiện tại.',
  },
  format_unavailable: {
    label: 'Không có định dạng phù hợp',
    color: 'text-zinc-300 bg-zinc-500/10 border-zinc-500/20',
    desc: 'Không tìm thấy luồng âm thanh thích hợp từ YouTube.',
    advice: 'Hệ thống đã hỗ trợ chế độ trích xuất stream không suy hao (stream copy), hãy thử lại bài này.',
  },
  network_error: {
    label: 'Lỗi mạng / Timeout',
    color: 'text-sky-300 bg-sky-500/10 border-sky-500/20',
    desc: 'Kết nối mạng bị gián đoạn hoặc timeout trong lúc tải từ máy chủ YouTube.',
    advice: 'Kiểm tra lại đường truyền mạng và bấm [Thử lại].',
  },
  filesystem: {
    label: 'Lỗi ổ đĩa / Phân quyền',
    color: 'text-rose-400 bg-rose-500/10 border-rose-500/20',
    desc: 'Không thể ghi file vào thư mục lưu trữ do đầy dung lượng hoặc thiếu quyền ghi.',
    advice: 'Kiểm tra dung lượng ổ đĩa và quyền truy cập thư mục lưu trữ.',
  },
  download_error: {
    label: 'Lỗi tải về',
    color: 'text-zinc-300 bg-zinc-500/10 border-zinc-500/20',
    desc: 'Lỗi không xác định trong quá trình tải.',
    advice: 'Bấm [Thử lại] để kích hoạt engine tải với client dự phòng.',
  },
};

type StatusFilter = 'all' | 'failed' | 'running' | 'queued' | 'completed';

export const DownloadView: React.FC<DownloadViewProps> = ({
  batchLocked,
  onRefreshWorkflow,
}) => {
  const queryClient = useQueryClient();
  const [outputDir, setOutputDir] = useState<string>(() => {
    try {
      return localStorage.getItem('auralytica-output') || '~/Music/Auralytica';
    } catch {
      return '~/Music/Auralytica';
    }
  });

  const [selectedBatchId, setSelectedBatchId] = useState<number | null>(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [batchPage, setBatchPage] = useState(1);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [inspectItem, setInspectItem] = useState<DownloadBatchItem | null>(null);
  const [isListExpanded, setIsListExpanded] = useState<boolean>(false);

  const [format, setFormat] = useState<AudioFormat>(() => {
    try {
      return (localStorage.getItem('auralytica-format') as AudioFormat) || 'm4a_alac';
    } catch {
      return 'm4a_alac';
    }
  });

  // Clean names & embed metadata are now always enabled by default
  const cleanNames = true;
  const embedMetadata = true;

  // Save settings to local storage
  useEffect(() => {
    try {
      localStorage.setItem('auralytica-output', outputDir);
      localStorage.setItem('auralytica-format', format);
    } catch { }
  }, [outputDir, format]);

  // Fetch preview
  const previewQuery = useQuery({
    queryKey: ['downloads', 'preview', outputDir],
    queryFn: () => api.getDownloadPreview(outputDir),
    enabled: outputDir.trim().length > 0,
  });

  // Fetch batches list (poll if batchLocked)
  const batchesQuery = useQuery({
    queryKey: ['downloads', 'batches'],
    queryFn: () => api.getDownloads(),
    refetchInterval: batchLocked ? 1500 : 5000,
  });

  const batches = batchesQuery.data?.batches || [];

  // Default selectedBatchId to first batch if not set
  useEffect(() => {
    if (batches.length > 0 && selectedBatchId === null) {
      setSelectedBatchId(batches[0].batch_id);
    }
  }, [batches, selectedBatchId]);

  // Fetch selected batch detail with status filter
  const batchDetailQuery = useQuery({
    queryKey: ['downloads', 'batch', selectedBatchId, batchPage, statusFilter],
    queryFn: () => api.getDownloadBatch(selectedBatchId!, batchPage, 20, statusFilter),
    enabled: selectedBatchId !== null,
    refetchInterval: batchLocked ? 1500 : false,
  });

  const currentBatch: DownloadBatch | undefined = batchDetailQuery.data;

  // Start download mutation
  const startMutation = useMutation({
    mutationFn: () => {
      const token = previewQuery.data?.token;
      if (!token) throw new Error('Chưa có preview token hợp lệ.');
      return api.startDownload(outputDir.trim(), token, format, cleanNames, embedMetadata);
    },
    onSuccess: (data) => {
      setSelectedBatchId(data.batch_id);
      setBatchPage(1);
      setStatusFilter('all');
      queryClient.invalidateQueries({ queryKey: ['downloads'] });
      onRefreshWorkflow();
    },
    onError: (err: any) => {
      setErrorMsg(err.message);
    },
  });

  // Stop download mutation
  const stopMutation = useMutation({
    mutationFn: (id: number) => api.stopDownload(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['downloads'] });
      onRefreshWorkflow();
    },
  });

  // Resume download mutation
  const resumeMutation = useMutation({
    mutationFn: (id: number) => api.resumeDownload(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['downloads'] });
      onRefreshWorkflow();
    },
  });

  // Retry all failed items
  const retryFailedMutation = useMutation({
    mutationFn: (id: number) => api.retryFailedDownloads(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['downloads'] });
      onRefreshWorkflow();
    },
    onError: (err: any) => {
      setErrorMsg(err.message);
    },
  });

  // Retry single item
  const retryItemMutation = useMutation({
    mutationFn: ({ batchId, videoId }: { batchId: number; videoId: string }) =>
      api.retryDownloadItem(batchId, videoId),
    onSuccess: () => {
      if (inspectItem) {
        setInspectItem(null);
      }
      queryClient.invalidateQueries({ queryKey: ['downloads'] });
      onRefreshWorkflow();
    },
    onError: (err: any) => {
      setErrorMsg(err.message);
    },
  });

  const preview = previewQuery.data;
  const canStart = (preview?.needed ?? 0) > 0 && !batchLocked && !startMutation.isPending;

  const counts = currentBatch?.counts || {};
  const completedCount = (counts.completed || 0) + (counts.skipped || 0);
  const failedCount = counts.failed || 0;
  const runningCount = counts.running || 0;
  const queuedCount = counts.queued || 0;
  const totalCount = currentBatch?.total || 0;

  // Filtered total for pagination
  const filteredTotal = currentBatch?.filtered_total ?? totalCount;
  const totalPages = Math.max(1, Math.ceil(filteredTotal / 20));

  // Diagnostic breakdown
  const isRetrying = retryFailedMutation.isPending || retryItemMutation.isPending;

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold tracking-tight text-zinc-100">04 · Download — Tải thư viện nhạc</h1>
        <p className="text-xs text-zinc-400 mt-1">
          Tải toàn bộ các bản thu được giữ lại. File audio giữ nguyên codec nguồn không chuyển mã; tự động phát hiện và bỏ qua file đã có.
        </p>
      </div>

      {/* Directory & Preview Card */}
      <div className="glass-panel rounded-2xl border border-white/10 p-6 space-y-4 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-end gap-3">
          <div className="flex-1">
            <div className="flex items-center justify-between mb-1.5">
              <label className="block text-xs font-medium text-zinc-300">
                Thư mục lưu trên máy
              </label>
              <button
                type="button"
                onClick={() => previewQuery.refetch()}
                disabled={previewQuery.isFetching}
                className="text-xs text-sky-400 hover:text-sky-300 flex items-center gap-1 transition-colors disabled:opacity-50"
                title="Quét lại file đã có trong thư mục"
              >
                <span>{previewQuery.isFetching ? 'Đang quét...' : '↻ Quét lại thư mục'}</span>
              </button>
            </div>
            <input
              type="text"
              value={outputDir}
              onChange={(e) => setOutputDir(e.target.value)}
              disabled={batchLocked}
              placeholder="~/Music/Auralytica"
              className="w-full px-3.5 py-2 text-xs rounded-lg glass-input text-zinc-200 font-mono disabled:opacity-50"
            />
          </div>

          <button
            type="button"
            disabled={!canStart}
            onClick={() => startMutation.mutate()}
            className="px-5 py-2 text-xs font-semibold rounded-lg bg-zinc-100 text-zinc-900 hover:bg-white border border-white disabled:opacity-40 disabled:pointer-events-none transition-all shadow-md shrink-0"
          >
            {startMutation.isPending
              ? 'Đang khởi tạo...'
              : preview && preview.needed > 0
                ? `Tải ${preview.needed} bài còn thiếu`
                : preview && preview.needed === 0
                  ? 'Đã có đủ file trên máy'
                  : 'Tải toàn bộ bản giữ'}
          </button>
        </div>

        {/* Status Preview summary */}
        <div className="p-3.5 rounded-xl bg-zinc-950/40 border border-white/5 text-xs text-zinc-400 font-mono flex flex-wrap gap-y-1 gap-x-3">
          {preview ? (
            <>
              <span>{preview.music} video nhạc</span>
              <span>·</span>
              <span>{preview.excluded} loại bởi Deduplicate</span>
              <span>·</span>
              <span className="text-zinc-200 font-semibold">{preview.kept} giữ lại</span>
              <span>·</span>
              <span>{preview.skipped} file đã có</span>
              <span>·</span>
              <span className="text-zinc-100 font-bold">{preview.needed} file cần tải</span>
            </>
          ) : (
            <span>Đang kiểm tra số lượng file...</span>
          )}
        </div>

        {/* Audio Pipeline Settings */}
        {/* Clean Audio Format Selection (2 Choices) */}
        <div className="pt-3 border-t border-white/5 space-y-2.5">
          <div className="text-xs font-semibold uppercase tracking-wider text-zinc-300">
            Định dạng âm thanh xuất xưởng
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {[
              {
                id: 'm4a_alac',
                name: 'Lossless ALAC (M4A)',
                badge: 'Chuẩn Apple Music',
                desc: 'Lossless bit-perfect từ Opus nguồn, tương thích gốc với Apple Music / iTunes.',
              },
              {
                id: 'mp3',
                name: 'MP3 (320 kbps)',
                badge: 'Phổ thông',
                desc: 'Định dạng tương thích mọi dòng máy nghe nhạc, hệ thống ô tô và thiết bị di động.',
              },
            ].map((fmt) => (
              <button
                key={fmt.id}
                type="button"
                disabled={batchLocked}
                onClick={() => setFormat(fmt.id as AudioFormat)}
                className={`text-left p-3.5 rounded-xl border transition-all ${format === fmt.id
                    ? 'bg-sky-500/15 text-white border-sky-400/40 shadow-[0_0_15px_rgba(56,189,248,0.12)] ring-1 ring-sky-400/20'
                    : 'bg-zinc-950/40 text-zinc-300 border-white/5 hover:border-white/20 hover:bg-zinc-900/40'
                  }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold text-xs text-zinc-100">{fmt.name}</span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded font-medium ${format === fmt.id
                        ? 'bg-sky-500/25 text-sky-200 border border-sky-400/30'
                        : 'bg-white/5 text-zinc-400 border border-white/5'
                      }`}
                  >
                    {fmt.badge}
                  </span>
                </div>
                <p
                  className={`text-xs leading-relaxed ${format === fmt.id ? 'text-zinc-300' : 'text-zinc-500'
                    }`}
                >
                  {fmt.desc}
                </p>
              </button>
            ))}
          </div>
        </div>

        {errorMsg && (
          <div className="p-3 rounded-lg bg-red-950/40 border border-red-800/40 text-red-300 text-xs flex justify-between items-center">
            <span>{errorMsg}</span>
            <button
              type="button"
              onClick={() => setErrorMsg(null)}
              className="text-red-400 hover:text-red-200 text-xs ml-2 underline"
            >
              Đóng
            </button>
          </div>
        )}
      </div>

      {/* Batches History & Real-time Monitor */}
      {batches.length > 0 && (
        <div className="glass-panel rounded-2xl border border-white/10 p-6 space-y-4 shadow-xl">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-sm font-semibold tracking-wide text-zinc-200 uppercase">
              Lượt tải
            </h3>

            {batches.length > 1 && (
              <select
                value={selectedBatchId ?? ''}
                onChange={(e) => {
                  setSelectedBatchId(Number(e.target.value));
                  setBatchPage(1);
                  setStatusFilter('all');
                }}
                className="px-3 py-1.5 text-xs rounded-lg glass-input text-zinc-200 border border-white/10 cursor-pointer"
              >
                {batches.map((b) => (
                  <option key={b.batch_id} value={b.batch_id}>
                    #{b.batch_id} · {BATCH_STATUS_LABELS[b.status] || b.status} · {b.total} video
                  </option>
                ))}
              </select>
            )}
          </div>

          {currentBatch && (() => {
            const runningItem = currentBatch.items.find((i) => i.status === 'running');
            const isCompleted = currentBatch.status === 'completed';
            const percent = Math.round((completedCount / Math.max(1, currentBatch.total)) * 100);

            return (
              <div className="space-y-4 pt-1">
                {/* Apple Music Live Player Card */}
                <div className="p-4 sm:p-5 rounded-2xl bg-zinc-950/60 border border-white/10 shadow-lg space-y-4 backdrop-blur-md">
                  {/* Top: Track visual & live status */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="flex items-center gap-3.5 min-w-0 flex-1">
                      {/* 60x60 Album Squircle / Vinyl visual */}
                      <div className="relative w-14 h-14 shrink-0 rounded-2xl bg-zinc-900 border border-white/10 shadow-md flex items-center justify-center overflow-hidden">
                        {runningItem ? (
                          <>
                            <img
                              src={`https://i.ytimg.com/vi/${runningItem.video_id}/mqdefault.jpg`}
                              alt=""
                              className="w-full h-full object-cover scale-110 opacity-75"
                            />
                            {/* Live Audio Equalizer Animation */}
                            <div className="absolute inset-0 bg-black/50 backdrop-blur-[1px] flex items-end justify-center gap-1 p-2">
                              <span className="w-1 bg-sky-400 rounded-full animate-[pulse_0.8s_ease-in-out_infinite] h-3" />
                              <span className="w-1 bg-sky-400 rounded-full animate-[pulse_1.2s_ease-in-out_infinite] h-5" />
                              <span className="w-1 bg-sky-400 rounded-full animate-[pulse_0.6s_ease-in-out_infinite] h-4" />
                              <span className="w-1 bg-sky-400 rounded-full animate-[pulse_1.0s_ease-in-out_infinite] h-2" />
                            </div>
                          </>
                        ) : isCompleted ? (
                          <div className="w-full h-full flex items-center justify-center bg-sky-500/10 text-sky-400">
                            <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                          </div>
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-zinc-500 bg-zinc-900">
                            <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                            </svg>
                          </div>
                        )}
                      </div>

                      {/* Track info & Live State */}
                      <div className="flex-1 min-w-0 pr-2">
                        {runningItem ? (
                          <>
                            <div className="text-xs font-mono text-sky-400 flex items-center gap-1.5 mb-0.5">
                              <span className="w-2 h-2 rounded-full bg-sky-400 animate-ping" />
                              <span>Đang tải audio...</span>
                            </div>
                            <div className="text-sm font-semibold text-zinc-100 truncate" title={runningItem.title || runningItem.video_id}>
                              {runningItem.title || runningItem.video_id}
                            </div>
                            <div className="text-xs text-zinc-400 font-mono mt-0.5">
                              Đã nhận {(runningItem.downloaded_bytes / (1024 * 1024)).toFixed(1)} MB · Định dạng {currentBatch.format?.toUpperCase()}
                            </div>
                          </>
                        ) : isCompleted ? (
                          <>
                            <div className="text-xs font-medium text-emerald-400 mb-0.5 flex items-center gap-1">
                              <span>✓</span>
                              <span>Toàn bộ đĩa nhạc đã hoàn tất!</span>
                            </div>
                            <div className="text-sm font-semibold text-zinc-100">
                              Đã nạp thành công {completedCount} bài hát vào thư viện
                            </div>
                            <div className="text-xs text-zinc-400 font-mono mt-0.5 truncate" title={currentBatch.output_dir}>
                              {currentBatch.output_dir}
                            </div>
                          </>
                        ) : (
                          <>
                            <div className="text-sm font-semibold text-zinc-200">
                              Lượt #{currentBatch.batch_id} · {BATCH_STATUS_LABELS[currentBatch.status] || currentBatch.status}
                            </div>
                            <div className="text-xs text-zinc-400 font-mono mt-0.5 truncate">
                              {completedCount} / {currentBatch.total} bài · {currentBatch.format?.toUpperCase()}
                            </div>
                          </>
                        )}
                      </div>
                    </div>

                    {/* Action buttons */}
                    <div className="flex flex-wrap items-center gap-2 shrink-0">

                      {['queued', 'running'].includes(currentBatch.status) && (
                        <button
                          type="button"
                          disabled={stopMutation.isPending}
                          onClick={() => stopMutation.mutate(currentBatch.batch_id)}
                          className="px-3 py-1.5 text-xs font-medium rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-white/10 transition-colors"
                        >
                          Tạm dừng
                        </button>
                      )}

                      {['paused', 'partial', 'failed', 'cancelled'].includes(currentBatch.status) && (
                        <button
                          type="button"
                          disabled={resumeMutation.isPending || batchLocked}
                          onClick={() => resumeMutation.mutate(currentBatch.batch_id)}
                          className="px-3 py-1.5 text-xs font-medium rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-white/10 transition-colors"
                        >
                          Tiếp tục
                        </button>
                      )}

                      {failedCount > 0 && !['running'].includes(currentBatch.status) && (
                        <button
                          type="button"
                          disabled={isRetrying || batchLocked}
                          onClick={() => retryFailedMutation.mutate(currentBatch.batch_id)}
                          className="px-3 py-1.5 text-xs font-medium rounded-lg bg-rose-500/20 text-rose-200 hover:bg-rose-500/30 border border-rose-500/30 transition-all shadow-sm"
                        >
                          {retryFailedMutation.isPending ? 'Đang gửi...' : `Thử lại ${failedCount} bài lỗi`}
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Master Progress Bar */}
                  <div className="space-y-2 pt-1">
                    <div className="w-full h-2 bg-zinc-950 rounded-full overflow-hidden border border-white/5">
                      <div
                        className="h-full bg-sky-400 transition-all duration-300 shadow-[0_0_8px_rgba(56,189,248,0.5)]"
                        style={{
                          width: `${Math.min(100, (completedCount / Math.max(1, currentBatch.total)) * 100)}%`,
                        }}
                      />
                    </div>

                    {/* Progress numbers & Collapsible trigger */}
                    <div className="flex flex-wrap items-center justify-between text-xs text-zinc-400 font-mono pt-0.5">
                      <div className="flex items-center gap-2">
                        <span className="text-zinc-200 font-medium">
                          {completedCount} / {currentBatch.total} bài ({percent}%)
                        </span>
                        {failedCount > 0 && (
                          <span className="text-rose-400 font-semibold">
                            · {failedCount} bài lỗi
                          </span>
                        )}
                        {runningCount > 0 && (
                          <span className="text-sky-400">
                            · {runningCount} đang tải
                          </span>
                        )}
                      </div>

                      <button
                        type="button"
                        onClick={() => setIsListExpanded(!isListExpanded)}
                        className="text-zinc-400 hover:text-zinc-100 flex items-center gap-1.5 transition-colors cursor-pointer py-0.5"
                      >
                        <span>{isListExpanded ? 'Thu gọn danh sách' : `Xem chi tiết (${totalCount} bài)`}</span>
                        <span className="text-[10px]">{isListExpanded ? '▲' : '▼'}</span>
                      </button>
                    </div>
                  </div>
                </div>

                {/* Collapsible Details Drawer */}
                {isListExpanded && (
                  <div className="space-y-3 pt-2">
                    {/* Status Filter Tabs */}
                    <div className="flex items-center gap-1 border-b border-white/10 pb-2 overflow-x-auto text-xs font-mono">
                      <button
                        type="button"
                        onClick={() => { setStatusFilter('all'); setBatchPage(1); }}
                        className={`px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap ${statusFilter === 'all'
                            ? 'bg-zinc-800 text-zinc-100 font-semibold border border-white/10'
                            : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.03]'
                          }`}
                      >
                        Tất cả ({totalCount})
                      </button>

                      <button
                        type="button"
                        onClick={() => { setStatusFilter('failed'); setBatchPage(1); }}
                        className={`px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap flex items-center gap-1.5 ${statusFilter === 'failed'
                            ? 'bg-rose-500/15 text-rose-300 font-semibold border border-rose-500/30'
                            : failedCount > 0
                              ? 'text-rose-400 hover:bg-rose-500/10'
                              : 'text-zinc-500 hover:text-zinc-300'
                          }`}
                      >
                        <span>Thất bại ({failedCount})</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => { setStatusFilter('running'); setBatchPage(1); }}
                        className={`px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap ${statusFilter === 'running'
                            ? 'bg-zinc-800 text-zinc-100 font-semibold border border-white/10'
                            : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.03]'
                          }`}
                      >
                        Đang tải ({runningCount})
                      </button>

                      <button
                        type="button"
                        onClick={() => { setStatusFilter('queued'); setBatchPage(1); }}
                        className={`px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap ${statusFilter === 'queued'
                            ? 'bg-zinc-800 text-zinc-100 font-semibold border border-white/10'
                            : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.03]'
                          }`}
                      >
                        Đang chờ ({queuedCount})
                      </button>

                      <button
                        type="button"
                        onClick={() => { setStatusFilter('completed'); setBatchPage(1); }}
                        className={`px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap ${statusFilter === 'completed'
                            ? 'bg-zinc-800 text-zinc-100 font-semibold border border-white/10'
                            : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.03]'
                          }`}
                      >
                        Hoàn tất ({completedCount})
                      </button>
                    </div>

                    {/* Items List Table */}
                    <div className="overflow-y-auto max-h-[380px] rounded-xl border border-white/10 bg-zinc-950/60 shadow-inner">
                      <table className="w-full text-left border-collapse text-xs">
                        <thead className="sticky top-0 z-10 bg-zinc-900/95 backdrop-blur-md">
                          <tr className="border-b border-white/10 text-zinc-400 font-mono text-xs">
                            <th className="p-3">Video</th>
                            <th className="p-3 w-36">Trạng thái</th>
                            <th className="p-3">Chẩn đoán / Chi tiết</th>
                            <th className="p-3 w-24 text-right">Thao tác</th>
                          </tr>
                        </thead>
                        <tbody>
                          {currentBatch.items.length === 0 ? (
                            <tr>
                              <td colSpan={4} className="p-8 text-center text-zinc-500 font-mono">
                                Không có bài nào trong danh mục này.
                              </td>
                            </tr>
                          ) : (
                            currentBatch.items.map((item) => {
                              const errMeta = item.error_code ? ERROR_CODE_LABELS[item.error_code] : null;

                              return (
                                <tr key={item.video_id} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                                  {/* Video Title & Link */}
                                  <td className="p-3 max-w-[280px]">
                                    <div className="truncate font-medium text-zinc-200">
                                      {item.title || item.video_id}
                                    </div>
                                    <div className="flex items-center gap-2 mt-0.5 text-xs font-mono text-zinc-500">
                                      {/* <span>{item.video_id}</span>
                                      <span>·</span> */}
                                      <a
                                        href={`https://www.youtube.com/watch?v=${encodeURIComponent(item.video_id)}`}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-zinc-400 hover:text-zinc-200 hover:underline"
                                      >
                                        Mở YouTube ↗
                                      </a>
                                    </div>
                                  </td>

                                  {/* Status */}
                                  <td className="p-3 font-mono text-xs whitespace-nowrap">
                                    {item.status === 'failed' ? (
                                      <span className={`inline-block px-2 py-0.5 rounded text-xs border font-sans ${errMeta?.color || 'text-rose-400 bg-rose-500/10 border-rose-500/20'}`}>
                                        {errMeta?.label || 'Thất bại'}
                                      </span>
                                    ) : item.status === 'completed' || item.status === 'skipped' ? (
                                      <span className="inline-block px-2 py-0.5 rounded text-xs text-zinc-300 bg-zinc-800/80 border border-white/5">
                                        {item.status === 'skipped' ? 'Đã có file' : 'Hoàn tất'}
                                      </span>
                                    ) : item.status === 'running' ? (
                                      <span className="inline-block px-2 py-0.5 rounded text-xs text-sky-300 bg-sky-500/10 border border-sky-500/20 animate-pulse">
                                        Đang tải {(item.downloaded_bytes / (1024 * 1024)).toFixed(1)} MB
                                      </span>
                                    ) : (
                                      <span className="text-zinc-500">
                                        {BATCH_STATUS_LABELS[item.status] || item.status}
                                      </span>
                                    )}
                                  </td>

                                  {/* Error Details / Message */}
                                  <td className="p-3 text-xs">
                                    {item.status === 'failed' ? (
                                      <div className="space-y-0.5">
                                        <div className="text-zinc-300 truncate max-w-[260px]">
                                          {item.error_message || 'yt-dlp không thể tải video này.'}
                                        </div>
                                        <button
                                          type="button"
                                          onClick={() => setInspectItem(item)}
                                          className="text-zinc-400 hover:text-zinc-200 underline text-xs cursor-pointer"
                                        >
                                          Xem chi tiết nguyên nhân
                                        </button>
                                      </div>
                                    ) : item.status === 'running' && item.total_bytes ? (
                                      <div className="w-28 h-1 bg-zinc-800 rounded-full overflow-hidden">
                                        <div
                                          className="h-full bg-sky-400"
                                          style={{
                                            width: `${Math.min(100, (item.downloaded_bytes / Math.max(1, item.total_bytes)) * 100)}%`,
                                          }}
                                        />
                                      </div>
                                    ) : (
                                      <span className="text-zinc-600 font-mono">—</span>
                                    )}
                                  </td>

                                  {/* Action: Retry single item */}
                                  <td className="p-3 text-right">
                                    {item.status === 'failed' && (
                                      <button
                                        type="button"
                                        disabled={isRetrying || ['running'].includes(currentBatch.status)}
                                        onClick={() => retryItemMutation.mutate({ batchId: currentBatch.batch_id, videoId: item.video_id })}
                                        className="px-2.5 py-1 text-xs font-medium rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-white/10 disabled:opacity-40 transition-colors"
                                      >
                                        Thử lại
                                      </button>
                                    )}
                                  </td>
                                </tr>
                              );
                            })
                          )}
                        </tbody>
                      </table>
                    </div>

                    {/* Pagination Footer */}
                    {totalPages > 1 && (
                      <div className="p-2.5 px-3.5 rounded-xl border border-white/5 bg-zinc-950/40 flex items-center justify-between text-xs text-zinc-400">
                        <span className="font-mono text-xs">
                          Trang {batchPage} / {totalPages} · {filteredTotal} bài
                        </span>
                        <div className="flex items-center gap-1">
                          <button
                            type="button"
                            disabled={batchPage <= 1}
                            onClick={() => setBatchPage(batchPage - 1)}
                            className="px-2.5 py-1 rounded-lg bg-zinc-900 border border-white/5 text-zinc-300 hover:text-white disabled:opacity-40 transition-colors"
                          >
                            ←
                          </button>
                          <button
                            type="button"
                            disabled={batchPage >= totalPages}
                            onClick={() => setBatchPage(batchPage + 1)}
                            className="px-2.5 py-1 rounded-lg bg-zinc-900 border border-white/5 text-zinc-300 hover:text-white disabled:opacity-40 transition-colors"
                          >
                            →
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })()}
        </div>
      )}

      {/* Inspect Item Modal */}
      {inspectItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
          <div className="glass-panel rounded-2xl border border-white/15 p-6 max-w-lg w-full space-y-4 shadow-2xl bg-zinc-900/90 text-xs">
            <div className="flex items-start justify-between gap-3">
              <div>
                <span className="text-xs font-mono text-zinc-400 uppercase tracking-wider">
                  Chẩn đoán lỗi video
                </span>
                <h3 className="text-sm font-semibold text-zinc-100 mt-1">
                  {inspectItem.title || inspectItem.video_id}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setInspectItem(null)}
                className="text-zinc-400 hover:text-zinc-200 text-sm px-1.5 py-0.5 rounded hover:bg-white/5"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 p-3.5 rounded-xl bg-zinc-950/60 border border-white/5 font-mono">
              <div className="flex justify-between text-xs">
                <span className="text-zinc-500">Video ID:</span>
                <span className="text-zinc-300">{inspectItem.video_id}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-zinc-500">Mã lỗi hệ thống:</span>
                <span className="text-zinc-300 font-semibold">{inspectItem.error_code || 'unknown'}</span>
              </div>
              <div className="border-t border-white/5 pt-2 text-xs">
                <span className="text-zinc-500 block mb-1">Thông điệp từ yt-dlp:</span>
                <p className="text-zinc-300 leading-relaxed font-sans bg-zinc-900/60 p-2 rounded border border-white/5">
                  {inspectItem.error_message || 'Không có thông tin chi tiết.'}
                </p>
              </div>
            </div>

            {inspectItem.error_code && ERROR_CODE_LABELS[inspectItem.error_code] && (
              <div className="space-y-2 p-3.5 rounded-xl bg-zinc-800/30 border border-white/5">
                <div className="font-semibold text-zinc-200 flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded text-xs border font-sans ${ERROR_CODE_LABELS[inspectItem.error_code].color}`}>
                    {ERROR_CODE_LABELS[inspectItem.error_code].label}
                  </span>
                </div>
                <p className="text-zinc-400 text-xs leading-relaxed">
                  {ERROR_CODE_LABELS[inspectItem.error_code].desc}
                </p>
                <div className="pt-1.5 border-t border-white/5 text-xs text-zinc-300">
                  <strong className="text-zinc-200">Gợi ý xử lý: </strong>
                  {ERROR_CODE_LABELS[inspectItem.error_code].advice}
                </div>
              </div>
            )}

            <div className="flex items-center justify-between pt-2">
              <a
                href={`https://www.youtube.com/watch?v=${encodeURIComponent(inspectItem.video_id)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="px-3 py-1.5 rounded-lg border border-white/10 text-zinc-300 hover:text-zinc-100 hover:bg-white/5 transition-colors"
              >
                Kiểm tra trên YouTube ↗
              </a>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setInspectItem(null)}
                  className="px-3 py-1.5 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-white/5 transition-colors"
                >
                  Đóng
                </button>
                {currentBatch && !['running'].includes(currentBatch.status) && (
                  <button
                    type="button"
                    disabled={isRetrying}
                    onClick={() => retryItemMutation.mutate({ batchId: currentBatch.batch_id, videoId: inspectItem.video_id })}
                    className="px-3.5 py-1.5 rounded-lg bg-sky-500 hover:bg-sky-400 text-white font-medium transition-all shadow-sm"
                  >
                    {retryItemMutation.isPending ? 'Đang gửi...' : 'Thử lại bài này'}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
