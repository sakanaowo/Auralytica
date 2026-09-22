import React, { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../api/client';
import { ColumnPane } from '../../components/ColumnPane';

interface ExploreViewProps {
  batchLocked: boolean;
  onRefreshWorkflow: () => void;
}

export const ExploreView: React.FC<ExploreViewProps> = ({ batchLocked, onRefreshWorkflow }) => {
  const queryClient = useQueryClient();

  // Read initial params from URL
  const initialParams = new URLSearchParams(window.location.search);

  // Shared page size for both columns (default 10 items to fit screen comfortably without scrolling)
  const [sharedPageSize, setSharedPageSize] = useState<number>(
    Number(initialParams.get('size')) || Number(initialParams.get('music_size')) || Number(initialParams.get('rest_size')) || 10
  );

  const [musicFilters, setMusicFilters] = useState({
    search: initialParams.get('music_search') || '',
    reason: initialParams.get('music_reason') || '',
    sort: (initialParams.get('music_sort') as any) || 'watch_count',
    page: Number(initialParams.get('music_page')) || 1,
    pageSize: sharedPageSize,
  });

  const [restFilters, setRestFilters] = useState({
    search: initialParams.get('rest_search') || '',
    reason: initialParams.get('rest_reason') || '',
    sort: (initialParams.get('rest_sort') as any) || 'watch_count',
    page: Number(initialParams.get('rest_page')) || 1,
    pageSize: sharedPageSize,
  });

  const [selectedMusicIds, setSelectedMusicIds] = useState<Set<string>>(new Set());
  const [selectedRestIds, setSelectedRestIds] = useState<Set<string>>(new Set());

  // Handle changing page size for both columns simultaneously
  const handlePageSizeChange = (newSize: number) => {
    setSharedPageSize(newSize);
    setMusicFilters((prev) => ({ ...prev, pageSize: newSize, page: 1 }));
    setRestFilters((prev) => ({ ...prev, pageSize: newSize, page: 1 }));
  };

  // Sync filters to URL
  useEffect(() => {
    const sp = new URLSearchParams();
    if (musicFilters.search) sp.set('music_search', musicFilters.search);
    if (musicFilters.reason) sp.set('music_reason', musicFilters.reason);
    if (musicFilters.sort !== 'watch_count') sp.set('music_sort', musicFilters.sort);
    if (musicFilters.page > 1) sp.set('music_page', String(musicFilters.page));
    if (sharedPageSize !== 10) sp.set('size', String(sharedPageSize));

    if (restFilters.search) sp.set('rest_search', restFilters.search);
    if (restFilters.reason) sp.set('rest_reason', restFilters.reason);
    if (restFilters.sort !== 'watch_count') sp.set('rest_sort', restFilters.sort);
    if (restFilters.page > 1) sp.set('rest_page', String(restFilters.page));

    const newUrl = '/explore' + (sp.toString() ? '?' + sp.toString() : '');
    if (newUrl !== window.location.pathname + window.location.search) {
      window.history.replaceState(null, '', newUrl);
    }
  }, [musicFilters, restFilters, sharedPageSize]);

  // Fetch Music
  const musicQuery = useQuery({
    queryKey: ['videos', 'music', musicFilters],
    queryFn: () =>
      api.getVideos({
        group: 'music',
        search: musicFilters.search,
        reason: musicFilters.reason,
        sort: musicFilters.sort,
        page: musicFilters.page,
        page_size: musicFilters.pageSize,
      }),
  });

  // Fetch Rest
  const restQuery = useQuery({
    queryKey: ['videos', 'rest', restFilters],
    queryFn: () =>
      api.getVideos({
        group: 'rest',
        search: restFilters.search,
        reason: restFilters.reason,
        sort: restFilters.sort,
        page: restFilters.page,
        page_size: restFilters.pageSize,
      }),
  });

  // Move mutation
  const moveMutation = useMutation({
    mutationFn: (vars: { video_ids: string[]; to_group: 'music' | 'rest' }) => api.moveVideos(vars),
    onSuccess: (_, vars) => {
      // Clear selections
      if (vars.to_group === 'rest') {
        setSelectedMusicIds(new Set());
      } else {
        setSelectedRestIds(new Set());
      }
      // Invalidate both lists & workflow
      queryClient.invalidateQueries({ queryKey: ['videos'] });
      onRefreshWorkflow();
    },
  });

  const handleToggleSelectMusic = useCallback((id: string) => {
    setSelectedMusicIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const handleToggleSelectRest = useCallback((id: string) => {
    setSelectedRestIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const handleSelectAllMusic = useCallback((pageIds: string[], checked: boolean) => {
    setSelectedMusicIds((prev) => {
      const next = new Set(prev);
      pageIds.forEach((id) => {
        if (checked) next.add(id);
        else next.delete(id);
      });
      return next;
    });
  }, []);

  const handleSelectAllRest = useCallback((pageIds: string[], checked: boolean) => {
    setSelectedRestIds((prev) => {
      const next = new Set(prev);
      pageIds.forEach((id) => {
        if (checked) next.add(id);
        else next.delete(id);
      });
      return next;
    });
  }, []);

  const handleMove = (ids: string[], toGroup: 'music' | 'rest') => {
    if (batchLocked || moveMutation.isPending || ids.length === 0) return;
    moveMutation.mutate({ video_ids: ids, to_group: toGroup });
  };

  return (
    <div className="flex flex-col h-full space-y-3">

      {/* Dual-Pane 50/50 Split View */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 flex-1 min-h-0">
        {/* Left Pane: Music */}
        <ColumnPane
          title="Nhạc đã nhận diện"
          group="music"
          data={musicQuery.data}
          isLoading={musicQuery.isLoading}
          selectedIds={selectedMusicIds}
          onToggleSelect={handleToggleSelectMusic}
          onSelectAllPage={handleSelectAllMusic}
          onMove={handleMove}
          disabled={batchLocked || moveMutation.isPending}
          search={musicFilters.search}
          reason={musicFilters.reason}
          sort={musicFilters.sort}
          page={musicFilters.page}
          pageSize={musicFilters.pageSize}
          onUpdateFilters={(updates) => setMusicFilters((prev) => ({ ...prev, ...updates }))}
          onPageSizeChange={handlePageSizeChange}
        />

        {/* Right Pane: Rest */}
        <ColumnPane
          title="Còn lại (Cần duyệt / Bổ sung)"
          group="rest"
          data={restQuery.data}
          isLoading={restQuery.isLoading}
          selectedIds={selectedRestIds}
          onToggleSelect={handleToggleSelectRest}
          onSelectAllPage={handleSelectAllRest}
          onMove={handleMove}
          disabled={batchLocked || moveMutation.isPending}
          search={restFilters.search}
          reason={restFilters.reason}
          sort={restFilters.sort}
          page={restFilters.page}
          pageSize={restFilters.pageSize}
          onUpdateFilters={(updates) => setRestFilters((prev) => ({ ...prev, ...updates }))}
          onPageSizeChange={handlePageSizeChange}
        />
      </div>

      {/*
        TODO: Collect user correction & implicit labeling data for future AI model fine-tuning.
        User feedback on classifications will be gathered silently to enhance heuristic accuracy.
      */}
    </div>
  );
};
