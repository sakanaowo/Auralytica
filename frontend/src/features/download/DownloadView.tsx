import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../api/client';
import { DownloadBatch } from '../../api/types';

interface DownloadViewProps {
  batchLocked: boolean;
  onRefreshWorkflow: () => void;
}

const BATCH_STATUS_LABELS: Record<string, string> = {
  queued: 'Đang chờ',
  running: 'Đang tải',
  paused: 'Đã dừng',
  completed: 'Hoàn tất',
  partial: 'Có lỗi',
  failed: 'Thất bại',
  skipped: 'Đã có file',
  cancelled: 'Đã hủy',
};

export const DownloadView: React.FC<DownloadViewProps> = ({ batchLocked, onRefreshWorkflow }) => {
  const queryClient = useQueryClient();
  const [outputDir, setOutputDir] = useState<string>(() => {
    try {
      return localStorage.getItem('auralytica-output') || '~/Music/Auralytica';
    } catch {
      return '~/Music/Auralytica';
    }
  });

  const [selectedBatchId, setSelectedBatchId] = useState<number | null>(null);
  const [batchPage, setBatchPage] = useState(1);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Save outputDir to local storage
  useEffect(() => {
    try {
      localStorage.setItem('auralytica-output', outputDir);
    } catch {}
  }, [outputDir]);

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

  // Fetch selected batch detail
  const batchDetailQuery = useQuery({
    queryKey: ['downloads', 'batch', selectedBatchId, batchPage],
    queryFn: () => api.getDownloadBatch(selectedBatchId!, batchPage, 20),
    enabled: selectedBatchId !== null,
    refetchInterval: batchLocked ? 1500 : false,
  });

  const currentBatch: DownloadBatch | undefined = batchDetailQuery.data;

  // Start download mutation
  const startMutation = useMutation({
    mutationFn: () => {
      const token = previewQuery.data?.token;
      if (!token) throw new Error('Chưa có preview token hợp lệ.');
      return api.startDownload(outputDir.trim(), token);
    },
    onSuccess: (data) => {
      setSelectedBatchId(data.batch_id);
      setBatchPage(1);
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

  const preview = previewQuery.data;
  const canStart = (preview?.needed ?? 0) > 0 && !batchLocked && !startMutation.isPending;

  const doneCount =
    (currentBatch?.counts.completed || 0) + (currentBatch?.counts.skipped || 0);

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold tracking-tight text-zinc-100">04 · Download — Tải thư viện nhạc</h1>
        <p className="text-xs text-zinc-400 mt-1">
          Tải toàn bộ các bản thu được giữ sau bước Deduplicate. File audio giữ nguyên codec nguồn; bỏ qua các file đã có hợp lệ.
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

        {errorMsg && (
          <div className="p-3 rounded-lg bg-red-950/40 border border-red-800/40 text-red-300 text-xs">
            {errorMsg}
          </div>
        )}
      </div>

      {/* Batches History & Real-time Monitor */}
      {batches.length > 0 && (
        <div className="glass-panel rounded-2xl border border-white/10 p-6 space-y-4 shadow-xl">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-sm font-semibold tracking-wide text-zinc-200 uppercase">
              Lượt tải gần đây
            </h3>

            <select
              value={selectedBatchId ?? ''}
              onChange={(e) => {
                setSelectedBatchId(Number(e.target.value));
                setBatchPage(1);
              }}
              className="px-3 py-1 text-xs rounded-lg glass-input text-zinc-200"
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
                  <div className="font-semibold text-zinc-200">
                    Lượt #{currentBatch.batch_id} · {BATCH_STATUS_LABELS[currentBatch.status] || currentBatch.status}
                    {currentBatch.stop_requested && currentBatch.status === 'running' && (
                      <span className="text-amber-400 ml-2">(Đang yêu cầu dừng...)</span>
                    )}
                  </div>
                  <div className="text-[11px] text-zinc-500 font-mono mt-0.5">
                    {doneCount} / {currentBatch.total} hoàn thành · {currentBatch.counts.failed || 0} lỗi · Thư mục: {currentBatch.output_dir}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {['queued', 'running'].includes(currentBatch.status) && (
                    <button
                      type="button"
                      disabled={stopMutation.isPending}
                      onClick={() => stopMutation.mutate(currentBatch.batch_id)}
                      className="px-3 py-1.5 text-xs font-medium rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-white/10"
                    >
                      Dừng
                    </button>
                  )}

                  {['paused', 'partial', 'failed', 'cancelled'].includes(currentBatch.status) && (
                    <button
                      type="button"
                      disabled={resumeMutation.isPending || batchLocked}
                      onClick={() => resumeMutation.mutate(currentBatch.batch_id)}
                      className="px-3 py-1.5 text-xs font-medium rounded-lg bg-zinc-100 text-zinc-900 hover:bg-white border border-white"
                    >
                      Tiếp tục lượt này
                    </button>
                  )}
                </div>
              </div>

              {/* Progress Bar */}
              <div className="w-full h-2 bg-zinc-950 rounded-full overflow-hidden border border-white/5">
                <div
                  className="h-full bg-zinc-200 transition-all duration-300"
                  style={{
                    width: `${Math.min(100, (doneCount / Math.max(1, currentBatch.total)) * 100)}%`,
                  }}
                />
              </div>

              {/* Items List */}
              <div className="max-h-64 overflow-y-auto rounded-xl border border-white/5 bg-zinc-950/40">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-white/10 bg-zinc-900/60 text-zinc-400 font-mono text-[11px]">
                      <th className="p-2.5">Video</th>
                      <th className="p-2.5">Trạng thái</th>
                      <th className="p-2.5">Lỗi nếu có</th>
                    </tr>
                  </thead>
                  <tbody>
                    {currentBatch.items.map((item) => (
                      <tr key={item.video_id} className="border-b border-white/5 hover:bg-white/[0.02]">
                        <td className="p-2.5 max-w-[280px] truncate text-zinc-200">
                          <a
                            href={`https://www.youtube.com/watch?v=${encodeURIComponent(item.video_id)}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:underline"
                          >
                            {item.title || item.video_id}
                          </a>
                        </td>
                        <td className="p-2.5 font-mono text-[11px] text-zinc-400">
                          {BATCH_STATUS_LABELS[item.status] || item.status}
                          {item.status === 'running' && (
                            <span className="ml-1 text-zinc-500">
                              ({(item.downloaded_bytes / (1024 * 1024)).toFixed(1)} MB)
                            </span>
                          )}
                        </td>
                        <td className="p-2.5 text-zinc-500 text-[11px] max-w-[200px] truncate">
                          {item.error_message || '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Items Pager */}
              {Math.ceil(currentBatch.total / 20) > 1 && (
                <div className="flex items-center justify-between text-xs text-zinc-400 pt-1">
                  <span>
                    Trang {batchPage} / {Math.ceil(currentBatch.total / 20)}
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      disabled={batchPage <= 1}
                      onClick={() => setBatchPage((p) => p - 1)}
                      className="px-2.5 py-1 rounded bg-zinc-900 border border-white/5 disabled:opacity-40"
                    >
                      ←
                    </button>
                    <button
                      type="button"
                      disabled={batchPage >= Math.ceil(currentBatch.total / 20)}
                      onClick={() => setBatchPage((p) => p + 1)}
                      className="px-2.5 py-1 rounded bg-zinc-900 border border-white/5 disabled:opacity-40"
                    >
                      →
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
