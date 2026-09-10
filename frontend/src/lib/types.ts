export type JobStatus = 'QUEUED' | 'RUNNING' | 'NEEDS_USER' | 'COMPLETED' | 'PARTIAL_SUCCESS' | 'FAILED' | 'CANCELLED'
export type ContentType = 'RECRUITMENT' | 'TRAVEL' | 'VIDEO_NOTE' | 'UNSUPPORTED'
export type UserState = 'DISCOVERED' | 'SAVED' | 'PLANNED' | 'VISITED' | 'DISMISSED'

export interface JobView {
  id: string
  job_type: string
  status: JobStatus
  current_step: string
  progress: number
  title: string
  error: string | null
  error_code: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
  retry_count: number
  worker_id: string | null
  heartbeat_at: string | null
  last_activity_at: string | null
  current_step_status: string | null
  current_step_started_at: string | null
  current_step_message: string | null
  runtime_state: 'ACTIVE' | 'STALLED' | 'IDLE' | 'UNKNOWN'
  last_activity_age_seconds: number | null
  last_activity_source: string | null
  completion_summary: string | null
  model_step: string | null
  provider: string | null
  model: string | null
}

export interface ContentView {
  id: string
  content_type: ContentType
  title: string
  summary: string
  status: string
  user_state: UserState
  structured: Record<string, unknown>
  updated_at: string
}

export interface DashboardView {
  job_counts: Record<string, number>
  jobs: JobView[]
  contents: ContentView[]
}

export interface RuntimeCheck {
  name: string
  status: 'READY' | 'MISSING' | 'DEGRADED' | 'UNAVAILABLE'
  detail: string
  path?: string | null
}

export interface StatusView {
  node_name: string
  deployment_target: string
  system: string
  release: string
  architecture: string
  python: string
  data_dir: string
  database: string
  lan_url: string
  services: Record<string, string>
  runtime: { ollama: string; asr: string }
  hardware: {
    machine_name: string
    model: string
    chip: string
    cpu_cores: number | null
    gpu: string
    gpu_cores: number | null
    memory: string
    architecture: string
    lan_ip: string
    disk: { total_gb: number; used_gb: number; free_gb: number }
  }
  metrics: {
    sampled_at: string
    freshness: 'FRESH' | 'STALE' | 'PENDING'
    cpu: { percent: number | null; unavailable_reason: string | null; source?: string | null }
    memory: { used_bytes: number | null; total_bytes: number | null; available_bytes: number | null; cached_bytes: number | null; compressed_bytes: number | null; percent: number | null; method: string | null; unavailable_reason: string | null }
    disk: { used_bytes: number | null; total_bytes: number | null; percent: number | null; unavailable_reason: string | null }
    worker: { heartbeat_at: string | null; heartbeat_age_seconds: number | null }
  }
  runtime_checks: RuntimeCheck[]
}

export interface SourceView {
  id: string
  source_type: string
  locator: string
  title: string
  authority: string
  snapshot_count: number
  content_count: number
  updated_at: string
}

export interface SourceDetailView {
  id: string
  source_type: string
  locator: string
  title: string | null
  authority: string
  metadata: Record<string, unknown>
  snapshots: Array<{ id: string; content_hash: string; raw_path: string | null; captured_at: string }>
  segment_count: number
  contents: ContentView[]
  deletion: { allowed: boolean; content_count: number; video_note_count: number; active_job_count: number }
}

export interface TodoView {
  id: string
  kind: string
  title: string
  detail: string
  to: string
  created_at: string
}

export interface ProfileView {
  name: string
  education: string
  major: string
  graduation_year: string
  graduate_status: string
  household_registration: string
  preferred_regions: string[]
}

export interface LogEventView {
  id: string
  created_at: string
  level: string
  component: string
  event_type: string
  message: string
  actor: string
  entity_type: string | null
  entity_id: string | null
  request_id: string | null
  detail: Record<string, unknown>
}

export interface LogsView {
  items: LogEventView[]
  next_cursor: string | null
  server_time: string
  applied_filters: Record<string, unknown>
}

export interface ModelProfileView {
  id: string
  name: string
  provider: string
  base_url: string
  model: string
  timeout_seconds: number
  request_interval_seconds: number | null
  api_key_saved: boolean
  location: 'LOCAL' | 'REMOTE'
  modalities: string[]
  capabilities: string[]
  supports_json_mode: boolean
  supports_json_schema: boolean
  supports_thinking: boolean
  supports_tools: boolean
  context_window: number
  recommended_working_context: number
  max_output_tokens: number
  quality_tier: 'FAST' | 'MAIN' | 'STRONG' | 'SPECIALIST'
  specialties: string[]
  enabled: boolean
  probe_results: Record<string, string>
}

export interface AIStagePolicy {
  stage: string
  capability: string
  execution_mode: 'AUTO' | 'LOCAL_ONLY' | 'LOCAL_FIRST' | 'REMOTE_FIRST' | 'REMOTE_ONLY' | null
  local_profile_id: string | null
  remote_profile_id: string | null
  temperature: number | null
  max_input_tokens: number | null
  max_output_tokens: number | null
  thinking: boolean | null
  timeout_seconds: number | null
  retry_count: number | null
  confidence_threshold: number | null
  escalation_threshold: number | null
  context_strategy: string | null
  chunk_size: number | null
  neighbor_segments: number | null
  domain: string | null
  domain_pack_ids: string[]
  cache_enabled: boolean | null
  force_regenerate: boolean
  version: number
  sources?: Record<string, string>
}

export interface AIStageView {
  stage: string
  capability: string
  parameter_spec: string[]
  resolved_default: AIStagePolicy
}

export interface AIUsageView {
  total: { calls: number; input_tokens: number; output_tokens: number; cached_tokens: number; duration_ms: number }
  local: { calls: number; input_tokens: number; output_tokens: number; cached_tokens: number; duration_ms: number }
  remote: { calls: number; input_tokens: number; output_tokens: number; cached_tokens: number; duration_ms: number }
  by_stage: Record<string, { calls: number; input_tokens: number; output_tokens: number; cached_tokens: number; duration_ms: number }>
  by_model: Record<string, { calls: number; input_tokens: number; output_tokens: number; cached_tokens: number; duration_ms: number }>
  cache: { hits: number }
  escalations: number
}

export interface DomainPackView {
  id: string
  name: string
  version: string
  glossary: Record<string, string>
  aliases: Record<string, string[]>
  rules: string[]
  examples: Array<{ input: string; output: string }>
  prompt_supplement: string
  allowed_capabilities: string[]
}

export interface ModelRoutingView {
  primary_id: string | null
  fallback_id: string | null
}

export interface TranscriptProcessingView {
  chunk_chars: number
  batch_size: number
  timeout_seconds: number
}

export interface PromptSupplementsView {
  transcript_correction: string
  video_note_summary: string
  travel_place_extraction: string
  core_contracts: Record<string, string[]>
  max_length: number
  version: string
  hashes: Record<string, string>
}

export interface PlaceObservation {
  type: string
  value?: string
  timestamp?: string
}

export interface PlacePreview {
  id: string
  name: string
  address: string
  place_type: string
  summary: string
  user_state: UserState
  observations: PlaceObservation[]
}

export interface MapMarker {
  id: string
  marker_id: string | null
  place_id: string | null
  origin: string
  visibility: string
  name: string
  canonical_name: string
  place_type: string
  latitude: number
  longitude: number
  user_state: UserState
  summary: string
  address: string
  preview_image: string | null
  brief: Record<string, unknown>
  source_count: number
  visit_window_summary?: string
  visit_window_state?: string
  visit_window_reason?: string
  recommendation?: { tier?: string; label?: string; reasons?: Array<{ text: string }> }
}

export interface MapOverviewView {
  coordinate_system: 'GCJ02'
  total_places: number
  visible_places: number
  markers: MapMarker[]
  clusters: Array<Record<string, unknown>>
  selected_place_id: string | null
  selected_preview: PlacePreview | null
  route_draft_count: number
  viewport: { bbox: number[]; zoom: number; is_default_china: boolean }
}

export interface PlaceListView { items: MapMarker[]; next_cursor: string | null; total: number }
export interface PlaceVisitWindow { id: string; season: string | null; month: number | null; month_segment: string | null; day_time_slot: string | null; period_type: string; suitability: string; source_text: string; segment_ids: string[]; provenance: string; confidence: number; status: string }

export interface RouteDraftView {
  id: string
  name: string
  city: string
  status: string
  places: PlacePreview[]
}

export interface VideoNoteView {
  id: string
  status: string
  title: string
  canonical_url: string
  cover_url: string | null
  cover_status?: string
  cover_image_url?: string | null
  cover_width?: number | null
  cover_height?: number | null
  cover_error?: string | null
  uploader: string
  duration_ms: number | null
  current_version_id: string | null
  overview: string
  updated_at: string
  place_summary: { total: number; confirmed: number }
}

export interface VideoNoteDetail extends VideoNoteView {
  markdown: string
  warnings: string[]
  needs_regeneration: boolean
  sections: Array<{ id: string; heading: string; thesis: string; summary: string; bullets: string[]; anchor_id: string; body_markdown: string; segment_ids: string[]; start_ms: number | null; end_ms: number | null }>
  transcript_status: 'AVAILABLE' | 'EXPIRED' | 'NOT_READY'
  transcript_segment_count: number
  transcript_retention_until: string | null
  screenshot_status: 'PLANNING' | 'READY' | 'PARTIAL' | 'UNAVAILABLE'
}

export interface VideoScreenshotView {
  id: string
  section_id: string | null
  place_mention_id?: string | null
  segment_id?: string | null
  planned_timestamp_ms: number
  actual_timestamp_ms: number | null
  image_url: string | null
  selection_reason: string
  caption: string
  content_role: string
  status: 'PLANNED' | 'READY' | 'REJECTED'
}
