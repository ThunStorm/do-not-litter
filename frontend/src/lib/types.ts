export type JobStatus = 'QUEUED' | 'RUNNING' | 'NEEDS_USER' | 'COMPLETED' | 'FAILED' | 'CANCELLED'
export type ContentType = 'RECRUITMENT' | 'TRAVEL' | 'UNSUPPORTED'
export type UserState = 'DISCOVERED' | 'SAVED' | 'PLANNED' | 'VISITED' | 'DISMISSED'

export interface JobView {
  id: string
  job_type: string
  status: JobStatus
  current_step: string
  progress: number
  title: string
  error: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
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
  detail: Record<string, unknown>
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
  name: string
  place_type: string
  latitude: number
  longitude: number
  user_state: UserState
  summary: string
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
}

export interface RouteDraftView {
  id: string
  name: string
  city: string
  status: string
  places: PlacePreview[]
}
