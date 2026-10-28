export type JobStatus = 'QUEUED' | 'RUNNING' | 'NEEDS_USER' | 'COMPLETED' | 'PARTIAL_SUCCESS' | 'FAILED' | 'CANCELLED'
export type ContentType = 'RECRUITMENT' | 'TRAVEL' | 'VIDEO_NOTE' | 'UNSUPPORTED'
export type UserState = 'DISCOVERED' | 'SAVED' | 'PLANNED' | 'VISITED' | 'DISMISSED'

export interface JobView {
  id: string
  job_type: string
  asr_provider?: ASRProvider | null
  status: JobStatus
  current_step: string
  progress: number
  title: string
  source_url?: string | null
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
  active_attempt: ActiveAttemptView | null
}

export interface ActiveAttemptView {
  id: string
  stage: string | null
  step: string | null
  provider: string
  model: string
  route: string | null
  chunk_index: number | null
  chunk_count: number | null
  split_path: string | null
  started_at: string
  updated_at: string
  deadline_at: string | null
  elapsed_seconds: number
  timeout_seconds: number | null
  status: string
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

export type ASRProvider = 'WHISPER_CPP' | 'QWEN3_ASR'
export interface ASRSettingsView { default_provider: ASRProvider }

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
  attempts: LogAttemptView[]
  next_cursor: string | null
  server_time: string
  applied_filters: Record<string, unknown>
}

export interface LogAttemptView {
  id: string
  created_at: string
  updated_at: string
  capability: string
  operation: string
  provider: string
  model: string
  route: string | null
  attempt: number | null
  timeout_seconds: number | null
  deadline_at: string | null
  stage: string | null
  step: string | null
  split_path: string | null
  recovery: string | null
  status: string
  duration_ms: number | null
  elapsed_seconds: number
  input_chars: number | null
  chunk_index: number | null
  chunk_count: number | null
  status_code: number | null
  error_code: string | null
  error_message: string | null
  provider_error: Record<string, unknown> | null
}

export interface InterfaceCapabilities {
  model: string
  base_url: string
  sampled_at: string
  source: string
  version: string
  system: 'SUPPORTED' | 'UNSUPPORTED' | 'UNKNOWN'
  history: 'SUPPORTED' | 'UNSUPPORTED' | 'UNKNOWN'
  json_object: 'SUPPORTED' | 'UNSUPPORTED' | 'UNKNOWN'
  usage: 'SUPPORTED' | 'UNSUPPORTED' | 'UNKNOWN'
  output: { support: 'SUPPORTED' | 'UNSUPPORTED' | 'UNKNOWN'; minimum: number | null; maximum: number | null }
  temperature: { support: 'SUPPORTED' | 'UNSUPPORTED' | 'UNKNOWN'; minimum: number | null; maximum: number | null }
  limiting_layer: string
}

export interface ModelProfileView {
  interface_probe?: InterfaceProbe | null
  id: string
  name: string
  provider: string
  base_url: string
  model: string
  connection_type: 'DIRECT' | 'LOCAL_ROUTER'
  interface_capabilities: InterfaceCapabilities | null
  timeout_seconds: number
  reliability_mode: 'DIRECT' | 'STANDARD' | 'GUARDED' | 'FREE_TIER'
  request_interval_seconds: number | null
  max_concurrency: number | null
  retry_count: number | null
  json_retry_count: number | null
  rate_limit_rpm: number | null
  circuit_breaker_enabled: boolean | null
  circuit_breaker_threshold: number | null
  circuit_breaker_cooldown_seconds: number | null
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
  max_output_tokens: number | null
  temperature?: number | null
  quality_tier: 'FAST' | 'MAIN' | 'STRONG' | 'SPECIALIST'
  specialties: string[]
  enabled: boolean
  probe_results: Record<string, string>
}

export interface InterfaceProbe {
  status: string
  reason: string
  error_code: string | null
  tested_at?: string
  model?: string
  interface_fingerprint?: string | null
}

export interface ModelTestView {
  id: string
  profile_id: string
  name: string
  mode: 'TEST' | 'PROBE' | 'BOTH' | 'INTERFACE'
  status: string
  phase: string
  progress: number
  error: string | null
  error_code: string | null
  results: { TEST?: { status: string; message: string }; PROBE?: { probe_results: Record<string, string>; interface_probe?: InterfaceProbe | null }; INTERFACE?: { probe_results: Record<string, string>; interface_probe: InterfaceProbe } }
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
  wall_time_seconds: number | null
  max_attempts: number | null
  retry_count: number | null
  json_retry_count: number | null
  confidence_threshold: number | null
  escalation_threshold: number | null
  context_strategy: string | null
  chunk_size: number | null
  batch_size?: number | null
  neighbor_segments: number | null
  domain: string | null
  domain_pack_ids: string[]
  cache_enabled: boolean | null
  force_regenerate: boolean
  allow_unverified_model: boolean
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
  call_details?: Array<{ id: string; stage: string; status: string; model: string; attempt_state?: string | null;
    parse_quality: string | null; execution_path: string | null; usage_source: string;
    queue_ms: number | null; provider_ms: number | null; duration_ms: number | null;
    error_code: string | null; rejected_items: number | null; acceptance: string | null }>
  total: AIUsageBucket
  local: AIUsageBucket
  remote: AIUsageBucket
  by_stage: Record<string, AIUsageBucket>
  by_model: Record<string, AIUsageBucket>
  cache: { hits: number; saved_prompt_tokens?: number }
  retry?: AIUsageBucket
  fallback?: AIUsageBucket
  waste?: AIUsageBucket & { repeated_input_tokens: number }
  automation?: { decisions: Array<Record<string, unknown>>; estimated_tokens_saved: number }
  ratios?: { cache_hit_ratio: number; retry_token_ratio: number; fallback_token_ratio: number; repeated_input_ratio: number }
  budget?: { status: 'EXPECTED' | 'WARNING' | 'HARD_LIMIT'; expected_prompt_tokens?: number; expected_completion_tokens?: number; expected_total_calls?: number; projected_prompt_tokens?: number }
  anomalies?: Array<Record<string, unknown>>
  escalations: number
}

export interface AIUsageBucket {
  calls: number
  attempt_count?: number
  input_tokens: number
  output_tokens: number
  estimated_input_tokens?: number
  estimated_output_tokens?: number
  estimated_input_calls?: number
  estimated_output_calls?: number
  unknown_input_calls?: number
  unknown_output_calls?: number
  cached_tokens: number
  input_chars?: number
  cache_hit_count?: number
  retry_count?: number
  fallback_count?: number
  duration_ms: number
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
  recommendation_summary?: Recommendation
  id: string
  name: string
  address: string
  place_type: string
  summary: string
  user_state: UserState
  observations: PlaceObservation[]
}

export interface TravelBriefData {
  access?: string[]
  source_label?: string
  timing?: string
  conditions?: string[]
  highlights?: string[]
  warnings?: string[]
  inherited?: boolean
}

export interface MapMarker {
  entity_type?: 'PLACE' | 'DESTINATION'
  recommendation_summary?: Recommendation
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
  timing_status?: string
  travel_brief?: TravelBriefData
  source_notes?: Array<{ note_id: string; version_id: string; title: string }>
  recording_reasons?: string[]
  visit_window_evidence?: Array<{ source_kind: string; source_text: string; source_id?: string; segment_ids?: string[] }>
  recommendation?: { tier?: string; label?: string; reasons?: Array<{ kind?: string; text: string; trace?: { summary?: string } }> }
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
export interface PlaceVisitWindow { valid_as_time?: boolean; id: string; source_id?: string | null; source_kind?: string; season: string | null; month: number | null; month_segment: string | null; day_time_slot: string | null; period_type: string; suitability: string; source_text: string; segment_ids: string[]; provenance: string; confidence: number; status: string }

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
  platform: 'BILIBILI' | 'LOCAL' | 'YOUTUBE'
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
  model_provider: string
  model_name: string
  overview: string
  search_match?: string
  search_snippet?: string
  updated_at: string
  place_summary: { total: number; confirmed: number }
}

export type VideoNoteSection = { id: string; heading: string; section_kind: 'PLACE' | 'AREA' | 'ROUTE' | 'SUPPLEMENTAL'; thesis: string; summary: string; bullets: string[]; anchor_id: string; body_markdown: string; segment_ids: string[]; place_mention_ids: string[]; evidence_quotes: string[]; start_ms: number | null; end_ms: number | null } & { source_section_ids?: string[]; source_ranges?: Array<{ start_ms: number; end_ms: number | null }> }

export interface VideoNoteDetail extends VideoNoteView {
  markdown: string
  warnings: string[]
  needs_regeneration: boolean
  sections: VideoNoteSection[]
  reading_sections?: VideoNoteSection[]
  reading_overview?: string
  reading_organization?: string
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

export interface StageLimitsPreview {
  limits_policy_version: number
  request_timeouts: Array<{profile_id: string; name: string; seconds: number; source: string; initial_ceiling_seconds: number}>
  wall_time_seconds: number | null
  job_wall_time_seconds: number
  chunk_chars: number | null
  batch_size: number | null
}

export interface RecommendationStatement { statement_id: string; quote: string; speaker: string; scope: string; segment_ids: string[] }
export interface Recommendation { status: string; review_required?: boolean; source_opinions?: Array<{ mention_id?: string; assessment_status?: string; note_id?: string; title?: string; statements?: RecommendationStatement[] }> }
export interface LogPolicy { version: number; compress: boolean; compression_delay_hours: number; retention_days: number; volume_bytes: number; capacity_bytes: number; bootstrap_retention_days: number; bootstrap_capacity_bytes: number; low_space_bytes: number }
export interface LogPreview { token: string; delete_count: number; delete_bytes: number; oldest_closed_at: number | null; archived_bytes: number }
export interface StorageStatus { root: string; generation: number; configured_generation: number; registered: boolean; plan: { stage?: string; error?: string; target?: string; required_bytes?: number; free_bytes?: number; categories?: Record<string, number> }; state: { stage?: string }; policy: LogPolicy; handler_versions: number[]; exceptions: string[]; log_summary: LogPreview; maintenance: { at?: number; compressed?: number; deleted?: number; errors?: string[] } }

export interface RouteGuide {
  id: string; guide_id: string; name: string; note_id: string; version_id: string; source_title: string; evidence_url: string
  mode: string; sequence_kind: string; display_notice: string; review_status: string
  stops: Array<{ raw_name: string; place_id: string | null; review_status: string }>
  evidence: { quote: string; segment_ids: string[] }; conditions: Array<{ subject: string; quote: string }>
}
