import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../api/client';
import { DedupGroup, DedupMember } from '../../api/types';

interface DedupViewProps {
  onNavigateDownload: () => void;
}

export const DedupView: React.FC<DedupViewProps> = ({ onNavigateDownload }) => {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [aliasIds, setAliasIds] = useState('');
  const [aliasArtist, setAliasArtist] = useState('');
  const [aliasMsg, setAliasMsg] = useState<string | null>(null);

  // Fetch latest run
  const latestQuery = useQuery({
    queryKey: ['dedup', 'latest'],
    queryFn: () => api.getDedupLatest(),
  });

  const runId = latestQuery.data?.run?.run_id;
  const currentRevision = latestQuery.data?.selection_revision ?? 0;

  // Fetch groups
  const groupsQuery = useQuery({
    queryKey: ['dedup', 'groups', runId, page],
    queryFn: () => api.getDedupGroups(runId!, page, 20),
    enabled: !!runId,
  });

  // Start dedup run mutation
  const scanMutation = useMutation({
    mutationFn: () => api.startDedupRun(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dedup'] });
    },
  });

  // Update selection mutation
  const selectionMutation = useMutation({
    mutationFn: (vars: { videoIds: string[]; keep: boolean }) =>
      api.updateDedupSelections(vars.videoIds, vars.keep, currentRevision),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dedup'] });
    },
  });

  // Reject group mutation
  const rejectMutation = useMutation({
    mutationFn: (vars: { groupId: string; rejected: boolean }) =>
      api.setGroupRejection(vars.groupId, vars.rejected, currentRevision),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dedup'] });
    },
  });

  // Confirm alias mutation
  const aliasMutation = useMutation({
    mutationFn: (vars: { videoIds: string[]; artist?: string }) =>
      api.confirmVideoAliases(vars.videoIds, vars.artist),
    onSuccess: () => {
      setAliasIds('');
      setAliasArtist('');
      setAliasMsg('Đã xác nhận alias và quét lại thành công.');
      queryClient.invalidateQueries({ queryKey: ['dedup'] });
    },
    onError: (err: any) => {
      setAliasMsg(err.message);
    },
  });

  const handleManualAlias = (e: React.FormEvent) => {
    e.preventDefault();
    const ids = aliasIds
      .split(',')
      .map((s) => s.trim())
      .filter((s) => /^[A-Za-z0-9_-]{11}$/.test(s));

    if (ids.length < 2) {
      setAliasMsg('Vui lòng nhập ít nhất 2 video ID hợp lệ.');
      return;
    }
    aliasMutation.mutate({ videoIds: ids, artist: aliasArtist.trim() || undefined });
  };

  const groups = groupsQuery.data?.items || [];
  const totalGroups = groupsQuery.data?.total || 0;
  const maxPage = Math.max(1, Math.ceil(totalGroups / 20));

  return (
    <div className="max-w-7xl w-full mx-auto py-6 px-4 lg:px-6 space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-2xl bg-zinc-950/40 border border-white/5 backdrop-blur-md">
        <div>
          <h1 className="text-lg font-bold tracking-tight text-zinc-100 flex items-center gap-2.5">
            <span>03 · Deduplicate — Chọn bản của cùng bài</span>
            {totalGroups > 0 && (
              <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-300 border border-white/10">
                {totalGroups} nhóm
              </span>
            )}
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            So sánh trực diện các bản thu của cùng bài hát. Nhấp vào thẻ bất kỳ để giữ hoặc loại bỏ bản tải.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            type="button"
            disabled={scanMutation.isPending}
            onClick={() => scanMutation.mutate()}
            className="px-3.5 py-1.5 text-xs font-medium rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-white/10 transition-colors shadow-sm"
          >
            {scanMutation.isPending ? 'Đang quét...' : 'Quét lại gợi ý'}
          </button>

          <button
            type="button"
            onClick={onNavigateDownload}
            className="px-4 py-1.5 text-xs font-medium rounded-lg bg-sky-500/15 text-sky-200 border border-sky-400/30 hover:bg-sky-500/25 transition-all shadow-sm"
          >
            Tiếp tục sang bước 04 · Download →
          </button>
        </div>
      </div>

      {/* Manual Alias Card */}
      <details className="glass-panel rounded-xl border border-white/5 p-3.5 text-xs group">
        <summary className="font-medium text-zinc-400 hover:text-zinc-200 cursor-pointer select-none flex items-center gap-2">
          <span>Ghép thủ công hai hoặc nhiều video</span>
          <span className="text-zinc-600 font-mono text-xs">(Nâng cao)</span>
        </summary>
        <form onSubmit={handleManualAlias} className="mt-3 space-y-3 pt-3 border-t border-white/5">
          <p className="text-zinc-400 text-xs">
            Dán các video ID cách nhau bằng dấu phẩy để xác nhận alias độc lập với việc loại bản tải.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <input
              type="text"
              placeholder="Video ID (ví dụ: aaaaaaaaaaa, bbbbbbbbbbb)"
              value={aliasIds}
              onChange={(e) => setAliasIds(e.target.value)}
              className="px-3 py-1.5 text-xs rounded-lg glass-input text-zinc-200"
            />
            <input
              type="text"
              placeholder="Nghệ sĩ nếu biết (tùy chọn)"
              value={aliasArtist}
              onChange={(e) => setAliasArtist(e.target.value)}
              className="px-3 py-1.5 text-xs rounded-lg glass-input text-zinc-200"
            />
          </div>
          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={aliasMutation.isPending}
              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-white/10"
            >
              {aliasMutation.isPending ? 'Đang xử lý...' : 'Xác nhận alias và quét lại'}
            </button>
            {aliasMsg && <span className="text-xs text-zinc-400">{aliasMsg}</span>}
          </div>
        </form>
      </details>

      {/* Groups List (Responsive Comparison Cards) */}
      <div className="space-y-4">
        {groupsQuery.isLoading ? (
          <div className="py-16 text-center text-xs font-mono text-zinc-500">Đang tải danh sách nhóm trùng...</div>
        ) : groups.length === 0 ? (
          <div className="glass-panel rounded-2xl p-12 text-center text-xs text-zinc-400 space-y-3">
            <p className="text-sm text-zinc-300 font-medium">Không có nhóm nào bị trùng lặp.</p>
            <p className="text-zinc-500">Mọi bản bài hát trong thư viện sẽ được giữ mặc định để tải về.</p>
            <button
              type="button"
              onClick={onNavigateDownload}
              className="mt-3 px-4 py-2 text-xs font-medium rounded-xl bg-sky-500 hover:bg-sky-400 text-white shadow-md transition-all"
            >
              Chuyển tiếp sang bước 04 · Download →
            </button>
          </div>
        ) : (
          groups.map((group: DedupGroup) => (
            <div
              key={group.group_id}
              className={`glass-panel rounded-2xl border p-4 sm:p-5 space-y-3.5 transition-all ${
                group.rejected ? 'opacity-50 border-white/5 bg-zinc-950/20' : 'border-white/10 shadow-lg'
              }`}
            >
              {/* Group Header */}
              <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-white/5">
                <div>
                  <h3 className="text-base font-semibold text-zinc-100">{group.title_key}</h3>
                  <div className="text-xs text-zinc-400 mt-0.5 flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded-full bg-zinc-800/80 border border-white/5 font-mono text-zinc-300">
                      {group.member_count} bản thu
                    </span>
                    <span className="text-zinc-600">·</span>
                    <span>
                      {group.evidence_type === 'confirmed_alias'
                        ? 'Alias đã xác nhận'
                        : group.artist_conflict
                          ? 'Tên giống nhau · Khác nghệ sĩ/kênh'
                          : 'Tên chuẩn hóa trùng'}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() =>
                      selectionMutation.mutate({
                        videoIds: group.members.map((m) => m.video_id),
                        keep: true,
                      })
                    }
                    className="px-3 py-1 text-xs font-medium rounded-lg bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white border border-white/10 transition-colors"
                  >
                    Giữ tất cả
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      rejectMutation.mutate({
                        groupId: group.group_id,
                        rejected: !group.rejected,
                      })
                    }
                    className="px-3 py-1 text-xs font-medium rounded-lg bg-zinc-900 hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 border border-white/5 transition-colors"
                  >
                    {group.rejected ? 'Hoàn tác' : 'Không ghép nhóm này'}
                  </button>
                </div>
              </div>

              {/* Members Grid (Responsive Multi-Column Comparison Cards) */}
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                {group.members.map((member: DedupMember) => (
                  <div
                    key={member.video_id}
                    onClick={() =>
                      selectionMutation.mutate({
                        videoIds: [member.video_id],
                        keep: !member.keep,
                      })
                    }
                    className={`group relative flex items-start gap-3 p-3 rounded-xl border cursor-pointer select-none transition-all duration-150 ${
                      member.keep
                        ? 'bg-sky-500/5 border-sky-400/30 hover:border-sky-400/50 shadow-sm'
                        : 'bg-zinc-950/40 border-white/5 opacity-55 hover:opacity-85 hover:border-white/20'
                    }`}
                  >
                    {/* Square Squircle Album Cover (56x56) */}
                    <div className="relative w-14 h-14 shrink-0 rounded-xl bg-zinc-900 overflow-hidden border border-white/5 shadow-sm">
                      <img
                        src={`https://i.ytimg.com/vi/${member.video_id}/mqdefault.jpg`}
                        alt=""
                        className="w-full h-full object-cover scale-105"
                        loading="lazy"
                      />
                      {member.keep && (
                        <div className="absolute inset-0 bg-sky-500/15 backdrop-blur-[1px] flex items-center justify-center">
                          <span className="w-5 h-5 rounded-full bg-sky-500 text-white text-xs font-bold flex items-center justify-center shadow-sm">
                            ✓
                          </span>
                        </div>
                      )}
                    </div>

                    {/* Track Details */}
                    <div className="flex-1 min-w-0 pr-1">
                      <a
                        href={`https://www.youtube.com/watch?v=${encodeURIComponent(member.video_id)}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="font-medium text-xs text-zinc-100 hover:text-white line-clamp-2 leading-snug transition-colors"
                        title={member.raw_title || member.video_id}
                      >
                        {member.raw_title || member.video_id}
                      </a>

                      <div className="text-xs text-zinc-400 truncate mt-1 flex items-center gap-1.5">
                        <span className="truncate max-w-[140px]">{member.channel || 'Chưa rõ kênh'}</span>
                        <span className="text-zinc-600">·</span>
                        <span className="font-mono text-zinc-500">{member.version_marker || 'Chuẩn'}</span>
                      </div>
                    </div>

                    {/* Keep / Skip Status Badge */}
                    <div className="shrink-0 pt-0.5">
                      <span
                        className={`text-xs font-medium px-2 py-0.5 rounded-md transition-colors ${
                          member.keep
                            ? 'bg-sky-500/20 text-sky-200 border border-sky-400/30'
                            : 'bg-zinc-800/80 text-zinc-500 border border-white/5'
                        }`}
                      >
                        {member.keep ? 'Sẽ tải' : 'Bỏ qua'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Pagination */}
      {maxPage > 1 && (
        <div className="flex items-center justify-between text-xs text-zinc-400 pt-2">
          <span>
            Trang {page} / {maxPage} ({totalGroups} nhóm)
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="px-3 py-1 rounded bg-zinc-900 border border-white/5 disabled:opacity-40"
            >
              ← Trước
            </button>
            <button
              type="button"
              disabled={page >= maxPage}
              onClick={() => setPage((p) => p + 1)}
              className="px-3 py-1 rounded bg-zinc-900 border border-white/5 disabled:opacity-40"
            >
              Sau →
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
