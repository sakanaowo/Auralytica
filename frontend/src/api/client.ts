import {
  WorkflowState,
  VideoListResponse,
  MoveRequest,
  ExploreSummary,
  MetadataScope,
  MetadataRun,
  ClassificationPreview,
  DedupListResponse,
  DownloadPreviewData,
  DownloadBatch,
  AudioFormat,
  ConverterScanResponse,
  ConverterStatus,
  ConverterStartPayload,
} from './types';

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  let data: any;
  try {
    data = await response.json();
  } catch {
    throw new ApiError('Server trả kết quả không hợp lệ. Vui lòng thử lại.', response.status);
  }

  if (!response.ok) {
    const detail = typeof data?.detail === 'string' ? data.detail : 'Đã có lỗi xảy ra. Vui lòng kiểm tra lại.';
    throw new ApiError(detail, response.status);
  }

  return data as T;
}

export const api = {
  // Workflow
  getWorkflow: () => request<WorkflowState>('/api/workflow'),

  // Videos
  getVideos: (params: {
    group: 'music' | 'rest';
    search?: string;
    channel?: string;
    reason?: string;
    page?: number;
    page_size?: number;
    sort?: 'watch_count' | 'title' | 'channel';
  }) => {
    const sp = new URLSearchParams({
      group: params.group,
      page: String(params.page || 1),
      page_size: String(params.page_size || 50),
      sort: params.sort || 'watch_count',
    });
    if (params.search?.trim()) sp.set('search', params.search.trim());
    if (params.channel?.trim()) sp.set('channel', params.channel.trim());
    if (params.reason) sp.set('reason', params.reason);
    return request<VideoListResponse>(`/api/videos?${sp.toString()}`);
  },

  moveVideos: (payload: MoveRequest) =>
    request<{ moved: number; to_group: 'music' | 'rest' }>('/api/videos/move', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),

  // Explore Summary
  getExploreSummary: () => request<ExploreSummary>('/api/explore/summary'),

  // Metadata & Classification
  getMetadataScope: (group: 'music' | 'rest' | 'all' = 'rest', limit = 50) =>
    request<MetadataScope>(`/api/metadata/scope?group=${group}&limit=${limit}`),

  getMetadataRuns: () => request<{ items: MetadataRun[] }>('/api/metadata/runs'),

  startMetadataRun: (payload: { group: 'music' | 'rest' | 'all'; limit: number; refresh: boolean }) =>
    request<MetadataRun>('/api/metadata/runs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),

  getMetadataRun: (runId: string) => request<MetadataRun>(`/api/metadata/runs/${runId}`),

  stopMetadataRun: (runId: string) =>
    request<MetadataRun>(`/api/metadata/runs/${runId}/stop`, { method: 'POST' }),

  resumeMetadataRun: (runId: string) =>
    request<MetadataRun>(`/api/metadata/runs/${runId}/resume`, { method: 'POST' }),

  createClassificationPreview: () =>
    request<ClassificationPreview>('/api/classification/previews', { method: 'POST' }),

  getClassificationPreview: (previewId: string) =>
    request<ClassificationPreview>(`/api/classification/previews/${previewId}`),

  applyClassificationPreview: (previewId: string) =>
    request<{ changed: number; preview_id: string }>(`/api/classification/previews/${previewId}/apply`, {
      method: 'POST',
    }),

  // Deduplication
  getDedupLatest: () =>
    request<{ run: { run_id: string; stale: boolean } | null; selection_revision: number }>('/api/dedup/runs/latest'),

  startDedupRun: () => request<DedupListResponse['run']>('/api/dedup/runs', { method: 'POST' }),

  getDedupGroups: (runId: string, page = 1, pageSize = 20) =>
    request<DedupListResponse>(`/api/dedup/runs/${runId}/groups?page=${page}&page_size=${pageSize}`),

  updateDedupSelections: (videoIds: string[], keep: boolean, expectedRevision: number) =>
    request<{ revision: number; updated: number }>('/api/dedup/selections', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ video_ids: videoIds, keep, expected_revision: expectedRevision }),
    }),

  setGroupRejection: (groupId: string, rejected: boolean, expectedRevision: number) =>
    request<{ revision: number; rejected: boolean }>(`/api/dedup/groups/${groupId}/rejection`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rejected, expected_revision: expectedRevision }),
    }),

  confirmVideoAliases: (videoIds: string[], artistScope?: string) =>
    request<{ alias: any; run: any }>('/api/dedup/aliases', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ video_ids: videoIds, artist_scope: artistScope || null }),
    }),

  // Downloads
  getDownloadPreview: (outputDir: string) => {
    const sp = new URLSearchParams({ output_dir: outputDir });
    return request<DownloadPreviewData>(`/api/downloads/preview?${sp.toString()}`);
  },

  getDownloads: () => request<{ batches: DownloadBatch[] }>('/api/downloads'),

  getDownloadBatch: (batchId: number, page = 1, pageSize = 20, status?: string) => {
    const sp = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    if (status && status !== 'all') {
      sp.set('status', status);
    }
    return request<DownloadBatch>(`/api/downloads/${batchId}?${sp.toString()}`);
  },

  retryFailedDownloads: (batchId: number) =>
    request<DownloadBatch>(`/api/downloads/${batchId}/retry-failed`, { method: 'POST' }),

  retryDownloadItem: (batchId: number, videoId: string) =>
    request<DownloadBatch>(`/api/downloads/${batchId}/items/${videoId}/retry`, { method: 'POST' }),

  startDownload: (
    outputDir: string,
    previewToken: string,
    format: AudioFormat = 'm4a_alac',
    cleanNames: boolean = true,
    embedMetadata: boolean = true
  ) =>
    request<DownloadBatch>('/api/downloads', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        output_dir: outputDir,
        preview_token: previewToken,
        format,
        clean_names: cleanNames,
        embed_metadata: embedMetadata,
      }),
    }),

  stopDownload: (batchId: number) =>
    request<DownloadBatch>(`/api/downloads/${batchId}/stop`, { method: 'POST' }),

  resumeDownload: (batchId: number) =>
    request<DownloadBatch>(`/api/downloads/${batchId}/resume`, { method: 'POST' }),

  // Import
  importUpload: (formData: FormData) =>
    request<{ import_id: number; unique_videos: number; video_events: number }>('/api/imports', {
      method: 'POST',
      body: formData,
    }),

  // Converter
  scanConverter: (directory?: string) => {
    const sp = new URLSearchParams();
    if (directory) sp.set('directory', directory);
    const qs = sp.toString() ? `?${sp.toString()}` : '';
    return request<ConverterScanResponse>(`/api/converter/scan${qs}`);
  },

  startConversion: (payload: ConverterStartPayload) =>
    request<ConverterStatus>('/api/converter/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),

  getConverterStatus: () => request<ConverterStatus>('/api/converter/status'),

  stopConversion: () => request<ConverterStatus>('/api/converter/stop', { method: 'POST' }),

  renameFiles: (items: Array<{ source_path: string; new_name: string }>) =>
    request<{ results: Array<{ source: string; target?: string; status: string; error?: string }> }>(
      '/api/converter/rename',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items }),
      }
    ),
};

