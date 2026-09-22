export interface WorkflowState {
  active_import: number | null;
  counts: {
    music: number;
    rest: number;
  };
  batch_locked: boolean;
  steps: {
    import: 'ready' | 'locked' | 'needs_import';
    explore: 'ready' | 'needs_import';
    deduplicate: 'ready' | 'no_music' | 'needs_import';
    download: 'ready' | 'no_music' | 'needs_import';
  };
  revision: string;
}

export interface VideoEvidence {
  code: string;
  source: string;
  details?: Record<string, unknown>;
}

export interface VideoItem {
  id: string;
  title: string;
  channel_name: string;
  watch_count: number;
  reason: string;
  decision_source: 'user' | 'auto';
  evidence: VideoEvidence[];
  download_status: string | null;
}

export interface VideoListResponse {
  items: VideoItem[];
  filtered_count: number;
  group_totals: {
    music: number;
    rest: number;
  };
  page: number;
  page_size: number;
}

export interface MoveRequest {
  video_ids: string[];
  to_group: 'music' | 'rest';
}

export interface ExploreSummary {
  import_id: number;
  videos: number;
  watch_events: number;
  watch_days_utc: number;
  decisions: {
    user: number;
    automatic: number;
  };
  undated_events: number;
  metadata: {
    available: number;
    missing: number;
    fresh: number;
    stale: number;
    applied: number;
  };
  title_signals: {
    music_terms: number;
    talk_terms: number;
  };
  repeat_distribution: Record<string, number>;
  day_distribution: Record<string, number>;
  channels: Array<{
    name: string;
    videos: number;
    watch_events: number;
  }>;
  recent_days: Array<{
    day: string;
    events: number;
  }>;
  import_statistics: {
    unique_videos: number;
    video_events: number;
  };
}

export interface MetadataScope {
  group: 'music' | 'rest' | 'all';
  available: number;
  selected: number;
  cached: number;
  stale: number;
  video_ids: string[];
}

export interface MetadataRun {
  run_id: string;
  status: 'pending' | 'running' | 'stop_requested' | 'paused' | 'completed' | 'partial' | 'failed';
  total: number;
  counts: {
    done?: number;
    failed?: number;
  };
}

export interface ClassificationPreviewItem {
  video_id: string;
  title?: string;
  current_group: string;
  proposed_group: string;
  reason: string;
  changed: boolean;
}

export interface ClassificationPreview {
  preview_id: string;
  status: string;
  changed: number;
  items: ClassificationPreviewItem[];
}

export interface DedupMember {
  video_id: string;
  raw_title: string;
  channel: string;
  version_marker: string | null;
  keep: boolean;
  evidence: {
    source: string;
    alias_source?: string;
  };
}

export interface DedupGroup {
  group_id: string;
  title_key: string;
  evidence_type: string;
  artist_conflict: boolean;
  member_count: number;
  member_page: number;
  member_page_size: number;
  rejected: boolean;
  members: DedupMember[];
}

export interface DedupListResponse {
  run: {
    run_id: string;
    stale: boolean;
  };
  selection_revision: number;
  total: number;
  page: number;
  page_size: number;
  items: DedupGroup[];
}

export interface DownloadPreviewData {
  music: number;
  excluded: number;
  kept: number;
  skipped: number;
  needed: number;
  token: string;
}

export interface DownloadBatchItem {
  video_id: string;
  title: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'skipped' | 'cancelled';
  downloaded_bytes: number;
  total_bytes?: number;
  error_code?: string | null;
  error_message?: string | null;
}

export interface DownloadBatch {
  batch_id: number;
  status: 'queued' | 'running' | 'paused' | 'completed' | 'partial' | 'failed' | 'cancelled';
  output_dir: string;
  total: number;
  queued?: number;
  skipped?: number;
  counts: {
    completed?: number;
    failed?: number;
    skipped?: number;
    running?: number;
    queued?: number;
  };
  page?: number;
  page_size?: number;
  filtered_total?: number;
  filter_status?: string;
  stop_requested: boolean;
  error: string | null;
  items: DownloadBatchItem[];
}

export interface ConverterItem {
  source_path: string;
  filename: string;
  raw_stem: string;
  suffix: string;
  size: number;
  video_id: string | null;
  cleaned_stem: string;
  artist: string;
  title: string;
  is_apple_compatible: boolean;
  suggested_apple_filename: string;
}

export interface ConverterScanResponse {
  directory: string;
  total: number;
  compatible_count: number;
  incompatible_count: number;
  has_video_id_count: number;
  items: ConverterItem[];
}

export interface ConverterStatus {
  state: 'idle' | 'running' | 'completed' | 'paused' | 'failed';
  format: 'm4a_alac' | 'm4a_aac' | 'mp3';
  output_dir: string;
  total: number;
  completed: number;
  failed: number;
  current_file: string;
  items: Array<{
    source: string;
    target: string;
    status: 'completed' | 'failed';
    error: string | null;
  }>;
  error: string | null;
  started_at: number | null;
  finished_at: number | null;
}

export interface ConverterStartPayload {
  directory: string;
  output_dir: string;
  format: 'm4a_alac' | 'm4a_aac' | 'mp3';
  remove_source?: boolean;
  items?: Array<{
    source_path: string;
    cleaned_stem?: string;
    artist?: string;
    title?: string;
  }>;
}
