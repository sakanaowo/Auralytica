import React, { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../api/client';
import { ConverterScanResponse, ConverterStatus } from '../../api/types';

interface ConvertViewProps {
  batchLocked: boolean;
  onRefreshWorkflow: () => void;
}

export const ConvertView: React.FC<ConvertViewProps> = ({ batchLocked }) => {
  const queryClient = useQueryClient();

  const [inputDir, setInputDir] = useState<string>(() => {
    try {
      return localStorage.getItem('auralytica-output') || '~/Music/Auralytica';
    } catch {
      return '~/Music/Auralytica';
    }
  });

  const [outputSubdir, setOutputSubdir] = useState<string>('Apple Music');
  const [targetFormat, setTargetFormat] = useState<'m4a_alac' | 'm4a_aac' | 'mp3'>('m4a_alac');
  const [stripVideoId, setStripVideoId] = useState(true);
  const [cleanYoutubeTags, setCleanYoutubeTags] = useState(true);
  const [removeSource, setRemoveSource] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterMode, setFilterMode] = useState<'all' | 'incompatible' | 'compatible'>('all');

  // Local overrides for cleaned names (source_path -> custom_stem)
  const [customNames, setCustomNames] = useState<Record<string, string>>({});
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Scan directory query
  const scanQuery = useQuery({
    queryKey: ['converter', 'scan', inputDir],
    queryFn: () => api.scanConverter(inputDir),
    enabled: inputDir.trim().length > 0,
  });

  // Converter status query (poll when running)
  const statusQuery = useQuery({
    queryKey: ['converter', 'status'],
    queryFn: () => api.getConverterStatus(),
    refetchInterval: (query) => {
      const state = query.state.data?.state;
      return state === 'running' ? 1000 : false;
    },
  });

  const scanData: ConverterScanResponse | undefined = scanQuery.data;
  const converterStatus: ConverterStatus | undefined = statusQuery.data;
  const isConverting = converterStatus?.state === 'running';

  // Resolved output directory
  const resolvedOutputDir = useMemo(() => {
    const base = inputDir.trim().replace(/\/+$/, '');
    if (!outputSubdir.trim()) return base;
    return `${base}/${outputSubdir.trim()}`;
  }, [inputDir, outputSubdir]);

  // Start conversion mutation
  const startConversionMutation = useMutation({
    mutationFn: () => {
      if (!scanData || scanData.items.length === 0) {
        throw new Error('Không có file nào để chuyển đổi.');
      }
      const itemsToConvert = scanData.items.map((it) => {
        const customStem = customNames[it.source_path];
        return {
          source_path: it.source_path,
          cleaned_stem: customStem !== undefined ? customStem : it.cleaned_stem,
          artist: it.artist,
          title: it.title,
        };
      });

      return api.startConversion({
        directory: inputDir.trim(),
        output_dir: resolvedOutputDir,
        format: targetFormat,
        remove_source: removeSource,
        items: itemsToConvert,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['converter', 'status'] });
    },
    onError: (err: any) => {
      setErrorMsg(err.message);
    },
  });

  // Stop conversion mutation
  const stopConversionMutation = useMutation({
    mutationFn: () => api.stopConversion(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['converter', 'status'] });
    },
  });

  // Rename in-place mutation
  const renameMutation = useMutation({
    mutationFn: () => {
      if (!scanData || scanData.items.length === 0) {
        throw new Error('Không có file nào để đổi tên.');
      }
      const renames = scanData.items.map((it) => {
        const customStem = customNames[it.source_path];
        return {
          source_path: it.source_path,
          new_name: customStem !== undefined ? customStem : it.cleaned_stem,
        };
      });
      return api.renameFiles(renames);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['converter', 'scan'] });
    },
    onError: (err: any) => {
      setErrorMsg(err.message);
    },
  });

  // Filter items
  const filteredItems = useMemo(() => {
    if (!scanData) return [];
    return scanData.items.filter((item) => {
      if (filterMode === 'incompatible' && item.is_apple_compatible) return false;
      if (filterMode === 'compatible' && !item.is_apple_compatible) return false;

      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesFilename = item.filename.toLowerCase().includes(q);
        const matchesCleaned = (customNames[item.source_path] || item.cleaned_stem).toLowerCase().includes(q);
        const matchesArtist = item.artist.toLowerCase().includes(q);
        if (!matchesFilename && !matchesCleaned && !matchesArtist) return false;
      }
      return true;
    });
  }, [scanData, filterMode, searchQuery, customNames]);

  const progressPercent = useMemo(() => {
    if (!converterStatus || converterStatus.total === 0) return 0;
    return Math.min(100, Math.round(((converterStatus.completed + converterStatus.failed) / converterStatus.total) * 100));
  }, [converterStatus]);

  return (
    <div className="max-w-5xl mx-auto py-8 px-4 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold tracking-tight text-zinc-100">
          05 · Apple Music — Xử lý tên & Chuyển đổi định dạng
        </h1>
        <p className="text-xs text-zinc-400 mt-1">
          Loại bỏ mã [video_id] và hậu tố YouTube rác; chuyển đổi toàn bộ audio sang định dạng mà Apple Music / macOS đọc được mượt mà.
        </p>
      </div>

      {/* Control & Configuration Panel */}
      <div className="glass-panel rounded-2xl border border-white/10 p-6 space-y-5 shadow-xl">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Input Directory */}
          <div>
            <label className="block text-xs font-medium text-zinc-300 mb-1.5">
              Thư mục nguồn (chứa file audio tải về)
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={inputDir}
                onChange={(e) => setInputDir(e.target.value)}
                disabled={isConverting}
                className="w-full px-3.5 py-2 text-xs rounded-lg glass-input text-zinc-200 font-mono disabled:opacity-50"
              />
              <button
                type="button"
                disabled={scanQuery.isFetching || isConverting}
                onClick={() => scanQuery.refetch()}
                className="px-3 py-2 text-xs rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-white/10 shrink-0 transition-colors"
              >
                Quét lại
              </button>
            </div>
          </div>

          {/* Output Subdir */}
          <div>
            <label className="block text-xs font-medium text-zinc-300 mb-1.5">
              Thư mục con đích
            </label>
            <input
              type="text"
              value={outputSubdir}
              onChange={(e) => setOutputSubdir(e.target.value)}
              disabled={isConverting}
              placeholder="Apple Music"
              className="w-full px-3.5 py-2 text-xs rounded-lg glass-input text-zinc-200 font-mono disabled:opacity-50"
            />
            <span className="text-[11px] text-zinc-400 font-mono mt-1 block truncate" title={resolvedOutputDir}>
              Đích: {resolvedOutputDir}
            </span>
          </div>
        </div>

        {/* Name Sanitizer Options */}
        <div className="p-4 rounded-xl bg-zinc-950/40 border border-white/5 space-y-3">
          <div className="text-xs font-semibold text-zinc-200 uppercase tracking-wide">
            Quy tắc làm sạch tên file
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs text-zinc-300">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={stripVideoId}
                onChange={(e) => setStripVideoId(e.target.checked)}
                className="rounded border-zinc-700 bg-zinc-900 text-zinc-100 focus:ring-0"
              />
              <span>Loại bỏ mã [video_id] thừa ở đuôi</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={cleanYoutubeTags}
                onChange={(e) => setCleanYoutubeTags(e.target.checked)}
                className="rounded border-zinc-700 bg-zinc-900 text-zinc-100 focus:ring-0"
              />
              <span>Lọc hậu tố YouTube (Official, Lyric...)</span>
            </label>

            <label className="flex items-center gap-2 cursor-pointer text-zinc-400 hover:text-zinc-200">
              <input
                type="checkbox"
                checked={removeSource}
                onChange={(e) => setRemoveSource(e.target.checked)}
                className="rounded border-zinc-700 bg-zinc-900 text-zinc-100 focus:ring-0"
              />
              <span>Xóa file gốc sau khi convert</span>
            </label>
          </div>
        </div>

        {/* Target Format Selection */}
        <div className="space-y-2">
          <label className="block text-xs font-semibold text-zinc-200 uppercase tracking-wide">
            Định dạng xuất cho Apple Music
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {/* ALAC */}
            <div
              onClick={() => setTargetFormat('m4a_alac')}
              className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                targetFormat === 'm4a_alac'
                  ? 'bg-zinc-800/90 border-white/20 shadow-md ring-1 ring-white/10'
                  : 'bg-zinc-900/30 border-white/5 hover:bg-zinc-800/40 text-zinc-400'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-zinc-100">M4A · Apple Lossless (ALAC)</span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Khuyên dùng
                </span>
              </div>
              <p className="text-[11px] text-zinc-400 mt-1">
                Bảo toàn 100% chất lượng từ Opus nguồn, không suy hao âm thanh, Apple Music đọc gốc.
              </p>
            </div>

            {/* AAC */}
            <div
              onClick={() => setTargetFormat('m4a_aac')}
              className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                targetFormat === 'm4a_aac'
                  ? 'bg-zinc-800/90 border-white/20 shadow-md ring-1 ring-white/10'
                  : 'bg-zinc-900/30 border-white/5 hover:bg-zinc-800/40 text-zinc-400'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-zinc-100">M4A · AAC (256 kbps)</span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-300 border border-white/5">
                  iTunes Standard
                </span>
              </div>
              <p className="text-[11px] text-zinc-400 mt-1">
                Chuẩn nén iTunes Store, dung lượng nhỏ gọn, tương thích mọi iPhone / iPod / Mac.
              </p>
            </div>

            {/* MP3 */}
            <div
              onClick={() => setTargetFormat('mp3')}
              className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                targetFormat === 'mp3'
                  ? 'bg-zinc-800/90 border-white/20 shadow-md ring-1 ring-white/10'
                  : 'bg-zinc-900/30 border-white/5 hover:bg-zinc-800/40 text-zinc-400'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-zinc-100">MP3 (320 kbps)</span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-white/5">
                  Universal
                </span>
              </div>
              <p className="text-[11px] text-zinc-400 mt-1">
                Tương thích phổ thông trên mọi phần mềm, thiết bị và máy nghe nhạc cổ điển.
              </p>
            </div>
          </div>
        </div>

        {errorMsg && (
          <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800/40 text-rose-300 text-xs flex justify-between items-center">
            <span>{errorMsg}</span>
            <button
              type="button"
              onClick={() => setErrorMsg(null)}
              className="text-rose-400 hover:text-rose-200 text-xs underline ml-2"
            >
              Đóng
            </button>
          </div>
        )}
      </div>

      {/* Overview & Action Bar */}
      {scanData && (
        <div className="glass-panel rounded-2xl border border-white/10 p-5 space-y-4 shadow-xl">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
                <span>Tìm thấy {scanData.total} bài trong thư mục</span>
                <span className="text-zinc-500">·</span>
                <span className="text-rose-400 text-xs font-mono">
                  {scanData.incompatible_count} bài WebM cần chuyển đổi
                </span>
                <span className="text-zinc-500">·</span>
                <span className="text-amber-400 text-xs font-mono">
                  {scanData.has_video_id_count} bài có mã [ID] thừa
                </span>
              </div>
              <p className="text-xs text-zinc-400 mt-1">
                Sau khi chuyển đổi, bạn chỉ cần mở Finder và kéo thư mục kết quả vào Apple Music.
              </p>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <button
                type="button"
                disabled={renameMutation.isPending || isConverting || batchLocked || scanData.total === 0}
                onClick={() => renameMutation.mutate()}
                className="px-3.5 py-2 text-xs font-medium rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-white/10 transition-colors disabled:opacity-40"
              >
                {renameMutation.isPending ? 'Đang đổi tên...' : 'Chỉ đổi tên file gốc'}
              </button>

              <button
                type="button"
                disabled={startConversionMutation.isPending || isConverting || batchLocked || scanData.total === 0}
                onClick={() => startConversionMutation.mutate()}
                className="px-5 py-2 text-xs font-semibold rounded-lg bg-zinc-100 text-zinc-900 hover:bg-white border border-white transition-all shadow-md disabled:opacity-40"
              >
                {startConversionMutation.isPending ? 'Đang khởi chạy...' : `Chuyển đổi sang Apple Music (${scanData.total} bài)`}
              </button>
            </div>
          </div>

          {/* Real-time Conversion Progress Bar (shown when converting) */}
          {isConverting && converterStatus && (
            <div className="p-4 rounded-xl border border-white/10 bg-zinc-950/60 space-y-3 animate-fade-in">
              <div className="flex items-center justify-between text-xs">
                <div className="font-semibold text-zinc-200 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                  <span>Đang chuyển đổi sang {converterStatus.format.toUpperCase()}</span>
                  <span className="text-zinc-500 font-mono">
                    ({converterStatus.completed + converterStatus.failed} / {converterStatus.total})
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => stopConversionMutation.mutate()}
                  className="px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs border border-white/10"
                >
                  Tạm dừng
                </button>
              </div>

              <div className="w-full h-2 bg-zinc-900 rounded-full overflow-hidden border border-white/5">
                <div
                  className="h-full bg-zinc-100 transition-all duration-200"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>

              <div className="text-[11px] font-mono text-zinc-400 truncate">
                Đang xử lý: {converterStatus.current_file || 'Chuẩn bị file...'}
              </div>
            </div>
          )}

          {/* Completion Notice */}
          {converterStatus?.state === 'completed' && (
            <div className="p-4 rounded-xl border border-emerald-500/30 bg-emerald-950/20 flex items-center justify-between gap-3 text-xs">
              <div>
                <span className="font-semibold text-emerald-300">
                  Hoàn tất chuyển đổi {converterStatus.completed} bài!
                </span>
                <p className="text-[11px] text-zinc-400 mt-0.5 font-mono">
                  File đã được xuất vào: {converterStatus.output_dir}
                </p>
              </div>
              <span className="px-2.5 py-1 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 text-xs font-mono">
                Sẵn sàng cho Apple Music
              </span>
            </div>
          )}
        </div>
      )}

      {/* Comparison & Editable Table */}
      {scanData && (
        <div className="glass-panel rounded-2xl border border-white/10 p-6 space-y-4 shadow-xl">
          {/* Table Controls */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
            {/* Filter Tabs */}
            <div className="flex items-center gap-1 font-mono">
              <button
                type="button"
                onClick={() => setFilterMode('all')}
                className={`px-3 py-1.5 rounded-lg transition-colors ${
                  filterMode === 'all'
                    ? 'bg-zinc-800 text-zinc-100 font-semibold border border-white/10'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.02]'
                }`}
              >
                Tất cả ({scanData.total})
              </button>
              <button
                type="button"
                onClick={() => setFilterMode('incompatible')}
                className={`px-3 py-1.5 rounded-lg transition-colors ${
                  filterMode === 'incompatible'
                    ? 'bg-rose-500/15 text-rose-300 font-semibold border border-rose-500/30'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.02]'
                }`}
              >
                Cần chuyển đổi ({scanData.incompatible_count})
              </button>
              <button
                type="button"
                onClick={() => setFilterMode('compatible')}
                className={`px-3 py-1.5 rounded-lg transition-colors ${
                  filterMode === 'compatible'
                    ? 'bg-zinc-800 text-zinc-100 font-semibold border border-white/10'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.02]'
                }`}
              >
                Đã tương thích ({scanData.compatible_count})
              </button>
            </div>

            {/* Search Input */}
            <div className="w-full sm:w-64">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Tìm kiếm bài hoặc nghệ sĩ..."
                className="w-full px-3 py-1.5 text-xs rounded-lg glass-input text-zinc-200"
              />
            </div>
          </div>

          {/* Table */}
          <div className="overflow-hidden rounded-xl border border-white/5 bg-zinc-950/40">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-white/10 bg-zinc-900/60 text-zinc-400 font-mono text-[11px]">
                  <th className="p-3 w-1/3">File hiện tại (Gốc)</th>
                  <th className="p-3 w-1/3">Tên sau khi xử lý (Đề xuất)</th>
                  <th className="p-3 w-40">Nghệ sĩ</th>
                  <th className="p-3 w-28 text-right">Định dạng</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="p-8 text-center text-zinc-500 font-mono">
                      Không tìm thấy file nào phù hợp với bộ lọc.
                    </td>
                  </tr>
                ) : (
                  filteredItems.map((item) => {
                    const currentCleaned = customNames[item.source_path] !== undefined
                      ? customNames[item.source_path]
                      : item.cleaned_stem;

                    return (
                      <tr
                        key={item.source_path}
                        className="border-b border-white/5 hover:bg-white/[0.02] transition-colors"
                      >
                        {/* Original File */}
                        <td className="p-3">
                          <div className="text-zinc-300 font-medium truncate max-w-xs" title={item.filename}>
                            {item.filename}
                          </div>
                          <div className="text-[11px] font-mono text-zinc-500 mt-0.5">
                            {(item.size / (1024 * 1024)).toFixed(1)} MB · {item.suffix.toUpperCase().replace('.', '')}
                          </div>
                        </td>

                        {/* Suggested Clean Name (Editable) */}
                        <td className="p-3">
                          <input
                            type="text"
                            value={currentCleaned}
                            onChange={(e) => {
                              setCustomNames((prev) => ({
                                ...prev,
                                [item.source_path]: e.target.value,
                              }));
                            }}
                            className="w-full px-2.5 py-1 text-xs rounded bg-zinc-900/80 text-zinc-100 border border-white/10 focus:border-white/30 focus:outline-none font-medium"
                          />
                        </td>

                        {/* Artist */}
                        <td className="p-3 text-zinc-400 text-[11px] truncate max-w-[150px]">
                          {item.artist || '—'}
                        </td>

                        {/* Compatibility Badge */}
                        <td className="p-3 text-right font-mono text-[11px]">
                          {item.is_apple_compatible ? (
                            <span className="inline-block px-2 py-0.5 rounded text-emerald-400 bg-emerald-500/10 border border-emerald-500/20">
                              Apple OK
                            </span>
                          ) : (
                            <span className="inline-block px-2 py-0.5 rounded text-rose-400 bg-rose-500/10 border border-rose-500/20">
                              Cần chuyển
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
