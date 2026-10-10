import React, { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Zap,
  Link2,
  ClipboardPaste,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Headphones,
  Play,
  Pause,
  RotateCcw,
  SkipForward,
  Sparkles,
  ExternalLink,
  X,
  Sliders,
  Folder,
  Wand2,
  Music,
} from 'lucide-react';
import { api } from '../../api/client';
import { DirectVideoItem, AudioFormat, DownloadBatchItem } from '../../api/types';

interface QuickDownloadViewProps {
  onRefreshWorkflow?: () => void;
  onNavigatePlayer?: () => void;
}

const ERROR_CODE_LABELS: Record<string, { label: string; color: string; desc: string }> = {
  unavailable: { label: 'Đã xóa / Riêng tư', color: 'text-rose-400 bg-rose-500/10 border-rose-500/20', desc: 'Video đã bị gỡ bỏ hoặc kênh đã chấm dứt.' },
  bot_blocked: { label: 'Chặn Bot', color: 'text-amber-300 bg-amber-500/10 border-amber-500/20', desc: 'IP bị YouTube chặn tạm thời.' },
  rate_limited: { label: 'Giới hạn tần suất', color: 'text-amber-300 bg-amber-500/10 border-amber-500/20', desc: 'Quá nhiều yêu cầu. Đợi 1-3 phút.' },
  age_restricted: { label: 'Giới hạn độ tuổi', color: 'text-orange-300 bg-orange-500/10 border-orange-500/20', desc: 'Cần đăng nhập tài khoản YouTube.' },
  geo_restricted: { label: 'Chặn vùng', color: 'text-purple-300 bg-purple-500/10 border-purple-500/20', desc: 'Video không khả dụng tại khu vực này.' },
  format_unavailable: { label: 'Không có định dạng', color: 'text-zinc-300 bg-zinc-500/10 border-zinc-500/20', desc: 'Không tìm thấy luồng âm thanh.' },
  network_error: { label: 'Lỗi mạng', color: 'text-sky-300 bg-sky-500/10 border-sky-500/20', desc: 'Timeout kết nối.' },
  filesystem: { label: 'Lỗi ổ đĩa', color: 'text-rose-400 bg-rose-500/10 border-rose-500/20', desc: 'Đầy dung lượng hoặc thiếu quyền ghi.' },
  download_error: { label: 'Lỗi tải', color: 'text-zinc-300 bg-zinc-500/10 border-zinc-500/20', desc: 'Lỗi không xác định.' },
};

type StatusFilter = 'all' | 'failed' | 'running' | 'queued' | 'completed';

export const QuickDownloadView: React.FC<QuickDownloadViewProps> = ({
  onRefreshWorkflow,
  onNavigatePlayer,
}) => {
  const queryClient = useQueryClient();
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Inputs & URL resolution state
  const [rawText, setRawText] = useState('');
  const [resolvedVideos, setResolvedVideos] = useState<DirectVideoItem[]>([]);
  const [invalidUrls, setInvalidUrls] = useState<string[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Settings
  const [outputDir, setOutputDir] = useState(() => localStorage.getItem('auralytica-output') || '~/Music/Auralytica');
  const [selectedFormat, setSelectedFormat] = useState<AudioFormat>(() => (localStorage.getItem('auralytica-format') as AudioFormat) || 'm4a_alac');
  const [concurrency, setConcurrency] = useState<number>(() => parseInt(localStorage.getItem('auralytica-concurrency') || '3', 10));

  // Batch state
  const [activeBatchId, setActiveBatchId] = useState<number | null>(() => {
    const saved = localStorage.getItem('auralytica_direct_batch_id');
    return saved ? parseInt(saved, 10) : null;
  });
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [batchPage, setBatchPage] = useState(1);

  // Persist settings
  useEffect(() => {
    localStorage.setItem('auralytica-output', outputDir);
    localStorage.setItem('auralytica-format', selectedFormat);
    localStorage.setItem('auralytica-concurrency', String(concurrency));
    if (activeBatchId) localStorage.setItem('auralytica_direct_batch_id', String(activeBatchId));
  }, [outputDir, selectedFormat, concurrency, activeBatchId]);

  // Keyboard: Ctrl+Enter to analyze
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        handleAnalyzeClick();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [rawText]);

  // Mutations
  const resolveMutation = useMutation({
    mutationFn: (urls: string[]) => api.resolveDirectUrls(urls),
    onSuccess: (data) => {
      setResolvedVideos(data.videos);
      setInvalidUrls(data.invalid_urls);
      setErrorMsg(null);
      if (data.videos.length === 0 && data.invalid_urls.length > 0) {
        setErrorMsg('Không tìm thấy video hợp lệ nào từ các liên kết đã cung cấp.');
      } else {
        setSuccessMsg(`Đã phân tích ${data.videos.length} bài hát.`);
        setTimeout(() => setSuccessMsg(null), 4000);
      }
    },
    onError: (err: any) => setErrorMsg(`Lỗi phân tích: ${err.message}`),
  });

  const submitMutation = useMutation({
    mutationFn: (payload: { videos: DirectVideoItem[]; output_dir: string; format: AudioFormat; concurrency: number }) => api.submitDirectDownload(payload),
    onSuccess: (data) => {
      setActiveBatchId(data.batch_id);
      setSuccessMsg(`Đã tạo lượt tải #${data.batch_id} gồm ${data.total_items} bài.`);
      setErrorMsg(null);
      queryClient.invalidateQueries({ queryKey: ['downloads'] });
      queryClient.invalidateQueries({ queryKey: ['workflow'] });
      onRefreshWorkflow?.();
    },
    onError: (err: any) => setErrorMsg(`Lỗi khởi tạo: ${err.message}`),
  });

  const batchQuery = useQuery({
    queryKey: ['download-batch', activeBatchId, batchPage, statusFilter],
    queryFn: () => activeBatchId ? api.getDownloadBatch(activeBatchId, batchPage, 20, statusFilter === 'all' ? undefined : statusFilter) : null,
    enabled: Boolean(activeBatchId),
    refetchInterval: (q) => {
      const b = q.state.data;
      if (!b) return 2000;
      return ['queued', 'running'].includes(b.status) ? 1500 : 5000;
    },
  });

  const pauseMutation = useMutation({ mutationFn: (id: number) => api.stopDownload(id), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['download-batch', activeBatchId] }) });
  const resumeMutation = useMutation({ mutationFn: (id: number) => api.resumeDownload(id), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['download-batch', activeBatchId] }) });
  const retryFailedMutation = useMutation({ mutationFn: (id: number) => api.retryFailedDownloads(id), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['download-batch', activeBatchId] }) });
  const skipFailedMutation = useMutation({ mutationFn: (id: number) => api.skipFailedDownloads(id), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['download-batch', activeBatchId] }) });
  const retryItemMutation = useMutation({ mutationFn: ({ batchId, videoId }: { batchId: number; videoId: string }) => api.retryDownloadItem(batchId, videoId), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['download-batch', activeBatchId] }) });
  // Skip mutation for future use
  // eslint-disable-next-line @typescript-eslint/no-unused-vars

  // Handlers
  const handlePasteClipboard = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        setRawText((prev) => (prev.trim() ? `${prev.trim()}\n${text.trim()}` : text.trim()));
        textareaRef.current?.focus();
      }
    } catch {
      setErrorMsg('Không thể đọc clipboard. Dán thủ công bằng Ctrl+V.');
    }
  };

  const parseLines = (text: string) => text.split(/[\r\n\s]+/).map(s => s.trim()).filter(s => s.length > 0);

  const handleAnalyzeClick = () => {
    const urls = parseLines(rawText);
    if (urls.length === 0) {
      setErrorMsg('Dán ít nhất 1 liên kết YouTube.');
      return;
    }
    setErrorMsg(null);
    resolveMutation.mutate(urls);
  };

  const handleUpdateItem = (videoId: string, updates: Partial<DirectVideoItem>) => {
    setResolvedVideos((prev) => prev.map((item) => (item.video_id === videoId ? { ...item, ...updates } : item)));
  };

  const handleRemoveItem = (videoId: string) => {
    setResolvedVideos((prev) => prev.filter((item) => item.video_id !== videoId));
  };

  const handleAutoCleanTitles = () => {
    setResolvedVideos((prev) => prev.map((item) => {
      let title = item.title || '';
      let artist = item.artist || item.channel || '';
      title = title.replace(/\s*\[(?:Official\s*)?(?:Music\s*)?Video\]/gi, '')
        .replace(/\s*\((?:Official\s*)?(?:Music\s*)?Video\)/gi, '')
        .replace(/\s*\[MV\]|\(MV\)|\s*\(Lyrics\)|\s*\[Lyrics\]|\s*\(Audio\)|\s*\[Audio\]/gi, '')
        .replace(/\s*\((?:4K|HD)\s*Remaster\)/gi, '')
        .replace(/\s*-\s*Topic\s*$/i, '').trim();
      if (title.includes(' - ')) {
        const parts = title.split(' - ');
        if (parts.length >= 2) { artist = parts[0].trim(); title = parts.slice(1).join(' - ').trim(); }
      }
      return { ...item, title, artist };
    }));
    setSuccessMsg('Đã chuẩn hóa tiêu đề.');
    setTimeout(() => setSuccessMsg(null), 3000);
  };

  const handleStartDownload = () => {
    if (resolvedVideos.length === 0) { setErrorMsg('Không có bài hát nào để tải.'); return; }
    setErrorMsg(null);
    submitMutation.mutate({ videos: resolvedVideos, output_dir: outputDir.trim() || '~/Music/Auralytica', format: selectedFormat, concurrency });
  };

  const rawUrlsCount = parseLines(rawText).length;
  const batchData = batchQuery.data;
  const counts = batchData?.counts || {};
  const completedCount = (counts.completed || 0) + (counts.skipped || 0);
  const failedCount = counts.failed || 0;
  const runningCount = counts.running || 0;
  const totalCount = batchData?.total || 0;

  const formatDuration = (sec?: number) => {
    if (!sec || sec <= 0) return '';
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  const totalDuration = resolvedVideos.reduce((sum, v) => sum + (v.duration || 0), 0);
  const formatTotalDuration = () => {
    const h = Math.floor(totalDuration / 3600);
    const m = Math.floor((totalDuration % 3600) / 60);
    return h > 0 ? `${h}h ${m}m` : `${m} phút`;
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="shrink-0 p-4 border-b border-white/10 bg-[#09090b]/80">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-spotify-500/15 border border-spotify-500/30 text-spotify-400 text-xs font-semibold">
              <Zap className="w-3 h-3 fill-current" />
              Tải nhanh YouTube
            </span>
            <span className="text-[11px] text-zinc-500 hidden sm:inline">Ctrl+Enter để phân tích</span>
          </div>
          <button
            type="button"
            onClick={handlePasteClipboard}
            className="px-3 py-1.5 text-xs font-medium rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-white/10 flex items-center gap-1.5 transition-colors"
            aria-label="Dán từ clipboard"
          >
            <ClipboardPaste className="w-3.5 h-3.5 text-amber-400" />
            <span>Dán</span>
          </button>
        </div>
      </div>

      {/* Notifications */}
      <div className="shrink-0 max-w-7xl mx-auto w-full px-4 pt-3">
        {errorMsg && (
          <div role="alert" className="mb-2 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm flex items-center justify-between">
            <div className="flex items-center gap-2"><AlertCircle className="w-4 h-4 text-rose-400 shrink-0" /><span>{errorMsg}</span></div>
            <button type="button" onClick={() => setErrorMsg(null)} className="p-1 hover:bg-rose-500/20 rounded" aria-label="Đóng"><X className="w-3.5 h-3.5" /></button>
          </div>
        )}
        {successMsg && (
          <div role="status" className="mb-2 p-3 rounded-lg bg-spotify-500/10 border border-spotify-500/20 text-spotify-300 text-sm flex items-center justify-between">
            <div className="flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-spotify-400 shrink-0" /><span>{successMsg}</span></div>
            <button type="button" onClick={() => setSuccessMsg(null)} className="p-1 hover:bg-spotify-500/20 rounded" aria-label="Đóng"><X className="w-3.5 h-3.5" /></button>
          </div>
        )}
      </div>

      {/* Main Content: 2-column layout */}
      <div className="flex-1 min-h-0 max-w-7xl mx-auto w-full p-4 flex flex-col lg:flex-row gap-4">
        {/* Left Column: URL Input + Video List */}
        <div className="flex-1 min-w-0 flex flex-col gap-4">
          {/* URL Input */}
          <div className="shrink-0 glass-panel p-4 rounded-xl">
            <div className="flex items-center justify-between gap-3 mb-3">
              <div className="flex items-center gap-2">
                <Link2 className="w-4 h-4 text-amber-400" />
                <span className="text-sm font-semibold text-zinc-100">Liên kết YouTube</span>
                {rawUrlsCount > 0 && (
                  <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400 border border-white/10">{rawUrlsCount} link</span>
                )}
              </div>
              {rawText && (
                <button type="button" onClick={() => { setRawText(''); setResolvedVideos([]); setInvalidUrls([]); }} className="p-1.5 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors" aria-label="Xóa tất cả">
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
            <textarea
              ref={textareaRef}
              id="direct-urls-input"
              rows={2}
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              placeholder="Dán link YouTube vào đây (mỗi dòng một link)"
              className="w-full px-4 py-2.5 text-sm font-mono rounded-lg bg-zinc-950/80 border border-white/10 text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-spotify-500 resize-none"
            />
            <div className="flex items-center justify-between gap-3 mt-3">
              <p className="text-xs text-zinc-500">Hỗ trợ video, Shorts, Playlist</p>
              <button
                type="button"
                disabled={rawUrlsCount === 0 || resolveMutation.isPending}
                onClick={handleAnalyzeClick}
                className="px-4 py-2 text-sm font-semibold rounded-lg bg-spotify-500 hover:bg-spotify-400 disabled:opacity-40 text-zinc-950 flex items-center gap-2 transition-all cursor-pointer"
              >
                {resolveMutation.isPending ? <><Loader2 className="w-4 h-4 animate-spin" /><span>Đang phân tích...</span></> : <><Sparkles className="w-4 h-4" /><span>Phân tích {rawUrlsCount > 0 ? `(${rawUrlsCount})` : ''}</span></>}
              </button>
            </div>
          </div>

          {/* Video List - Full scroll */}
          {resolvedVideos.length > 0 ? (
            <div className="flex-1 min-h-0 glass-panel rounded-xl flex flex-col">
              {/* List Header */}
              <div className="shrink-0 p-3 border-b border-white/5 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Music className="w-4 h-4 text-spotify-400" />
                  <span className="text-sm font-semibold text-zinc-100">{resolvedVideos.length} bài hát</span>
                  {totalDuration > 0 && <span className="text-xs text-zinc-500">{formatTotalDuration()}</span>}
                </div>
                <div className="flex items-center gap-2">
                  <button type="button" onClick={handleAutoCleanTitles} className="px-2.5 py-1 text-xs font-medium rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-white/10 flex items-center gap-1.5 transition-all cursor-pointer" aria-label="Làm sạch tiêu đề">
                    <Wand2 className="w-3.5 h-3.5 text-spotify-400" /><span>Làm sạch</span>
                  </button>
                  <button type="button" onClick={() => setResolvedVideos([])} className="px-2 py-1 text-xs rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors cursor-pointer" aria-label="Xóa tất cả">
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Invalid URLs */}
              {invalidUrls.length > 0 && (
                <div className="shrink-0 p-2 bg-amber-500/10 border-b border-amber-500/20">
                  <p className="text-xs text-amber-300 flex items-center gap-1.5"><AlertCircle className="w-3.5 h-3.5" />{invalidUrls.length} liên kết không hợp lệ</p>
                </div>
              )}

              {/* Scrollable List */}
              <div className="flex-1 min-h-0 overflow-y-auto">
                {resolvedVideos.map((video) => {
                  const ext = selectedFormat === 'mp3' ? 'mp3' : 'm4a';
                  const plannedFilename = `${video.artist || 'Unknown'} - ${video.title || 'Untitled'}.${ext}`;
                  return (
                    <div key={video.video_id} className="p-3 border-b border-white/5 last:border-0 hover:bg-white/[0.02] transition-colors">
                      <div className="flex items-start gap-3">
                        {/* Thumbnail */}
                        <div className="relative w-20 h-14 rounded-lg overflow-hidden bg-zinc-900 border border-white/10 shrink-0">
                          <img src={video.thumbnail_url || `https://i.ytimg.com/vi/${video.video_id}/hqdefault.jpg`} alt="" className="w-full h-full object-cover" onError={(e) => (e.target as HTMLElement).style.display = 'none'} />
                          {video.duration && (
                            <div className="absolute bottom-0.5 right-0.5 px-1 py-0.5 rounded bg-black/80 text-[9px] font-mono text-white">{formatDuration(video.duration)}</div>
                          )}
                        </div>

                        {/* Info */}
                        <div className="flex-1 min-w-0 space-y-1.5">
                          <div>
                            {video.channel && (
                              <p className="text-xs text-zinc-500 truncate">{video.channel}</p>
                            )}
                            <h3 className="text-sm font-medium text-zinc-100 truncate">{video.title || video.video_id}</h3>
                          </div>

                          {/* Editable inputs */}
                          <div className="grid grid-cols-2 gap-2">
                            <input
                              type="text"
                              value={video.title || ''}
                              onChange={(e) => handleUpdateItem(video.video_id, { title: e.target.value })}
                              placeholder="Tiêu đề"
                              className="w-full px-2 py-1 text-xs rounded bg-zinc-950/80 border border-white/10 text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-spotify-500"
                            />
                            <input
                              type="text"
                              value={video.artist || ''}
                              onChange={(e) => handleUpdateItem(video.video_id, { artist: e.target.value })}
                              placeholder="Nghệ sĩ"
                              className="w-full px-2 py-1 text-xs rounded bg-zinc-950/80 border border-white/10 text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-spotify-500"
                            />
                          </div>

                          {/* File preview */}
                          <p className="text-[11px] font-mono text-zinc-500 truncate">
                            File: <span className="text-spotify-400">{plannedFilename}</span>
                          </p>
                        </div>

                        {/* Actions */}
                        <div className="flex items-center gap-1 shrink-0">
                          <a href={video.url || `https://www.youtube.com/watch?v=${video.video_id}`} target="_blank" rel="noopener noreferrer" className="p-1.5 rounded-lg bg-zinc-800/80 hover:bg-zinc-700 text-zinc-400 hover:text-zinc-200 transition-colors" aria-label="Mở YouTube">
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                          <button type="button" onClick={() => handleRemoveItem(video.video_id)} className="p-1.5 rounded-lg bg-zinc-800/80 hover:bg-rose-500/20 text-zinc-400 hover:text-rose-400 transition-colors cursor-pointer" aria-label="Xóa">
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="flex-1 min-h-0 glass-panel rounded-xl flex items-center justify-center">
              <div className="text-center text-zinc-500 p-8">
                <Music className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p className="text-sm">Dán liên kết YouTube để bắt đầu</p>
                <p className="text-xs mt-1 text-zinc-600">Hỗ trợ video, Shorts, Playlist</p>
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Settings (sticky on desktop) */}
        <div className="w-full lg:w-72 shrink-0">
          <div className="glass-panel p-4 rounded-xl space-y-4 lg:sticky lg:top-4">
            <div className="flex items-center gap-2 pb-3 border-b border-white/5">
              <Sliders className="w-4 h-4 text-spotify-400" />
              <span className="text-sm font-semibold text-zinc-100">Cài đặt</span>
            </div>

            {/* Directory */}
            <div>
              <label htmlFor="output-dir" className="block text-xs font-medium text-zinc-400 mb-1.5 flex items-center gap-1.5">
                <Folder className="w-3 h-3" />Thư mục lưu trữ
              </label>
              <input
                id="output-dir"
                type="text"
                value={outputDir}
                onChange={(e) => setOutputDir(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg bg-zinc-950/80 border border-white/10 text-zinc-200 font-mono focus:outline-none focus:border-spotify-500"
              />
            </div>

            {/* Format */}
            <div>
              <span className="block text-xs font-medium text-zinc-400 mb-2">Định dạng</span>
              <div className="space-y-1.5">
                {[
                  { id: 'm4a_alac', name: 'Lossless ALAC', badge: 'Apple' },
                  { id: 'mp3', name: 'MP3 320kbps', badge: 'Phổ thông' },
                  { id: 'm4a_aac', name: 'AAC 256kbps', badge: 'Tiết kiệm' },
                ].map((fmt) => (
                  <button
                    key={fmt.id}
                    type="button"
                    onClick={() => setSelectedFormat(fmt.id as AudioFormat)}
                    className={`w-full p-2.5 rounded-lg border text-left transition-all ${
                      selectedFormat === fmt.id
                        ? 'bg-spotify-500/15 border-spotify-400/50 text-white'
                        : 'bg-zinc-950/40 border-white/5 text-zinc-300 hover:border-white/20'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{fmt.name}</span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                        selectedFormat === fmt.id ? 'bg-spotify-500/25 text-spotify-200' : 'bg-white/5 text-zinc-500'
                      }`}>{fmt.badge}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Concurrency */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-zinc-400">Tốc độ</span>
                <span className="text-sm font-bold text-spotify-400">{concurrency}x</span>
              </div>
              <input
                type="range"
                min={1}
                max={8}
                value={concurrency}
                onChange={(e) => setConcurrency(parseInt(e.target.value, 10))}
                className="w-full accent-spotify-500 h-1.5 bg-zinc-800 rounded-lg cursor-pointer"
              />
              <div className="flex justify-between mt-1 text-[10px] text-zinc-500">
                <span>1x</span><span>4x</span><span>8x</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Sticky Action Bar */}
      <div className="shrink-0 p-4 border-t border-white/10 bg-[#09090b]/95 backdrop-blur-md">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-4 text-sm text-zinc-400">
            {resolvedVideos.length > 0 ? (
              <>
                <span>{resolvedVideos.length} bài</span>
                {totalDuration > 0 && <span>{formatTotalDuration()}</span>}
              </>
            ) : (
              <span className="text-zinc-500">Chưa chọn bài nào</span>
            )}
          </div>
          <button
            type="button"
            disabled={resolvedVideos.length === 0 || submitMutation.isPending}
            onClick={handleStartDownload}
            className="px-6 py-2.5 text-sm font-bold rounded-xl bg-spotify-500 hover:bg-spotify-400 disabled:opacity-40 text-zinc-950 flex items-center gap-2 transition-all shadow-lg shadow-spotify-500/25 cursor-pointer"
          >
            {submitMutation.isPending ? <><Loader2 className="w-4 h-4 animate-spin" /><span>Đang khởi tạo...</span></> : <><Play className="w-4 h-4 fill-current" /><span>Bắt đầu tải {resolvedVideos.length > 0 ? `(${resolvedVideos.length})` : ''}</span></>}
          </button>
        </div>
      </div>

      {/* Active Batch Progress (if any) */}
      {batchData && (
        <div className="shrink-0 max-w-7xl mx-auto w-full px-4 pb-4">
          <div className="glass-panel p-4 rounded-xl space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-zinc-100">Tiến trình #{batchData.batch_id}</span>
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  batchData.status === 'completed' ? 'bg-spotify-500/20 text-spotify-300' :
                  batchData.status === 'running' ? 'bg-sky-500/20 text-sky-300' :
                  batchData.status === 'paused' ? 'bg-amber-500/20 text-amber-300' :
                  'bg-zinc-800 text-zinc-300'
                }`}>
                  {batchData.status === 'completed' ? 'Hoàn tất' :
                   batchData.status === 'running' ? 'Đang tải...' :
                   batchData.status === 'paused' ? 'Đã dừng' : batchData.status}
                </span>
              </div>
              <span className="text-sm text-zinc-400">{completedCount} / {totalCount} bài{failedCount > 0 && <span className="text-rose-400 ml-1">• {failedCount} lỗi</span>}</span>
            </div>

            {/* Progress Bar */}
            <div className="w-full bg-zinc-950 rounded-full h-2 overflow-hidden border border-white/5">
              <div
                className={`h-full transition-all ${
                  batchData.status === 'completed' ? 'bg-spotify-400' :
                  failedCount > 0 ? 'bg-gradient-to-r from-spotify-400 to-amber-400' : 'bg-sky-400'
                }`}
                style={{ width: `${totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0}%` }}
              />
            </div>

            {/* Filter tabs */}
            <div className="flex gap-1 overflow-x-auto">
              {[
                { id: 'all', label: `Tất cả (${totalCount})` },
                { id: 'failed', label: `Lỗi (${failedCount})` },
                { id: 'running', label: `Tải (${runningCount})` },
                { id: 'completed', label: `Xong (${completedCount})` },
              ].map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => { setStatusFilter(tab.id as StatusFilter); setBatchPage(1); }}
                  className={`px-3 py-1 rounded-lg text-xs font-medium whitespace-nowrap ${
                    statusFilter === tab.id ? 'bg-zinc-800 text-white' : 'text-zinc-400 hover:text-zinc-200'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Items list */}
            {batchData.items?.length > 0 && (
              <div className="max-h-48 overflow-y-auto space-y-1">
                {batchData.items.map((item: DownloadBatchItem) => {
                  const errMeta = item.error_code ? ERROR_CODE_LABELS[item.error_code] : null;
                  return (
                    <div key={item.video_id} className="flex items-center justify-between p-2 rounded-lg hover:bg-white/[0.02]">
                      <div className="min-w-0 flex-1">
                        <p className="text-sm text-zinc-200 truncate">{item.title || item.video_id}</p>
                        {errMeta && <p className="text-xs text-rose-400 truncate">{errMeta.label}</p>}
                      </div>
                      <div className="flex items-center gap-2 shrink-0 ml-2">
                        <span className={`text-xs px-2 py-0.5 rounded ${
                          item.status === 'completed' ? 'bg-spotify-500/10 text-spotify-400' :
                          item.status === 'running' ? 'bg-sky-500/10 text-sky-400' :
                          item.status === 'failed' ? 'bg-rose-500/10 text-rose-400' : 'bg-zinc-800 text-zinc-400'
                        }`}>{item.status}</span>
                        {item.status === 'failed' && (
                          <button type="button" onClick={() => retryItemMutation.mutate({ batchId: batchData.batch_id, videoId: item.video_id })} className="p-1 rounded hover:bg-zinc-800 text-zinc-400 hover:text-white" aria-label="Thử lại">
                            <RotateCcw className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-2">
              {batchData.status === 'running' && (
                <button type="button" onClick={() => pauseMutation.mutate(batchData.batch_id)} className="px-3 py-1.5 text-xs font-medium rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-white/10 flex items-center gap-1.5" disabled={pauseMutation.isPending}>
                  <Pause className="w-3.5 h-3.5" /><span>Tạm dừng</span>
                </button>
              )}
              {batchData.status === 'paused' && (
                <button type="button" onClick={() => resumeMutation.mutate(batchData.batch_id)} className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-spotify-500 hover:bg-spotify-400 text-zinc-950 flex items-center gap-1.5" disabled={resumeMutation.isPending}>
                  <Play className="w-3.5 h-3.5 fill-current" /><span>Tiếp tục</span>
                </button>
              )}
              {failedCount > 0 && (
                <>
                  <button type="button" onClick={() => retryFailedMutation.mutate(batchData.batch_id)} className="px-3 py-1.5 text-xs font-medium rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/30 flex items-center gap-1.5" disabled={retryFailedMutation.isPending}>
                    <RotateCcw className="w-3.5 h-3.5" /><span>Thử lại ({failedCount})</span>
                  </button>
                  <button type="button" onClick={() => skipFailedMutation.mutate(batchData.batch_id)} className="px-3 py-1.5 text-xs font-medium rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border border-white/10 flex items-center gap-1.5" disabled={skipFailedMutation.isPending}>
                    <SkipForward className="w-3.5 h-3.5" /><span>Bỏ qua</span>
                  </button>
                </>
              )}
              {onNavigatePlayer && (
                <button type="button" onClick={onNavigatePlayer} className={`px-3 py-1.5 text-xs font-semibold rounded-lg flex items-center gap-1.5 ml-auto ${batchData.status === 'completed' ? 'bg-spotify-500 hover:bg-spotify-400 text-zinc-950' : 'bg-zinc-800 hover:bg-zinc-700 text-zinc-100 border border-white/10'}`}>
                  <Headphones className="w-3.5 h-3.5" /><span>{batchData.status === 'completed' ? 'Mở Player' : 'Music Player'}</span>
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
