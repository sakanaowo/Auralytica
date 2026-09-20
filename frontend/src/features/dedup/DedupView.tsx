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
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-zinc-100">
            03 · Deduplicate — Chọn bản của cùng bài
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            So sánh các video nghi cùng bài. Mọi bản được giữ mặc định; bạn có thể bỏ chọn các bản không muốn tải.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            disabled={scanMutation.isPending}
            onClick={() => scanMutation.mutate()}
            className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-zinc-100 text-zinc-900 hover:bg-white border border-white transition-all shadow-sm"
          >
            {scanMutation.isPending ? 'Đang quét...' : 'Quét lại gợi ý'}
          </button>

          <button
            type="button"
            onClick={onNavigateDownload}
            className="px-3.5 py-1.5 text-xs font-medium rounded-lg glass-card text-zinc-300 hover:text-white border border-white/10"
          >
            Bỏ qua bước này → Download
          </button>
        </div>
      </div>

      {/* Manual Alias Card */}
      <details className="glass-panel rounded-xl border border-white/10 p-4 text-xs group">
        <summary className="font-semibold text-zinc-300 cursor-pointer select-none">
          Ghép thủ công hai hoặc nhiều video
        </summary>
        <form onSubmit={handleManualAlias} className="mt-3 space-y-3">
          <p className="text-zinc-500 text-[11px]">
            Dán các video ID cách nhau bằng dấu phẩy. Đây là xác nhận alias độc lập với việc loại bản tải.
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
            {aliasMsg && <span className="text-[11px] text-zinc-400">{aliasMsg}</span>}
          </div>
        </form>
      </details>

      {/* Groups List */}
      <div className="space-y-4">
        {groupsQuery.isLoading ? (
          <div className="py-12 text-center text-xs font-mono text-zinc-500">Đang tải danh sách nhóm trùng...</div>
        ) : groups.length === 0 ? (
          <div className="glass-panel rounded-2xl p-8 text-center text-xs text-zinc-400 space-y-2">
            <p>Chưa có nhóm nghi trùng nào. Mọi bản bài hát trong thư viện sẽ được giữ mặc định để tải.</p>
            <button
              type="button"
              onClick={onNavigateDownload}
              className="mt-2 text-zinc-200 underline font-medium hover:text-white"
            >
              Chuyển tiếp sang bước 04 · Download →
            </button>
          </div>
        ) : (
          groups.map((group: DedupGroup) => (
            <div
              key={group.group_id}
              className={`glass-panel rounded-xl border p-4 space-y-3 transition-opacity ${
                group.rejected ? 'opacity-50 border-white/5' : 'border-white/10'
              }`}
            >
              {/* Group Header */}
              <div className="flex items-center justify-between gap-4 pb-2 border-b border-white/5">
                <div>
                  <h3 className="text-sm font-semibold text-zinc-200">{group.title_key}</h3>
                  <div className="text-[11px] text-zinc-500 mt-0.5">
                    {group.evidence_type === 'confirmed_alias'
                      ? 'Alias đã xác nhận'
                      : group.artist_conflict
                        ? 'Tên chuẩn hóa giống · Kênh khác nhau · Cần xem kỹ'
                        : 'Tên chuẩn hóa giống nhau'}{' '}
                    · {group.member_count} bản thu
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
                    className="px-2.5 py-1 text-xs rounded-md bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border border-white/5"
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
                    className="px-2.5 py-1 text-xs rounded-md bg-zinc-900 hover:bg-zinc-800 text-zinc-300 border border-white/5"
                  >
                    {group.rejected ? 'Hoàn tác' : 'Không ghép nhóm này'}
                  </button>
                </div>
              </div>

              {/* Members List */}
              <div className="space-y-2">
                {group.members.map((member: DedupMember) => (
                  <div
                    key={member.video_id}
                    className="flex items-center gap-3 p-2 rounded-lg bg-zinc-950/30 border border-white/5 text-xs"
                  >
                    <input
                      type="checkbox"
                      checked={member.keep}
                      onChange={(e) =>
                        selectionMutation.mutate({
                          videoIds: [member.video_id],
                          keep: e.target.checked,
                        })
                      }
                      className="rounded border-zinc-700 bg-zinc-900 text-zinc-100 cursor-pointer"
                      title="Chọn giữ bản này để tải"
                    />

                    <div className="w-16 h-10 shrink-0 rounded bg-zinc-900 overflow-hidden">
                      <img
                        src={`https://i.ytimg.com/vi/${member.video_id}/mqdefault.jpg`}
                        alt=""
                        className="w-full h-full object-cover"
                        loading="lazy"
                      />
                    </div>

                    <div className="flex-1 min-w-0">
                      <a
                        href={`https://www.youtube.com/watch?v=${encodeURIComponent(member.video_id)}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-medium text-zinc-200 hover:text-white line-clamp-1"
                      >
                        {member.raw_title || member.video_id}
                      </a>
                      <div className="text-[11px] text-zinc-500 truncate">
                        {member.channel} · {member.version_marker || 'Bản chuẩn'}
                      </div>
                    </div>

                    <span className="text-[10px] text-zinc-500 font-mono">
                      {member.keep ? 'Sẽ tải' : 'Loại bỏ'}
                    </span>
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
