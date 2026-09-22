import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../api/client';
import { DownloadBatch, DownloadBatchItem, AudioFormat } from '../../api/types';

interface DownloadViewProps {
  batchLocked: boolean;
  onRefreshWorkflow: () => void;
  onNavigateConvert?: () => void;
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
  onNavigateConvert,
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

  const [format, setFormat] = useState<AudioFormat>(() => {
    try {
      return (localStorage.getItem('auralytica-format') as AudioFormat) || 'm4a_alac';
    } catch {
      return 'm4a_alac';
    }
  });

  const [cleanNames, setCleanNames] = useState<boolean>(() => {
    try {
      const v = localStorage.getItem('auralytica-clean-names');
      return v !== null ? v === '1' : true;
    } catch {
      return true;
    }
  });

  const [embedMetadata, setEmbedMetadata] = useState<boolean>(() => {
    try {
      const v = localStorage.getItem('auralytica-embed-metadata');
      return v !== null ? v === '1' : true;
    } catch {
      return true;
    }
  });

  // Save settings to local storage
  useEffect(() => {
    try {
      localStorage.setItem('auralytica-output', outputDir);
      localStorage.setItem('auralytica-format', format);
      localStorage.setItem('auralytica-clean-names', cleanNames ? '1' : '0');
      localStorage.setItem('auralytica-embed-metadata', embedMetadata ? '1' : '0');
    } catch {}
  }, [outputDir, format, cleanNames, embedMetadata]);

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
            <label className="block text-xs font-medium text-zinc-300 mb-1.5">
              Thư mục lưu trên máy
            </label>
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
            {startMutation.isPending ? 'Đang khởi tạo...' : 'Tải toàn bộ bản giữ'}
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
        <div className="pt-3 border-t border-white/5 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-300">
              Định dạng âm thanh xuất xưởng
            </span>
            <span className="text-[11px] text-zinc-500 font-mono">
              In-stream FFmpeg Pipeline
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
            {[
              {
                id: 'm4a_alac',
                name: 'M4A ALAC Lossless',
                badge: 'Apple Music',
                desc: 'Lossless bit-perfect từ nguồn Opus; tương thích tối đa Apple Music.',
              },
              {
                id: 'm4a_aac',
                name: 'M4A AAC (256k)',
                badge: 'Tiết kiệm bộ nhớ',
                desc: 'AAC chất lượng cao, nạp trực tiếp vào Apple Music / iTunes.',
              },
              {
                id: 'mp3',
                name: 'MP3 (320k)',
                badge: 'Phổ thông',
                desc: 'Định dạng tương thích mọi dòng máy nghe nhạc và hệ thống âm thanh.',
              },
              {
                id: 'raw',
                name: 'Nguyên bản (Raw)',
                badge: 'Gốc YouTube',
                desc: 'Giữ nguyên codec gốc từ YouTube không qua transcode.',
              },
            ].map((fmt) => (
              <button
                key={fmt.id}
                type="button"
                disabled={batchLocked}
                onClick={() => setFormat(fmt.id as AudioFormat)}
                className={`text-left p-3 rounded-xl border transition-all ${
                  format === fmt.id
                    ? 'bg-zinc-100 text-zinc-900 border-white shadow-lg shadow-white/5'
                    : 'bg-zinc-950/40 text-zinc-300 border-white/5 hover:border-white/20 hover:bg-zinc-900/40'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold text-xs">{fmt.name}</span>
                  <span
                    className={`text-[9px] px-1.5 py-0.5 rounded font-medium ${
                      format === fmt.id
                        ? 'bg-zinc-800 text-zinc-100'
                        : 'bg-white/5 text-zinc-400'
                    }`}
                  >
                    {fmt.badge}
                  </span>
                </div>
                <p
                  className={`text-[11px] leading-tight ${
                    format === fmt.id ? 'text-zinc-600' : 'text-zinc-500'
                  }`}
                >
                  {fmt.desc}
                </p>
              </button>
            ))}
          </div>

          {/* Option toggles */}
          <div className="flex flex-wrap items-center gap-6 pt-1 text-xs text-zinc-300">
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={cleanNames}
                onChange={(e) => setCleanNames(e.target.checked)}
                disabled={batchLocked}
                className="rounded border-zinc-700 bg-zinc-900 text-zinc-100 focus:ring-0 focus:ring-offset-0"
              />
              <span>Làm sạch tên file (Bỏ mã [video_id], lọc tags YouTube thừa)</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={embedMetadata}
                onChange={(e) => setEmbedMetadata(e.target.checked)}
                disabled={batchLocked}
                className="rounded border-zinc-700 bg-zinc-900 text-zinc-100 focus:ring-0 focus:ring-offset-0"
              />
              <span>Nhúng ảnh bìa bài hát (Cover Art) & siêu dữ liệu Tags</span>
            </label>
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

            <select
              value={selectedBatchId ?? ''}
              onChange={(e) => {
                setSelectedBatchId(Number(e.target.value));
                setBatchPage(1);
                setStatusFilter('all');
              }}
              className="px-3 py-1.5 text-xs rounded-lg glass-input text-zinc-200 border border-white/10"
            >
              {batches.map((b) => (
                <option key={b.batch_id} value={b.batch_id}>
                  #{b.batch_id} · {BATCH_STATUS_LABELS[b.status] || b.status} · {b.total} video
                </option>
              ))}
            </select>
          </div>

          {currentBatch && (
            <div className="space-y-4 pt-2">
              {/* Batch Meta & Actions */}
              <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-xl bg-zinc-950/40 border border-white/5 text-xs">
                <div>
                  <div className="font-semibold text-zinc-200 flex flex-wrap items-center gap-2">
                    <span>Lượt #{currentBatch.batch_id}</span>
                    <span className="text-zinc-500">·</span>
                    <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-zinc-800 text-zinc-300 border border-white/5">
                      {BATCH_STATUS_LABELS[currentBatch.status] || currentBatch.status}
                    </span>
                    {currentBatch.format && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-white/5 text-zinc-300 border border-white/10 uppercase">
                        {currentBatch.format}
                      </span>
                    )}
                    {currentBatch.clean_names && (
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-sans bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                        Tên sạch
                      </span>
                    )}
                    {currentBatch.stop_requested && currentBatch.status === 'running' && (
                      <span className="text-amber-400 text-[11px]">(Đang yêu cầu dừng...)</span>
                    )}
                  </div>
                  <div className="text-[11px] text-zinc-400 font-mono mt-1">
                    {completedCount} / {currentBatch.total} hoàn thành
                    {failedCount > 0 && (
                      <span className="text-rose-400 font-semibold ml-1.5">
                        · {failedCount} thất bại
                      </span>
                    )}
                    {runningCount > 0 && (
                      <span className="text-sky-400 ml-1.5">
                        · {runningCount} đang tải
                      </span>
                    )}
                    <span className="text-zinc-500 ml-1.5">· Thư mục: {currentBatch.output_dir}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
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
                      Tiếp tục lượt này
                    </button>
                  )}

                  {failedCount > 0 && !['running'].includes(currentBatch.status) && (
                    <button
                      type="button"
                      disabled={isRetrying || batchLocked}
                      onClick={() => retryFailedMutation.mutate(currentBatch.batch_id)}
                      className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-zinc-100 text-zinc-900 hover:bg-white border border-white transition-all shadow"
                    >
                      {retryFailedMutation.isPending ? 'Đang khởi chạy...' : `Thử lại ${failedCount} bài lỗi`}
                    </button>
                  )}
                </div>
              </div>

              {/* Progress Bar */}
              <div className="w-full h-1.5 bg-zinc-950 rounded-full overflow-hidden border border-white/5">
                <div
                  className="h-full bg-zinc-200 transition-all duration-300"
                  style={{
                    width: `${Math.min(100, (completedCount / Math.max(1, currentBatch.total)) * 100)}%`,
                  }}
                />
              </div>

              {/* Step 05 Apple Music Callout Banner */}
              {onNavigateConvert && completedCount > 0 && (
                <div className="p-3.5 rounded-xl border border-white/10 bg-zinc-950/40 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                  <div>
                    <span className="font-semibold text-zinc-200">
                      Đã có {completedCount} file audio trong thư mục
                    </span>
                    <p className="text-[11px] text-zinc-400 mt-0.5">
                      Chuyển sang bước Apple Music để loại bỏ mã [video_id] thừa ở tên file và chuyển đổi sang M4A (ALAC / AAC).
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={onNavigateConvert}
                    className="px-3.5 py-1.5 text-xs font-medium rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-white/10 shrink-0 transition-colors"
                  >
                    Xử lý tên & Chuyển đổi Apple Music →
                  </button>
                </div>
              )}

              {/* Diagnostic Error Banner (Only shown when there are failed items) */}
              {failedCount > 0 && (
                <div className="p-4 rounded-xl border border-rose-500/20 bg-rose-950/20 space-y-3">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div>
                      <div className="text-xs font-semibold text-rose-300 flex items-center gap-2">
                        <span>Chẩn đoán lượt tải: Có {failedCount} bài tải không thành công</span>
                      </div>
                      <p className="text-[11px] text-zinc-400 mt-0.5 leading-relaxed">
                        Hầu hết lỗi phát sinh do YouTube áp dụng giới hạn tạm thời khi tải danh sách dài. Động cơ tải đã tích hợp multi-client fallback để vượt qua cơ chế này khi thử lại.
                      </p>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {statusFilter !== 'failed' && (
                        <button
                          type="button"
                          onClick={() => {
                            setStatusFilter('failed');
                            setBatchPage(1);
                          }}
                          className="px-3 py-1.5 text-xs rounded-lg border border-white/10 bg-zinc-900/60 text-zinc-300 hover:bg-zinc-800 transition-colors"
                        >
                          Lọc riêng {failedCount} bài lỗi
                        </button>
                      )}

                      {!['running'].includes(currentBatch.status) && (
                        <button
                          type="button"
                          disabled={isRetrying || batchLocked}
                          onClick={() => retryFailedMutation.mutate(currentBatch.batch_id)}
                          className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-zinc-100 text-zinc-900 hover:bg-white border border-white transition-all shadow"
                        >
                          {retryFailedMutation.isPending ? 'Đang gửi...' : 'Thử lại tất cả bài lỗi'}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Status Filter Tabs */}
              <div className="flex items-center gap-1 border-b border-white/10 pb-2 overflow-x-auto text-xs font-mono">
                <button
                  type="button"
                  onClick={() => { setStatusFilter('all'); setBatchPage(1); }}
                  className={`px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap ${
                    statusFilter === 'all'
                      ? 'bg-zinc-800 text-zinc-100 font-semibold border border-white/10'
                      : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.03]'
                  }`}
                >
                  Tất cả ({totalCount})
                </button>

                <button
                  type="button"
                  onClick={() => { setStatusFilter('failed'); setBatchPage(1); }}
                  className={`px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap flex items-center gap-1.5 ${
                    statusFilter === 'failed'
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
                  className={`px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap ${
                    statusFilter === 'running'
                      ? 'bg-zinc-800 text-zinc-100 font-semibold border border-white/10'
                      : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.03]'
                  }`}
                >
                  Đang tải ({runningCount})
                </button>

                <button
                  type="button"
                  onClick={() => { setStatusFilter('queued'); setBatchPage(1); }}
                  className={`px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap ${
                    statusFilter === 'queued'
                      ? 'bg-zinc-800 text-zinc-100 font-semibold border border-white/10'
                      : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.03]'
                  }`}
                >
                  Đang chờ ({queuedCount})
                </button>

                <button
                  type="button"
                  onClick={() => { setStatusFilter('completed'); setBatchPage(1); }}
                  className={`px-3 py-1.5 rounded-lg transition-colors whitespace-nowrap ${
                    statusFilter === 'completed'
                      ? 'bg-zinc-800 text-zinc-100 font-semibold border border-white/10'
                      : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.03]'
                  }`}
                >
                  Hoàn tất ({completedCount})
                </button>
              </div>

              {/* Items List Table */}
              <div className="overflow-hidden rounded-xl border border-white/5 bg-zinc-950/40">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-white/10 bg-zinc-900/60 text-zinc-400 font-mono text-[11px]">
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
                              <div className="flex items-center gap-2 mt-0.5 text-[11px] font-mono text-zinc-500">
                                <span>{item.video_id}</span>
                                <span>·</span>
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
                            <td className="p-3 font-mono text-[11px] whitespace-nowrap">
                              {item.status === 'failed' ? (
                                <span className={`inline-block px-2 py-0.5 rounded text-[11px] border font-sans ${errMeta?.color || 'text-rose-400 bg-rose-500/10 border-rose-500/20'}`}>
                                  {errMeta?.label || 'Thất bại'}
                                </span>
                              ) : item.status === 'completed' || item.status === 'skipped' ? (
                                <span className="inline-block px-2 py-0.5 rounded text-[11px] text-zinc-300 bg-zinc-800/80 border border-white/5">
                                  {item.status === 'skipped' ? 'Đã có file' : 'Hoàn tất'}
                                </span>
                              ) : item.status === 'running' ? (
                                <span className="inline-block px-2 py-0.5 rounded text-[11px] text-sky-300 bg-sky-500/10 border border-sky-500/20 animate-pulse">
                                  Đang tải {(item.downloaded_bytes / (1024 * 1024)).toFixed(1)} MB
                                </span>
                              ) : (
                                <span className="text-zinc-500">
                                  {BATCH_STATUS_LABELS[item.status] || item.status}
                                </span>
                              )}
                            </td>

                            {/* Error Details / Message */}
                            <td className="p-3 text-[11px]">
                              {item.status === 'failed' ? (
                                <div className="space-y-0.5">
                                  <div className="text-zinc-300 truncate max-w-[260px]">
                                    {item.error_message || 'yt-dlp không thể tải video này.'}
                                  </div>
                                  <button
                                    type="button"
                                    onClick={() => setInspectItem(item)}
                                    className="text-zinc-400 hover:text-zinc-200 underline text-[11px] cursor-pointer"
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
                                  className="px-2.5 py-1 text-[11px] font-medium rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-white/10 disabled:opacity-40 transition-colors"
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

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between text-xs text-zinc-400 pt-2 font-mono">
                  <span>
                    Trang {batchPage} / {totalPages} · {filteredTotal} bài
                  </span>
                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      disabled={batchPage <= 1}
                      onClick={() => setBatchPage((p) => Math.max(1, p - 1))}
                      className="px-2.5 py-1 rounded-md bg-zinc-900 border border-white/10 disabled:opacity-30 hover:bg-zinc-800 transition-colors"
                    >
                      ← Trang trước
                    </button>
                    <button
                      type="button"
                      disabled={batchPage >= totalPages}
                      onClick={() => setBatchPage((p) => Math.min(totalPages, p + 1))}
                      className="px-2.5 py-1 rounded-md bg-zinc-900 border border-white/10 disabled:opacity-30 hover:bg-zinc-800 transition-colors"
                    >
                      Trang sau →
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Inspect Item Modal */}
      {inspectItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
          <div className="glass-panel rounded-2xl border border-white/15 p-6 max-w-lg w-full space-y-4 shadow-2xl bg-zinc-900/90 text-xs">
            <div className="flex items-start justify-between gap-3">
              <div>
                <span className="text-[11px] font-mono text-zinc-400 uppercase tracking-wider">
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
              <div className="flex justify-between text-[11px]">
                <span className="text-zinc-500">Video ID:</span>
                <span className="text-zinc-300">{inspectItem.video_id}</span>
              </div>
              <div className="flex justify-between text-[11px]">
                <span className="text-zinc-500">Mã lỗi hệ thống:</span>
                <span className="text-zinc-300 font-semibold">{inspectItem.error_code || 'unknown'}</span>
              </div>
              <div className="border-t border-white/5 pt-2 text-[11px]">
                <span className="text-zinc-500 block mb-1">Thông điệp từ yt-dlp:</span>
                <p className="text-zinc-300 leading-relaxed font-sans bg-zinc-900/60 p-2 rounded border border-white/5">
                  {inspectItem.error_message || 'Không có thông tin chi tiết.'}
                </p>
              </div>
            </div>

            {inspectItem.error_code && ERROR_CODE_LABELS[inspectItem.error_code] && (
              <div className="space-y-2 p-3.5 rounded-xl bg-zinc-800/30 border border-white/5">
                <div className="font-semibold text-zinc-200 flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded text-[11px] border font-sans ${ERROR_CODE_LABELS[inspectItem.error_code].color}`}>
                    {ERROR_CODE_LABELS[inspectItem.error_code].label}
                  </span>
                </div>
                <p className="text-zinc-400 text-[11px] leading-relaxed">
                  {ERROR_CODE_LABELS[inspectItem.error_code].desc}
                </p>
                <div className="pt-1.5 border-t border-white/5 text-[11px] text-zinc-300">
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
                    className="px-3.5 py-1.5 rounded-lg bg-zinc-100 text-zinc-900 font-semibold hover:bg-white border border-white transition-all shadow"
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
