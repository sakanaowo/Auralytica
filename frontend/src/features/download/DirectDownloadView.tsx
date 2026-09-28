import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Link2,
  ClipboardPaste,
  Trash2,
  Music,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Headphones,
  Folder,
  Play,
  Sparkles,
  ExternalLink,
  X,
} from 'lucide-react';
import { api } from '../../api/client';
import { DirectVideoItem, AudioFormat, DownloadBatch } from '../../api/types';

interface DirectDownloadViewProps {
  onRefreshWorkflow?: () => void;
  onNavigatePlayer?: () => void;
}

export const DirectDownloadView: React.FC<DirectDownloadViewProps> = ({
  onRefreshWorkflow,
  onNavigatePlayer,
}) => {
  const queryClient = useQueryClient();

  const [rawText, setRawText] = useState('');
  const [outputDir, setOutputDir] = useState<string>(() => {
    try {
      return localStorage.getItem('auralytica-output') || '~/Music/Auralytica';
    } catch {
      return '~/Music/Auralytica';
    }
  });
  const [selectedFormat, setSelectedFormat] = useState<AudioFormat>('m4a_alac');
  const [resolvedVideos, setResolvedVideos] = useState<DirectVideoItem[]>([]);
  const [invalidUrls, setInvalidUrls] = useState<string[]>([]);
  const [activeBatchId, setActiveBatchId] = useState<number | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Sync outputDir to localStorage
  const handleOutputDirChange = (val: string) => {
    setOutputDir(val);
    try {
      localStorage.setItem('auralytica-output', val);
    } catch {}
  };

  // Split input into lines/tokens
  const parseRawUrls = (text: string): string[] => {
    return text
      .split(/[\r\n,\s]+/)
      .map((s) => s.trim())
      .filter(Boolean);
  };

  // Resolve mutation
  const resolveMutation = useMutation({
    mutationFn: (urls: string[]) => api.resolveDirectUrls(urls),
    onSuccess: (data) => {
      setResolvedVideos(data.videos);
      setInvalidUrls(data.invalid_urls);
      if (data.videos.length === 0 && data.invalid_urls.length > 0) {
        setErrorMsg('Không tìm thấy link YouTube hợp lệ nào trong nội dung đã dán.');
      } else {
        setErrorMsg(null);
      }
    },
    onError: (err: Error) => {
      setErrorMsg(`Lỗi phân tích liên kết: ${err.message}`);
    },
  });

  // Submit download mutation
  const submitMutation = useMutation({
    mutationFn: (payload: { videos: DirectVideoItem[]; output_dir: string; format: AudioFormat }) =>
      api.submitDirectDownload(payload),
    onSuccess: (data) => {
      setActiveBatchId(data.batch_id);
      setSuccessMsg(`Đã tạo lượt tải #${data.batch_id} gồm ${data.total_items} bài hát.`);
      queryClient.invalidateQueries({ queryKey: ['workflow'] });
      queryClient.invalidateQueries({ queryKey: ['player-library'] });
      if (onRefreshWorkflow) onRefreshWorkflow();
    },
    onError: (err: Error) => {
      setErrorMsg(`Lỗi khởi tạo tải: ${err.message}`);
    },
  });

  // Query active batch status if available
  const { data: batchData } = useQuery<DownloadBatch | null>({
    queryKey: ['download-batch', activeBatchId],
    queryFn: () => (activeBatchId ? api.getDownloadBatch(activeBatchId) : null),
    enabled: Boolean(activeBatchId),
    refetchInterval: (query) => {
      const b = query.state.data;
      if (!b) return 2000;
      return ['queued', 'running'].includes(b.status) ? 1500 : false;
    },
  });

  // Handle paste from clipboard
  const handlePasteClipboard = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        const newText = rawText ? `${rawText}\n${text}` : text;
        setRawText(newText);
        const urls = parseRawUrls(newText);
        if (urls.length > 0) {
          resolveMutation.mutate(urls);
        }
      }
    } catch {
      setErrorMsg('Trình duyệt không cho phép truy cập clipboard. Bạn vui lòng dùng Ctrl+V / Cmd+V để dán trực tiếp.');
    }
  };

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setRawText(val);
  };

  const handleAnalyzeClick = () => {
    const urls = parseRawUrls(rawText);
    if (urls.length === 0) {
      setErrorMsg('Vui lòng dán ít nhất một liên kết YouTube.');
      return;
    }
    resolveMutation.mutate(urls);
  };

  const handleRemoveResolved = (index: number) => {
    setResolvedVideos((prev) => prev.filter((_, idx) => idx !== index));
  };

  const handleStartDownload = () => {
    if (resolvedVideos.length === 0) {
      setErrorMsg('Chưa có bài hát nào sẵn sàng để tải.');
      return;
    }
    setErrorMsg(null);
    submitMutation.mutate({
      videos: resolvedVideos,
      output_dir: outputDir,
      format: selectedFormat,
    });
  };

  const formatDuration = (seconds?: number) => {
    if (!seconds || isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const rawUrlsCount = parseRawUrls(rawText).length;

  return (
    <div className="flex-1 overflow-y-auto px-4 py-8 md:px-8 max-w-5xl mx-auto space-y-6">
      {/* Hero Header */}
      <div className="glass-panel p-6 rounded-2xl border border-white/10 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 p-8 opacity-10 pointer-events-none">
          <Link2 className="w-48 h-48 text-emerald-400" />
        </div>
        <div className="relative z-10 space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
            <Sparkles className="w-3.5 h-3.5" />
            <span>05 · Direct Download</span>
          </div>
          <h1 className="text-xl md:text-2xl font-bold tracking-tight text-white">
            Tải nhạc trực tiếp từ YouTube
          </h1>
          <p className="text-xs md:text-sm text-zinc-400 max-w-2xl leading-relaxed">
            Dán một hoặc nhiều liên kết YouTube (video đơn, Shorts, Playlist) để trích xuất âm thanh chất lượng cao về thư viện nhạc cục bộ mà không cần nạp lịch sử Google Takeout.
          </p>
        </div>
      </div>

      {/* Error / Success Notifications */}
      {errorMsg && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <button
            type="button"
            onClick={() => setErrorMsg(null)}
            className="p-1 hover:bg-rose-500/20 rounded-md transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{successMsg}</span>
          </div>
          <button
            type="button"
            onClick={() => setSuccessMsg(null)}
            className="p-1 hover:bg-emerald-500/20 rounded-md transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Input Section */}
      <div className="glass-panel p-6 rounded-2xl border border-white/10 space-y-4 shadow-xl">
        <div className="flex items-center justify-between gap-4">
          <label className="text-xs font-semibold uppercase tracking-wider text-zinc-300 flex items-center gap-2">
            <Link2 className="w-4 h-4 text-emerald-400" />
            <span>Danh sách liên kết YouTube</span>
            {rawUrlsCount > 0 && (
              <span className="text-[11px] font-normal px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400 border border-white/5">
                {rawUrlsCount} link
              </span>
            )}
          </label>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handlePasteClipboard}
              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-white/10 flex items-center gap-1.5 transition-colors"
              title="Dán nhanh nội dung từ clipboard"
            >
              <ClipboardPaste className="w-3.5 h-3.5 text-emerald-400" />
              <span>Dán clipboard</span>
            </button>

            {rawText && (
              <button
                type="button"
                onClick={() => {
                  setRawText('');
                  setResolvedVideos([]);
                  setInvalidUrls([]);
                }}
                className="px-2.5 py-1.5 text-xs font-medium rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
                title="Xóa trắng nội dung"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>

        <textarea
          id="direct-urls-input"
          rows={5}
          value={rawText}
          onChange={handleTextChange}
          placeholder="Dán các link YouTube vào đây (mỗi dòng một link hoặc cách nhau bằng dấu cách)&#10;Ví dụ:&#10;https://www.youtube.com/watch?v=dQw4w9WgXcQ&#10;https://youtu.be/dQw4w9WgXcQ&#10;https://www.youtube.com/playlist?list=PL1234567890abcdef&#10;https://www.youtube.com/shorts/dQw4w9WgXcQ"
          className="w-full px-4 py-3 text-xs font-mono rounded-xl bg-zinc-950/80 border border-white/10 text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-emerald-500 focus:border-emerald-500 transition-all resize-y"
        />

        <div className="flex items-center justify-between pt-1">
          <p className="text-[11px] text-zinc-500">
            Hỗ trợ URL video thông thường, link rút gọn youtu.be, video Shorts và link Playlist.
          </p>
          <button
            id="analyze-urls-btn"
            type="button"
            disabled={rawUrlsCount === 0 || resolveMutation.isPending}
            onClick={handleAnalyzeClick}
            className="px-4 py-2 text-xs font-semibold rounded-lg bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-zinc-950 font-medium flex items-center gap-1.5 transition-all shadow-md"
          >
            {resolveMutation.isPending ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Đang phân tích...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5" />
                <span>Phân tích liên kết</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Resolved Videos Preview List */}
      {resolvedVideos.length > 0 && (
        <div className="glass-panel p-6 rounded-2xl border border-white/10 space-y-4 shadow-xl">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <h2 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
                <Music className="w-4 h-4 text-emerald-400" />
                <span>Danh sách bài hát tìm thấy ({resolvedVideos.length})</span>
              </h2>
              <p className="text-[11px] text-zinc-400">
                Kiểm tra danh sách bài hát trước khi tiến hành tải. Bạn có thể bấm nút X để loại bỏ bài không mong muốn.
              </p>
            </div>
            {invalidUrls.length > 0 && (
              <span className="text-[11px] text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-full">
                {invalidUrls.length} link không hợp lệ bị bỏ qua
              </span>
            )}
          </div>

          <div className="divide-y divide-white/[0.04] max-h-72 overflow-y-auto pr-1">
            {resolvedVideos.map((video, idx) => (
              <div
                key={`${video.video_id}-${idx}`}
                className="py-2.5 px-3 flex items-center justify-between gap-3 hover:bg-white/[0.02] rounded-lg transition-colors group"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <span className="text-[11px] font-mono text-zinc-500 w-5 text-right shrink-0">
                    {idx + 1}
                  </span>
                  <div className="w-10 h-10 rounded-lg overflow-hidden bg-zinc-900 border border-white/10 shrink-0">
                    <img
                      src={video.thumbnail_url || `https://i.ytimg.com/vi/${video.video_id}/hqdefault.jpg`}
                      alt={video.title}
                      className="w-full h-full object-cover"
                      loading="lazy"
                    />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium text-zinc-200 truncate" title={video.title}>
                      {video.title}
                    </p>
                    <p className="text-[11px] text-zinc-400 truncate flex items-center gap-2">
                      <span>{video.channel || 'YouTube'}</span>
                      {video.duration ? (
                        <>
                          <span>·</span>
                          <span className="font-mono">{formatDuration(video.duration)}</span>
                        </>
                      ) : null}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <a
                    href={video.url || `https://www.youtube.com/watch?v=${video.video_id}`}
                    target="_blank"
                    rel="noreferrer"
                    className="p-1.5 text-zinc-500 hover:text-zinc-300 transition-colors"
                    title="Mở video trên YouTube"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                  <button
                    type="button"
                    onClick={() => handleRemoveResolved(idx)}
                    className="p-1.5 text-zinc-500 hover:text-rose-400 transition-colors"
                    title="Xóa bài này khỏi danh sách tải"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Configuration & Action Card */}
      <div className="glass-panel p-6 rounded-2xl border border-white/10 space-y-6 shadow-xl">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
          Cài đặt tải & Định dạng âm thanh
        </h2>

        <div className="space-y-2">
          <label className="text-xs font-medium text-zinc-300 flex items-center gap-2">
            <Folder className="w-3.5 h-3.5 text-emerald-400" />
            <span>Thư mục lưu trên máy</span>
          </label>
          <input
            type="text"
            value={outputDir}
            onChange={(e) => handleOutputDirChange(e.target.value)}
            className="w-full px-4 py-2.5 text-xs font-mono rounded-xl bg-zinc-950/80 border border-white/10 text-zinc-200 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            placeholder="~/Music/Auralytica"
          />
        </div>

        {/* Audio Format Selector */}
        <div className="space-y-2">
          <label className="text-xs font-medium text-zinc-300">
            Định dạng âm thanh xuất xưởng
          </label>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* ALAC */}
            <div
              onClick={() => setSelectedFormat('m4a_alac')}
              className={`p-4 rounded-xl border transition-all cursor-pointer ${
                selectedFormat === 'm4a_alac'
                  ? 'border-emerald-500/60 bg-emerald-500/5 shadow-md'
                  : 'border-white/10 bg-zinc-900/40 hover:border-white/20'
              }`}
            >
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold text-zinc-100">Lossless ALAC (M4A)</span>
                <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Chuẩn Apple Music
                </span>
              </div>
              <p className="text-[11px] text-zinc-400 leading-relaxed">
                Trích xuất bit-perfect từ Opus nguồn sang ALAC không suy hao, tương thích hoàn hảo với Apple Music và mọi trình phát cao cấp.
              </p>
            </div>

            {/* MP3 */}
            <div
              onClick={() => setSelectedFormat('mp3')}
              className={`p-4 rounded-xl border transition-all cursor-pointer ${
                selectedFormat === 'mp3'
                  ? 'border-emerald-500/60 bg-emerald-500/5 shadow-md'
                  : 'border-white/10 bg-zinc-900/40 hover:border-white/20'
              }`}
            >
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold text-zinc-100">MP3 (320 kbps)</span>
                <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400 border border-white/5">
                  Phổ thông
                </span>
              </div>
              <p className="text-[11px] text-zinc-400 leading-relaxed">
                Định dạng tương thích tối đa với mọi máy nghe nhạc di động, dàn loa ô tô và hệ thống âm thanh đời cũ.
              </p>
            </div>
          </div>
        </div>

        {/* Start Download Button */}
        <div className="pt-2 flex items-center justify-end gap-3">
          <button
            id="start-direct-download-btn"
            type="button"
            disabled={resolvedVideos.length === 0 || submitMutation.isPending}
            onClick={handleStartDownload}
            className="w-full md:w-auto px-6 py-2.5 text-xs font-semibold rounded-xl bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 text-zinc-950 font-medium flex items-center justify-center gap-2 transition-all shadow-lg hover:shadow-emerald-500/20"
          >
            {submitMutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Đang khởi tạo tải...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" />
                <span>Bắt đầu tải {resolvedVideos.length > 0 ? `(${resolvedVideos.length} bài)` : ''}</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Active Batch Progress Monitor */}
      {batchData && (
        <div className="glass-panel p-6 rounded-2xl border border-white/10 space-y-4 shadow-xl">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="space-y-0.5">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-semibold text-zinc-100">
                  Tiến trình tải lượt #{batchData.batch_id}
                </h3>
                <span
                  className={`text-[10px] font-medium px-2 py-0.5 rounded-full uppercase tracking-wider ${
                    batchData.status === 'completed'
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      : batchData.status === 'running'
                      ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20'
                      : 'bg-zinc-800 text-zinc-400 border border-white/5'
                  }`}
                >
                  {batchData.status}
                </span>
              </div>
              <p className="text-[11px] text-zinc-400">
                Đã hoàn thành {batchData.counts?.completed || 0} / {batchData.total} bài
                {batchData.counts?.failed ? ` · ${batchData.counts.failed} bài lỗi` : ''}
              </p>
            </div>

            {onNavigatePlayer && (
              <button
                type="button"
                onClick={onNavigatePlayer}
                className={`px-4 py-2 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-all shadow-md ${
                  batchData.status === 'completed'
                    ? 'bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-medium'
                    : 'bg-zinc-800 hover:bg-zinc-700 text-zinc-100 border border-white/10'
                }`}
              >
                <Headphones className="w-3.5 h-3.5" />
                <span>{batchData.status === 'completed' ? 'Mở trong Player nghe ngay' : 'Mở Music Player'}</span>
              </button>
            )}
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-zinc-950 rounded-full h-2 overflow-hidden border border-white/5">
            <div
              className={`h-full transition-all duration-300 ${
                batchData.status === 'completed' ? 'bg-emerald-400' : 'bg-sky-400'
              }`}
              style={{
                width: `${
                  batchData.total > 0
                    ? Math.round(
                        (((batchData.counts?.completed || 0) + (batchData.counts?.skipped || 0)) /
                          batchData.total) *
                          100
                      )
                    : 0
                }%`,
              }}
            />
          </div>

          {/* Items breakdown list */}
          {batchData.items && batchData.items.length > 0 && (
            <div className="divide-y divide-white/[0.04] max-h-60 overflow-y-auto text-xs pr-1">
              {batchData.items.map((item) => (
                <div key={item.video_id} className="py-2 flex items-center justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="text-zinc-200 font-medium truncate">{item.title || item.video_id}</p>
                    <p className="text-[11px] text-zinc-500 truncate">
                      {item.error_message ? (
                        <span className="text-rose-400">{item.error_message}</span>
                      ) : (
                        <span>ID: {item.video_id}</span>
                      )}
                    </p>
                  </div>
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded-full shrink-0 ${
                      item.status === 'completed'
                        ? 'text-emerald-400 bg-emerald-500/10'
                        : item.status === 'running'
                        ? 'text-sky-400 bg-sky-500/10'
                        : item.status === 'failed'
                        ? 'text-rose-400 bg-rose-500/10'
                        : 'text-zinc-400 bg-zinc-800'
                    }`}
                  >
                    {item.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
