// Enums
export type SearchStatus = 'queued' | 'processing' | 'completed' | 'failed';

export type Platform = 'tiktok' | 'instagram' | 'youtube' | 'twitter' | 'other';

export type FeedbackLabel = 'very_relevant' | 'somewhat_relevant' | 'irrelevant';

export type IngestionSourceType = 'local_folder' | 'csv_import' | 'url_stub' | 'demo_seed';

export type IngestionJobStatus = 'queued' | 'processing' | 'completed' | 'failed';

// Search types
export interface SearchCreate {
  raw_query: string;
  user_id?: string;
  platforms?: Platform[];
  region?: string;
  language?: string;
  date_from?: string;
  date_to?: string;
  max_results?: number;
  include_filters?: Record<string, unknown>;
  exclude_filters?: Record<string, unknown>;
  confidence_threshold?: number;
}

export interface Search {
  id: string;
  user_id?: string;
  raw_query: string;
  normalized_query_json?: Record<string, unknown>;
  region?: string;
  language?: string;
  platforms?: Platform[];
  include_filters_json?: Record<string, unknown>;
  exclude_filters_json?: Record<string, unknown>;
  date_from?: string;
  date_to?: string;
  max_results: number;
  confidence_threshold: number;
  status: SearchStatus;
  progress_percent: number;
  total_candidates: number;
  total_analyzed: number;
  total_results: number;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface MatchedSegment {
  start_sec: number;
  end_sec: number;
  dimension: string;
  label: string;
  score: number;
}

export interface SearchResult {
  id: string;
  search_id: string;
  candidate_video_id: string;
  final_score: number;
  rank_position: number;
  accepted: boolean;
  reason_codes_json?: string[];
  score_breakdown_json?: Record<string, number>;
  matched_segments_json?: MatchedSegment[];
  duplicate_group_id?: string;
  created_at?: string;
  updated_at?: string;
  // Hydrated fields from candidate_video
  platform?: string;
  source_url?: string;
  creator_handle?: string;
  caption_text?: string;
  thumbnail_path?: string;
}

export interface ResultExplanation {
  result_id: string;
  final_score: number;
  rank_position: number;
  score_breakdown?: Record<string, number>;
  matched_segments?: MatchedSegment[];
  reason_codes?: string[];
}

// Collection types
export interface CollectionCreate {
  name: string;
  description?: string;
}

export interface Collection {
  id: string;
  user_id?: string;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface CollectionItemCreate {
  candidate_video_id: string;
  notes?: string;
}

export interface CollectionItem {
  id: string;
  collection_id: string;
  candidate_video_id: string;
  notes?: string;
  created_at: string;
}

// Ingestion types
export interface IngestionJobCreate {
  source_type: string;
  source_config: Record<string, unknown>;
}

export interface IngestionJob {
  id: string;
  source_type: string;
  source_config_json: Record<string, unknown>;
  status: IngestionJobStatus;
  total_records: number;
  imported_records: number;
  rejected_records: number;
  log_json?: unknown[];
  created_at: string;
  updated_at: string;
}

// Feedback
export interface FeedbackCreate {
  user_id?: string;
  search_id: string;
  candidate_video_id: string;
  label: FeedbackLabel;
  reason?: string;
}

// API responses
export interface SearchListResponse {
  items: Search[];
  total: number;
  page: number;
  page_size: number;
}

export interface SearchResultResponse {
  search: Search;
  results: SearchResult[];
  total: number;
  page: number;
  page_size: number;
}

export interface HealthResponse {
  status: string;
  env: string;
}

// Rerank
export interface RerankRequest {
  strategy?: string;
  weights?: Record<string, number>;
}
