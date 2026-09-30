import React, { useState, useEffect } from 'react';
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
    advice: 'Hãy xuất file cookies.txt từ trình duyệt và đặt vào ~/.local/share/auralytica/cookies.txt.',
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
    advice: 'Hệ thống đã hỗ trợ chế độ trích xuất stream không suy hao, hãy thử lại bài này.',
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

export const QuickDownloadView: React.FC<QuickDownloadViewProps> = ({
  onRefreshWorkflow,
  onNavigatePlayer,
}) => {
  const queryClient = useQueryClient();

  // Inputs & URL resolution state
  const [rawText, setRawText] = useState('');
  const [resolvedVideos, setResolvedVideos] = useState<DirectVideoItem[]>([]);
  const [invalidUrls, setInvalidUrls] = useState<string[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Settings matching DownloadView
  const [outputDir, setOutputDir] = useState<string>(() => {
    try {
      return localStorage.getItem('auralytica-output') || '~/Music/Auralytica';
    } catch {
      return '~/Music/Auralytica';
    }
  });

  const [selectedFormat, setSelectedFormat] = useState<AudioFormat>(() => {
    try {
      return (localStorage.getItem('auralytica-format') as AudioFormat) || 'm4a_alac';
    } catch {
      return 'm4a_alac';
    }
  });

  const [concurrency, setConcurrency] = useState<number>(() => {
    try {
      const saved = localStorage.getItem('auralytica-concurrency');
      return saved ? parseInt(saved, 10) || 3 : 3;
    } catch {
      return 3;
    }
  });

  // Active batch monitoring
  const [activeBatchId, setActiveBatchId] = useState<number | null>(() => {
    try {
      const saved = localStorage.getItem('auralytica_direct_batch_id');
      return saved ? parseInt(saved, 10) : null;
    } catch {
      return null;
    }
  });
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [batchPage, setBatchPage] = useState(1);

  // Persist settings
  useEffect(() => {
    try {
      localStorage.setItem('auralytica-output', outputDir);
      localStorage.setItem('auralytica-format', selectedFormat);
      localStorage.setItem('auralytica-concurrency', String(concurrency));
      if (activeBatchId) {
        localStorage.setItem('auralytica_direct_batch_id', String(activeBatchId));
      }
    } catch { }
  }, [outputDir, selectedFormat, concurrency, activeBatchId]);

  // Resolve URLs mutation
  const resolveMutation = useMutation({
    mutationFn: (urls: string[]) => api.resolveDirectUrls(urls),
    onSuccess: (data) => {
      setResolvedVideos(data.videos);
      setInvalidUrls(data.invalid_urls);
      setErrorMsg(null);
      if (data.videos.length === 0 && data.invalid_urls.length > 0) {
        setErrorMsg('Không tìm thấy video hợp lệ nào từ các liên kết đã cung cấp.');
      } else {
        setSuccessMsg(`Đã phân tích thành công ${data.videos.length} bài hát.`);
      }
    },
    onError: (err: any) => {
      setErrorMsg(`Lỗi phân tích URL: ${err.message}`);
    },
  });

  // Submit batch mutation
  const submitMutation = useMutation({
    mutationFn: (payload: {
      videos: DirectVideoItem[];
      output_dir: string;
      format: AudioFormat;
      concurrency: number;
    }) => api.submitDirectDownload(payload),
    onSuccess: (data) => {
      setActiveBatchId(data.batch_id);
      setSuccessMsg(`Đã tạo lượt tải #${data.batch_id} gồm ${data.total_items} bài hát.`);
      setErrorMsg(null);
      queryClient.invalidateQueries({ queryKey: ['downloads'] });
      queryClient.invalidateQueries({ queryKey: ['workflow'] });
      if (onRefreshWorkflow) onRefreshWorkflow();
    },
    onError: (err: any) => {
      setErrorMsg(`Lỗi khởi tạo tải: ${err.message}`);
    },
  });

  // Query active batch status
  const batchQuery = useQuery({
    queryKey: ['download-batch', activeBatchId, batchPage, statusFilter],
    queryFn: () =>
      activeBatchId
        ? api.getDownloadBatch(
            activeBatchId,
            batchPage,
            20,
            statusFilter === 'all' ? undefined : statusFilter
          )
        : null,
    enabled: Boolean(activeBatchId),
    refetchInterval: (query) => {
      const b = query.state.data;
      if (!b) return 2000;
      return ['queued', 'running'].includes(b.status) ? 1500 : 5000;
    },
  });

  // Batch control mutations (pause, resume, retry, skip)
  const pauseMutation = useMutation({
    mutationFn: (id: number) => api.stopDownload(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['download-batch', activeBatchId] }),
  });

  const resumeMutation = useMutation({
    mutationFn: (id: number) => api.resumeDownload(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['download-batch', activeBatchId] }),
  });

  const retryFailedMutation = useMutation({
    mutationFn: (id: number) => api.retryFailedDownloads(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['download-batch', activeBatchId] }),
  });

  const skipFailedMutation = useMutation({
    mutationFn: (id: number) => api.skipFailedDownloads(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['download-batch', activeBatchId] }),
  });

  const retryItemMutation = useMutation({
    mutationFn: ({ batchId, videoId }: { batchId: number; videoId: string }) =>
      api.retryDownloadItem(batchId, videoId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['download-batch', activeBatchId] }),
  });

  const skipItemMutation = useMutation({
    mutationFn: ({ batchId, videoId }: { batchId: number; videoId: string }) =>
      api.skipDownloadItem(batchId, videoId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['download-batch', activeBatchId] }),
  });

  // Clipboard paste
  const handlePasteClipboard = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        setRawText((prev) => (prev.trim() ? `${prev.trim()}\n${text.trim()}` : text.trim()));
      }
    } catch {
      setErrorMsg('Không thể đọc dữ liệu từ clipboard. Hãy dán thủ công bằng phím Ctrl+V.');
    }
  };

  const parseLines = (text: string): string[] => {
    return text
      .split(/[\r\n\s]+/)
      .map((s) => s.trim())
      .filter((s) => s.length > 0);
  };

  const handleAnalyzeClick = () => {
    const urls = parseLines(rawText);
    if (urls.length === 0) {
      setErrorMsg('Vui lòng dán ít nhất 1 liên kết YouTube.');
      return;
    }
    setErrorMsg(null);
    resolveMutation.mutate(urls);
  };

  // Edit item metadata inline
  const handleUpdateItem = (videoId: string, updates: Partial<DirectVideoItem>) => {
    setResolvedVideos((prev) =>
      prev.map((item) => (item.video_id === videoId ? { ...item, ...updates } : item))
    );
  };

  const handleRemoveItem = (videoId: string) => {
    setResolvedVideos((prev) => prev.filter((item) => item.video_id !== videoId));
  };

  // Bulk auto-clean titles
  const handleAutoCleanTitles = () => {
    setResolvedVideos((prev) =>
      prev.map((item) => {
        let title = item.title || '';
        let artist = item.artist || item.channel || '';

        // Clean YouTube tag patterns
        title = title
          .replace(/\s*\[(?:Official\s*)?(?:Music\s*)?Video\]/gi, '')
          .replace(/\s*\((?:Official\s*)?(?:Music\s*)?Video\)/gi, '')
          .replace(/\s*\[MV\]/gi, '')
          .replace(/\s*\(MV\)/gi, '')
          .replace(/\s*\(Lyrics\)/gi, '')
          .replace(/\s*\[Lyrics\]/gi, '')
          .replace(/\s*\(Audio\)/gi, '')
          .replace(/\s*\[Audio\]/gi, '')
          .replace(/\s*\((?:4K|HD)\s*Remaster\)/gi, '')
          .replace(/\s*\[(?:4K|HD)\s*Remaster\]/gi, '')
          .replace(/\s*-\s*Topic\s*$/i, '')
          .trim();

        // If title has "Artist - Title" format
        if (title.includes(' - ')) {
          const parts = title.split(' - ');
          if (parts.length >= 2) {
            artist = parts[0].trim();
            title = parts.slice(1).join(' - ').trim();
          }
        }

        return { ...item, title, artist };
      })
    );
    setSuccessMsg('Đã tự động chuẩn hóa và dọn sạch tiêu đề các bài hát.');
  };

  // Start download
  const handleStartDownload = () => {
    if (resolvedVideos.length === 0) {
      setErrorMsg('Không có bài hát nào để tải.');
      return;
    }
    setErrorMsg(null);
    submitMutation.mutate({
      videos: resolvedVideos,
      output_dir: outputDir.trim() || '~/Music/Auralytica',
      format: selectedFormat,
      concurrency: concurrency,
    });
  };

  const rawUrlsCount = parseLines(rawText).length;
  const batchData = batchQuery.data;

  const formatDuration = (sec?: number) => {
    if (!sec || sec <= 0) return '';
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  const counts = batchData?.counts || {};
  const completedCount = (counts.completed || 0) + (counts.skipped || 0);
  const failedCount = counts.failed || 0;
  const runningCount = counts.running || 0;
  const queuedCount = counts.queued || 0;
  const totalCount = batchData?.total || 0;

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-6">
      {/* Hero Header */}
      <div className="relative overflow-hidden rounded-2xl glass-panel p-6 border border-white/10 shadow-xl flex items-center justify-between">
        <div className="space-y-1.5 z-10 max-w-2xl">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-semibold">
            <Zap className="w-3.5 h-3.5 fill-current" />
            <span>Tải nhanh trực tiếp từ YouTube</span>
          </div>
          <h1 className="text-xl md:text-2xl font-bold tracking-tight text-white">
            Quick YouTube Downloader
          </h1>
          <p className="text-xs text-zinc-400 leading-relaxed">
            Dán một hoặc nhiều liên kết YouTube (video đơn, Shorts, Playlist) để tải nhạc chất lượng cao trực tiếp về máy. Tự do chỉnh sửa tiêu đề và nghệ sĩ ngay trước khi tải.
          </p>
        </div>
        <div className="hidden md:block shrink-0 opacity-15 pr-4 pointer-events-none">
          <Link2 className="w-28 h-28 text-amber-400" />
        </div>
      </div>

      {/* Notifications */}
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
        <div className="p-4 rounded-xl bg-spotify-500/10 border border-spotify-500/20 text-spotify-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-spotify-400 shrink-0" />
            <span>{successMsg}</span>
          </div>
          <button
            type="button"
            onClick={() => setSuccessMsg(null)}
            className="p-1 hover:bg-spotify-500/20 rounded-md transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* 1. URL Input Card */}
      <div className="glass-panel p-6 rounded-2xl border border-white/10 space-y-4 shadow-xl">
        <div className="flex items-center justify-between gap-4">
          <label className="text-xs font-semibold uppercase tracking-wider text-zinc-300 flex items-center gap-2">
            <Link2 className="w-4 h-4 text-amber-400" />
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
              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-white/10 flex items-center gap-1.5 transition-colors cursor-pointer"
              title="Dán nhanh nội dung từ clipboard"
            >
              <ClipboardPaste className="w-3.5 h-3.5 text-amber-400" />
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
                className="px-2.5 py-1.5 text-xs font-medium rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors cursor-pointer"
                title="Xóa trắng nội dung"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>

        <textarea
          id="direct-urls-input"
          rows={4}
          value={rawText}
          onChange={(e) => setRawText(e.target.value)}
          placeholder="Dán các link YouTube vào đây (mỗi dòng một link hoặc cách nhau bằng khoảng trắng)&#10;Ví dụ:&#10;https://www.youtube.com/watch?v=dQw4w9WgXcQ&#10;https://youtu.be/dQw4w9WgXcQ&#10;https://www.youtube.com/playlist?list=PL1234567890abcdef"
          className="w-full px-4 py-3 text-xs font-mono rounded-xl bg-zinc-950/80 border border-white/10 text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-amber-500 focus:border-amber-500 transition-all resize-y"
        />

        <div className="flex items-center justify-between pt-1 flex-wrap gap-2">
          <p className="text-[11px] text-zinc-500">
            Hỗ trợ URL video đơn, Shorts, Playlist và link rút gọn. Tự động loại bỏ mã theo dõi (&si=, &t=).
          </p>
          <button
            id="analyze-urls-btn"
            type="button"
            disabled={rawUrlsCount === 0 || resolveMutation.isPending}
            onClick={handleAnalyzeClick}
            className="px-5 py-2 text-xs font-semibold rounded-lg bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-zinc-950 flex items-center gap-1.5 transition-all shadow-md cursor-pointer"
          >
            {resolveMutation.isPending ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Đang phân tích URL...</span>
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

      {/* 2. Resolved Items & Inline Metadata Editor */}
      {resolvedVideos.length > 0 && (
        <div className="glass-panel p-6 rounded-2xl border border-white/10 space-y-4 shadow-xl">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/5 pb-4">
            <div>
              <div className="flex items-center gap-2">
                <Music className="w-4 h-4 text-spotify-400" />
                <h2 className="text-sm font-semibold text-zinc-100">
                  Danh sách bài hát tìm thấy ({resolvedVideos.length})
                </h2>
              </div>
              <p className="text-xs text-zinc-400 mt-1">
                Trực tiếp chỉnh sửa <strong>Tiêu đề</strong> và <strong>Nghệ sĩ</strong> bên dưới. Dữ liệu này sẽ được dùng để đặt tên file và nhúng thẻ ID3 tag chuẩn xác.
              </p>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <button
                type="button"
                onClick={handleAutoCleanTitles}
                className="px-3 py-1.5 text-xs font-medium rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-white/10 flex items-center gap-1.5 transition-all cursor-pointer"
                title="Tự động bóc tách 'Nghệ sĩ - Bài hát' và xóa bỏ các tag thừa như [Official Video], (Audio), [MV]"
              >
                <Wand2 className="w-3.5 h-3.5 text-spotify-400" />
                <span>Dọn sạch tiêu đề tự động</span>
              </button>
              <button
                type="button"
                onClick={() => setResolvedVideos([])}
                className="px-2.5 py-1.5 text-xs font-medium rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors cursor-pointer"
                title="Xóa tất cả bài đã phân tích"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Invalid URLs Warning */}
          {invalidUrls.length > 0 && (
            <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-300 space-y-1">
              <p className="font-semibold flex items-center gap-1.5">
                <AlertCircle className="w-3.5 h-3.5" />
                <span>Không thể nhận diện {invalidUrls.length} liên kết sau:</span>
              </p>
              <ul className="list-disc list-inside text-[11px] text-amber-200/80 font-mono">
                {invalidUrls.map((u, i) => (
                  <li key={i} className="truncate">{u}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Interactive Editable List */}
          <div className="divide-y divide-white/5 space-y-3">
            {resolvedVideos.map((video, idx) => {
              const ext = selectedFormat === 'mp3' ? 'mp3' : 'm4a';
              const plannedFilename = `${video.artist || 'Unknown'} - ${video.title || 'Untitled'}.${ext}`;

              return (
                <div key={video.video_id} className="pt-3 first:pt-0 flex flex-col md:flex-row items-start md:items-center gap-4">
                  {/* Thumbnail & Index */}
                  <div className="flex items-center gap-3 shrink-0">
                    <span className="text-xs font-mono text-zinc-500 w-5 text-right">
                      {idx + 1}
                    </span>
                    <div className="relative w-20 h-14 rounded-lg overflow-hidden bg-zinc-900 border border-white/10 shrink-0">
                      <img
                        src={video.thumbnail_url || `https://i.ytimg.com/vi/${video.video_id}/hqdefault.jpg`}
                        alt={video.title || video.video_id}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          (e.target as HTMLElement).style.display = 'none';
                        }}
                      />
                      {video.duration ? (
                        <div className="absolute bottom-1 right-1 px-1 py-0.5 rounded bg-black/80 text-[9px] font-mono text-white">
                          {formatDuration(video.duration)}
                        </div>
                      ) : null}
                    </div>
                  </div>

                  {/* Editable Inputs: Title and Artist */}
                  <div className="flex-1 w-full grid grid-cols-1 sm:grid-cols-2 gap-2 min-w-0">
                    <div>
                      <label className="block text-[10px] uppercase font-semibold text-zinc-400 mb-1">
                        Tiêu đề bài hát (Title)
                      </label>
                      <input
                        type="text"
                        value={video.title || ''}
                        onChange={(e) => handleUpdateItem(video.video_id, { title: e.target.value })}
                        placeholder="Tiêu đề bài hát"
                        className="w-full px-3 py-1.5 text-xs rounded-lg bg-zinc-950/80 border border-white/10 text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-spotify-500 focus:border-spotify-500 transition-all"
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] uppercase font-semibold text-zinc-400 mb-1">
                        Nghệ sĩ / Ca sĩ (Artist)
                      </label>
                      <input
                        type="text"
                        value={video.artist || ''}
                        onChange={(e) => handleUpdateItem(video.video_id, { artist: e.target.value })}
                        placeholder="Nghệ sĩ"
                        className="w-full px-3 py-1.5 text-xs rounded-lg bg-zinc-950/80 border border-white/10 text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-spotify-500 focus:border-spotify-500 transition-all"
                      />
                    </div>

                    {/* Planned file name badge */}
                    <div className="sm:col-span-2 text-[11px] text-zinc-400 font-mono truncate flex items-center gap-1.5">
                      <span className="text-zinc-500">Tên file xuất:</span>
                      <span className="text-spotify-400/90 truncate">{plannedFilename}</span>
                    </div>
                  </div>

                  {/* Actions: YouTube link & Delete */}
                  <div className="flex items-center gap-2 shrink-0 self-end md:self-center">
                    <a
                      href={video.url || `https://www.youtube.com/watch?v=${video.video_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-2 rounded-lg bg-zinc-800/80 hover:bg-zinc-700 text-zinc-400 hover:text-zinc-200 transition-colors"
                      title="Mở video trên YouTube"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                    <button
                      type="button"
                      onClick={() => handleRemoveItem(video.video_id)}
                      className="p-2 rounded-lg bg-zinc-800/80 hover:bg-rose-500/20 text-zinc-400 hover:text-rose-400 transition-colors cursor-pointer"
                      title="Xóa bài này khỏi danh sách tải"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 3. Output Pipeline Settings (Reused UI from DownloadView) */}
      <div className="glass-panel p-6 rounded-2xl border border-white/10 space-y-5 shadow-xl">
        <div className="flex items-center justify-between border-b border-white/5 pb-3">
          <div className="flex items-center gap-2">
            <Sliders className="w-4 h-4 text-spotify-400" />
            <h2 className="text-sm font-semibold text-zinc-100">
              Cài đặt tải & Định dạng âm thanh
            </h2>
          </div>
          <span className="text-[11px] font-mono text-zinc-400">
            {resolvedVideos.length} bài đã chọn
          </span>
        </div>

        {/* Directory Input */}
        <div>
          <label className="block text-xs font-medium text-zinc-300 mb-1.5 flex items-center gap-1.5">
            <Folder className="w-3.5 h-3.5 text-zinc-400" />
            <span>Thư mục lưu trên máy</span>
          </label>
          <input
            type="text"
            value={outputDir}
            onChange={(e) => setOutputDir(e.target.value)}
            placeholder="~/Music/Auralytica"
            className="w-full px-3.5 py-2 text-xs rounded-lg glass-input text-zinc-200 font-mono focus:outline-none focus:ring-1 focus:ring-spotify-500"
          />
        </div>

        {/* Audio Format Selection Cards (ALAC, MP3, AAC) */}
        <div className="space-y-2.5">
          <div className="text-xs font-semibold uppercase tracking-wider text-zinc-300">
            Định dạng âm thanh xuất xưởng
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {[
              {
                id: 'm4a_alac',
                name: 'Lossless ALAC (M4A)',
                badge: 'Chuẩn Apple Music',
                desc: 'Lossless bit-perfect từ Opus nguồn, tương thích gốc Apple Music / iTunes.',
              },
              {
                id: 'mp3',
                name: 'MP3 (320 kbps)',
                badge: 'Phổ thông',
                desc: 'Tương thích mọi dòng máy nghe nhạc di động, dàn loa ô tô và thiết bị âm thanh.',
              },
              {
                id: 'm4a_aac',
                name: 'AAC (256 kbps - M4A)',
                badge: 'Tiết kiệm',
                desc: 'Chất lượng cao tương đương 320k nhưng dung lượng file nhẹ hơn ~25%.',
              },
            ].map((fmt) => {
              const isSelected = selectedFormat === fmt.id;
              return (
                <div
                  key={fmt.id}
                  onClick={() => setSelectedFormat(fmt.id as AudioFormat)}
                  className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-spotify-500/15 text-white border-spotify-400/50 shadow-[0_0_15px_rgba(16,185,129,0.15)] ring-1 ring-spotify-400/30'
                      : 'bg-zinc-950/40 text-zinc-300 border-white/5 hover:border-white/20 hover:bg-zinc-900/40'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-xs text-zinc-100">{fmt.name}</span>
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded font-medium ${
                        isSelected
                          ? 'bg-spotify-500/25 text-spotify-200 border border-spotify-400/30'
                          : 'bg-white/5 text-zinc-400 border border-white/5'
                      }`}
                    >
                      {fmt.badge}
                    </span>
                  </div>
                  <p className={`text-xs leading-relaxed ${isSelected ? 'text-zinc-300' : 'text-zinc-500'}`}>
                    {fmt.desc}
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Concurrency / Multi-threaded Settings Slider */}
        <div className="pt-2 border-t border-white/5 space-y-2">
          <div className="flex items-center justify-between">
            <div className="text-xs font-semibold uppercase tracking-wider text-zinc-300">
              Tốc độ tải song song (Concurrency)
            </div>
            <span className="text-xs font-mono font-bold text-spotify-400">
              {concurrency} luồng đồng thời
            </span>
          </div>
          <div className="flex items-center gap-4">
            <input
              type="range"
              min={1}
              max={8}
              step={1}
              value={concurrency}
              onChange={(e) => setConcurrency(parseInt(e.target.value, 10))}
              className="flex-1 accent-spotify-500 h-1.5 bg-zinc-800 rounded-lg cursor-pointer"
            />
            <div className="flex items-center gap-1">
              {[1, 2, 3, 4, 6, 8].map((val) => (
                <button
                  key={val}
                  type="button"
                  onClick={() => setConcurrency(val)}
                  className={`px-2 py-0.5 text-[10px] font-mono rounded transition-colors ${
                    concurrency === val
                      ? 'bg-spotify-500 text-zinc-950 font-bold'
                      : 'bg-zinc-800/80 text-zinc-400 hover:text-white'
                  }`}
                >
                  {val}x
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Start Download Button */}
        <div className="pt-3 border-t border-white/5 flex items-center justify-end">
          <button
            id="start-direct-download-btn"
            type="button"
            disabled={resolvedVideos.length === 0 || submitMutation.isPending}
            onClick={handleStartDownload}
            className="w-full md:w-auto px-6 py-2.5 text-xs font-semibold rounded-xl bg-spotify-500 hover:bg-spotify-400 disabled:opacity-40 text-zinc-950 font-medium flex items-center justify-center gap-2 transition-all shadow-lg hover:shadow-spotify-500/20 cursor-pointer"
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

      {/* 4. Active Batch Progress Monitor (Reused UI from DownloadView) */}
      {batchData && (
        <div className="glass-panel p-6 rounded-2xl border border-white/10 space-y-4 shadow-xl">
          {/* Batch Header & Controls */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/5 pb-4">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-semibold text-zinc-100">
                  Tiến trình tải lượt #{batchData.batch_id}
                </h3>
                <span
                  className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${
                    batchData.status === 'completed'
                      ? 'bg-spotify-500/20 text-spotify-300 border border-spotify-500/30'
                      : batchData.status === 'running'
                      ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                      : batchData.status === 'paused'
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                      : 'bg-zinc-800 text-zinc-300'
                  }`}
                >
                  {batchData.status === 'completed'
                    ? 'Hoàn tất'
                    : batchData.status === 'running'
                    ? 'Đang tải...'
                    : batchData.status === 'paused'
                    ? 'Đã dừng'
                    : batchData.status}
                </span>
              </div>
              <p className="text-xs text-zinc-400 mt-1">
                Đã hoàn thành {completedCount} / {totalCount} bài
                {failedCount > 0 && <span className="text-rose-400 ml-2">· {failedCount} bài lỗi</span>}
              </p>
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-2 flex-wrap">
              {batchData.status === 'running' && (
                <button
                  type="button"
                  onClick={() => pauseMutation.mutate(batchData.batch_id)}
                  disabled={pauseMutation.isPending}
                  className="px-3 py-1.5 text-xs font-medium rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-white/10 flex items-center gap-1.5 transition-all cursor-pointer"
                >
                  <Pause className="w-3.5 h-3.5" />
                  <span>Tạm dừng</span>
                </button>
              )}

              {batchData.status === 'paused' && (
                <button
                  type="button"
                  onClick={() => resumeMutation.mutate(batchData.batch_id)}
                  disabled={resumeMutation.isPending}
                  className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-spotify-500 hover:bg-spotify-400 text-zinc-950 flex items-center gap-1.5 transition-all shadow-md cursor-pointer"
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Tiếp tục tải</span>
                </button>
              )}

              {failedCount > 0 && (
                <>
                  <button
                    type="button"
                    onClick={() => retryFailedMutation.mutate(batchData.batch_id)}
                    disabled={retryFailedMutation.isPending}
                    className="px-3 py-1.5 text-xs font-medium rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/30 flex items-center gap-1.5 transition-all cursor-pointer"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>Thử lại ({failedCount})</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => skipFailedMutation.mutate(batchData.batch_id)}
                    disabled={skipFailedMutation.isPending}
                    className="px-3 py-1.5 text-xs font-medium rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border border-white/10 flex items-center gap-1.5 transition-all cursor-pointer"
                  >
                    <SkipForward className="w-3.5 h-3.5" />
                    <span>Bỏ qua lỗi</span>
                  </button>
                </>
              )}

              {onNavigatePlayer && (
                <button
                  type="button"
                  onClick={onNavigatePlayer}
                  className={`px-4 py-1.5 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-all shadow-md cursor-pointer ${
                    batchData.status === 'completed'
                      ? 'bg-spotify-500 hover:bg-spotify-400 text-zinc-950 font-medium'
                      : 'bg-zinc-800 hover:bg-zinc-700 text-zinc-100 border border-white/10'
                  }`}
                >
                  <Headphones className="w-3.5 h-3.5" />
                  <span>{batchData.status === 'completed' ? 'Mở trong Player nghe ngay' : 'Mở Music Player'}</span>
                </button>
              )}
            </div>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-zinc-950 rounded-full h-2.5 overflow-hidden border border-white/5">
            <div
              className={`h-full transition-all duration-300 ${
                batchData.status === 'completed'
                  ? 'bg-spotify-400'
                  : failedCount > 0
                  ? 'bg-gradient-to-r from-spotify-400 to-amber-400'
                  : 'bg-sky-400'
              }`}
              style={{
                width: `${totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0}%`,
              }}
            />
          </div>

          {/* Status Filter Tabs */}
          <div className="flex items-center gap-1 pt-1 overflow-x-auto text-xs border-b border-white/5 pb-2">
            {[
              { id: 'all', label: `Tất cả (${totalCount})` },
              { id: 'failed', label: `Lỗi (${failedCount})`, count: failedCount },
              { id: 'running', label: `Đang tải (${runningCount})`, count: runningCount },
              { id: 'queued', label: `Chờ (${queuedCount})`, count: queuedCount },
              { id: 'completed', label: `Hoàn tất (${completedCount})`, count: completedCount },
            ].map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => {
                  setStatusFilter(tab.id as StatusFilter);
                  setBatchPage(1);
                }}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
                  statusFilter === tab.id
                    ? 'bg-zinc-800 text-white border border-white/10'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Items breakdown list */}
          {batchData.items && batchData.items.length > 0 ? (
            <div className="divide-y divide-white/[0.04] max-h-80 overflow-y-auto text-xs pr-1">
              {batchData.items.map((item: DownloadBatchItem) => {
                const errMeta = item.error_code ? ERROR_CODE_LABELS[item.error_code] : null;

                return (
                  <div key={item.video_id} className="py-2.5 flex items-center justify-between gap-3">
                    <div className="min-w-0 flex-1 space-y-0.5">
                      <p className="text-zinc-200 font-medium truncate">{item.title || item.video_id}</p>
                      <div className="flex items-center gap-2 text-[11px] text-zinc-500 font-mono truncate">
                        <span>ID: {item.video_id}</span>
                        {(item.total_bytes || item.downloaded_bytes) ? (
                          <>
                            <span>·</span>
                            <span>{(((item.total_bytes || item.downloaded_bytes) as number) / (1024 * 1024)).toFixed(1)} MB</span>
                          </>
                        ) : null}
                      </div>
                      {errMeta && (
                        <div className={`mt-1 inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] border ${errMeta.color}`}>
                          <AlertCircle className="w-3 h-3 shrink-0" />
                          <span>{errMeta.label}: {errMeta.desc}</span>
                        </div>
                      )}
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded border uppercase ${
                          item.status === 'completed'
                            ? 'bg-spotify-500/10 text-spotify-400 border-spotify-500/20'
                            : item.status === 'running'
                            ? 'bg-sky-500/10 text-sky-400 border-sky-500/20'
                            : item.status === 'failed'
                            ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                            : 'bg-zinc-800 text-zinc-400 border-white/5'
                        }`}
                      >
                        {item.status}
                      </span>

                      {item.status === 'failed' && (
                        <div className="flex items-center gap-1">
                          <button
                            type="button"
                            onClick={() => retryItemMutation.mutate({ batchId: batchData.batch_id, videoId: item.video_id })}
                            className="p-1 rounded hover:bg-zinc-800 text-zinc-400 hover:text-white"
                            title="Thử lại bài này"
                          >
                            <RotateCcw className="w-3.5 h-3.5" />
                          </button>
                          <button
                            type="button"
                            onClick={() => skipItemMutation.mutate({ batchId: batchData.batch_id, videoId: item.video_id })}
                            className="p-1 rounded hover:bg-zinc-800 text-zinc-400 hover:text-white"
                            title="Bỏ qua bài này"
                          >
                            <SkipForward className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-xs text-zinc-500 py-4 text-center">Không có bài nào trong bộ lọc này.</p>
          )}
        </div>
      )}
    </div>
  );
};
