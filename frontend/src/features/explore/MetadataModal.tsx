import React, { useState, useEffect } from 'react';
import { api } from '../../api/client';
import { MetadataScope, MetadataRun, ClassificationPreview } from '../../api/types';

interface MetadataModalProps {
  isOpen: boolean;
  onClose: () => void;
  onApplied: () => void;
  batchLocked: boolean;
}

export const MetadataModal: React.FC<MetadataModalProps> = ({
  isOpen,
  onClose,
  onApplied,
  batchLocked,
}) => {
  const [group, setGroup] = useState<'rest' | 'music' | 'all'>('rest');
  const [limit, setLimit] = useState(50);
  const [refresh, setRefresh] = useState(false);
  const [scope, setScope] = useState<MetadataScope | null>(null);
  const [activeRun, setActiveRun] = useState<MetadataRun | null>(null);
  const [preview, setPreview] = useState<ClassificationPreview | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Load scope on open or filter change
  useEffect(() => {
    if (!isOpen) return;
    let cancel = false;
    api
      .getMetadataScope(group, limit)
      .then((data) => {
        if (!cancel) setScope(data);
      })
      .catch((err) => {
        if (!cancel) setMessage(err.message);
      });
    return () => {
      cancel = true;
    };
  }, [isOpen, group, limit]);

  // Poll active run if running
  useEffect(() => {
    if (!isOpen || !activeRun) return;
    if (!['pending', 'running', 'stop_requested'].includes(activeRun.status)) return;

    const timer = setTimeout(() => {
      api
        .getMetadataRun(activeRun.run_id)
        .then(setActiveRun)
        .catch(() => {});
    }, 1000);
    return () => clearTimeout(timer);
  }, [isOpen, activeRun]);

  if (!isOpen) return null;

  const handleStart = async () => {
    setLoading(true);
    setMessage(null);
    try {
      const run = await api.startMetadataRun({ group, limit, refresh });
      setActiveRun(run);
    } catch (err: any) {
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    if (!activeRun) return;
    try {
      const run = await api.stopMetadataRun(activeRun.run_id);
      setActiveRun(run);
    } catch (err: any) {
      setMessage(err.message);
    }
  };

  const handleResume = async () => {
    if (!activeRun) return;
    try {
      const run = await api.resumeMetadataRun(activeRun.run_id);
      setActiveRun(run);
    } catch (err: any) {
      setMessage(err.message);
    }
  };

  const handleCreatePreview = async () => {
    setLoading(true);
    setMessage(null);
    try {
      const p = await api.createClassificationPreview();
      setPreview(p);
    } catch (err: any) {
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleApplyPreview = async () => {
    if (!preview) return;
    setLoading(true);
    try {
      const res = await api.applyClassificationPreview(preview.preview_id);
      setMessage(`Đã áp dụng thành công ${res.changed} thay đổi vào thư viện.`);
      setPreview(null);
      onApplied();
    } catch (err: any) {
      setMessage(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md">
      <div className="w-full max-w-2xl glass-panel rounded-2xl border border-white/10 p-6 flex flex-col max-h-[90vh] shadow-2xl">
        {/* Modal Header */}
        <div className="flex items-center justify-between pb-4 border-b border-white/10">
          <div>
            <h3 className="text-sm font-semibold tracking-wide text-zinc-100 uppercase">
              Cập nhật Metadata & Xem trước phân loại
            </h3>
            <p className="text-xs text-zinc-400 mt-0.5">
              Lấy thông tin từ YouTube Music và kiểm tra đề xuất chuyển nhóm trước khi áp dụng.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-xs px-2.5 py-1 rounded-md bg-zinc-800 hover:bg-zinc-700 text-zinc-300 border border-white/10 transition-colors"
          >
            Đóng
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto py-4 space-y-5 text-xs text-zinc-300">
          {/* Controls */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-3.5 rounded-xl bg-zinc-950/40 border border-white/5">
            <div>
              <label className="block text-[11px] text-zinc-400 mb-1">Phạm vi</label>
              <select
                value={group}
                onChange={(e) => setGroup(e.target.value as any)}
                className="w-full px-2.5 py-1.5 rounded-lg glass-input text-zinc-200"
              >
                <option value="rest">Còn lại</option>
                <option value="music">Nhạc</option>
                <option value="all">Tất cả</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] text-zinc-400 mb-1">Số lượng video</label>
              <input
                type="number"
                min={1}
                max={1000}
                value={limit}
                onChange={(e) => setLimit(Math.max(1, Math.min(1000, Number(e.target.value))))}
                className="w-full px-2.5 py-1.5 rounded-lg glass-input text-zinc-200 font-mono"
              />
            </div>

            <div className="flex items-center pt-5">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={refresh}
                  onChange={(e) => setRefresh(e.target.checked)}
                  className="rounded border-zinc-700 bg-zinc-900 text-zinc-100"
                />
                <span className="text-zinc-400 text-[11px]">Bỏ qua cache còn hạn</span>
              </label>
            </div>
          </div>

          {/* Scope Info */}
          {scope && (
            <div className="text-[11px] text-zinc-400 px-1">
              Phạm vi: <strong className="text-zinc-200">{scope.selected}</strong> / {scope.available} video ·{' '}
              {scope.cached} cache còn hạn · {scope.stale} cache cũ.
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-2 pt-1">
            <button
              type="button"
              disabled={loading || batchLocked || !scope?.selected}
              onClick={handleStart}
              className="px-4 py-1.5 text-xs font-medium rounded-lg bg-zinc-100 text-zinc-900 hover:bg-white border border-white disabled:opacity-40 transition-colors shadow-sm"
            >
              Bắt đầu lấy metadata
            </button>

            {activeRun && ['pending', 'running'].includes(activeRun.status) && (
              <button
                type="button"
                onClick={handleStop}
                className="px-3 py-1.5 text-xs rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-white/10"
              >
                Tạm dừng
              </button>
            )}

            {activeRun && ['paused', 'partial', 'failed'].includes(activeRun.status) && (
              <button
                type="button"
                onClick={handleResume}
                disabled={batchLocked}
                className="px-3 py-1.5 text-xs rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-white/10"
              >
                Tiếp tục lượt này
              </button>
            )}
          </div>

          {/* Active Run Status */}
          {activeRun && (
            <div className="p-3 rounded-xl bg-zinc-950/50 border border-white/5 font-mono text-[11px]">
              Trạng thái: <span className="text-zinc-200 uppercase">{activeRun.status}</span> · Đã xong:{' '}
              {activeRun.counts.done || 0}/{activeRun.total} · Lỗi: {activeRun.counts.failed || 0}
            </div>
          )}

          <hr className="border-white/10" />

          {/* Classification Preview Section */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="text-xs font-semibold uppercase text-zinc-200">Xem trước phân loại</h4>
                <p className="text-[11px] text-zinc-500">
                  Tạo preview các đề xuất chuyển nhóm dựa trên metadata mới thu thập.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={loading}
                  onClick={handleCreatePreview}
                  className="px-3 py-1.5 text-xs rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 border border-white/10"
                >
                  Tạo preview
                </button>

                {preview && preview.changed > 0 && (
                  <button
                    type="button"
                    disabled={loading || batchLocked}
                    onClick={handleApplyPreview}
                    className="px-3 py-1.5 text-xs font-medium rounded-lg bg-zinc-100 text-zinc-900 hover:bg-white border border-white shadow-sm"
                  >
                    Áp dụng ({preview.changed})
                  </button>
                )}
              </div>
            </div>

            {preview && (
              <div className="space-y-2">
                <div className="text-[11px] text-zinc-400">
                  Có <strong className="text-zinc-200">{preview.changed}</strong> thay đổi đề xuất trên tổng số{' '}
                  {preview.items.length} video có metadata. Nhãn thủ công luôn được bảo toàn.
                </div>

                {preview.changed > 0 && (
                  <div className="max-h-48 overflow-y-auto rounded-lg border border-white/5 bg-zinc-950/40">
                    <table className="w-full text-left border-collapse text-[11px]">
                      <thead>
                        <tr className="border-b border-white/10 bg-zinc-900/60 text-zinc-400 font-mono">
                          <th className="p-2">Video</th>
                          <th className="p-2">Đề xuất</th>
                          <th className="p-2">Lý do</th>
                        </tr>
                      </thead>
                      <tbody>
                        {preview.items
                          .filter((i) => i.changed)
                          .map((item) => (
                            <tr key={item.video_id} className="border-b border-white/5 hover:bg-white/[0.02]">
                              <td className="p-2 text-zinc-200 truncate max-w-[200px]">
                                {item.title || item.video_id}
                              </td>
                              <td className="p-2 font-mono text-zinc-300">
                                {item.current_group} → {item.proposed_group}
                              </td>
                              <td className="p-2 text-zinc-400">{item.reason}</td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>

          {message && (
            <div className="p-2.5 rounded-lg bg-zinc-800/80 border border-white/10 text-zinc-300 text-xs">
              {message}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
