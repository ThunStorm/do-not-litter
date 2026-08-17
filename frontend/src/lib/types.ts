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
