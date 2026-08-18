import type {
  ContentView,
  DashboardView,
  JobView,
  MapOverviewView,
  PlacePreview,
  ProfileView,
  RouteDraftView,
  SourceView,
  StatusView,
  TodoView,
  LogEventView,
} from './types'

const jsonHeaders = { 'Content-Type': 'application/json' }

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { credentials: 'include', ...init })
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new Error(payload?.detail ?? `请求失败：${response.status}`)
  }
  return response.json() as Promise<T>
}

export const api = {
  createSession: (token: string) =>
    request<{ status: string }>('/api/auth/session', {
      method: 'POST',
      headers: jsonHeaders,
      body: JSON.stringify({ token, client_label: navigator.userAgent.slice(0, 180) }),
    }),
  dashboard: () => request<DashboardView>('/api/dashboard'),
  status: () => request<StatusView>('/api/status'),
  lanToken: () => request<{ token: string; display: string; digits: number }>('/api/admin/lan-token'),
  rotateLanToken: () => request<{ token: string; sessions_revoked: boolean }>('/api/admin/lan-token/rotate', { method: 'POST' }),
  jobs: () => request<JobView[]>('/api/jobs'),
  job: (id: string) => request<JobView & { steps: Array<Record<string, unknown>> }>(`/api/jobs/${id}`),
  retryJob: (id: string) => request(`/api/jobs/${id}/retry`, { method: 'POST' }),
  cancelJob: (id: string) => request(`/api/jobs/${id}/cancel`, { method: 'POST' }),
  content: (type?: string, query?: string) => {
    const params = new URLSearchParams()
    if (type) params.set('content_type', type)
    if (query) params.set('query', query)
    const suffix = params.size ? `?${params.toString()}` : ''
    return request<ContentView[]>(`/api/content${suffix}`)
  },
  contentDetail: (id: string) => request<ContentView & Record<string, unknown>>(`/api/content/${id}`),
  capture: (value: string) => {
    const payload = value.startsWith('http') ? { url: value } : { text: value }
    return request<{ job_id: string }>('/api/capture', {
      method: 'POST',
      headers: jsonHeaders,
      body: JSON.stringify(payload),
    })
  },
  captureFile: (file: File) => {
    const body = new FormData()
    body.append('upload', file)
    return request<{ job_id: string }>('/api/capture/file', { method: 'POST', body })
  },
  map: (selectedPlaceId?: string, state?: string, query?: string, district?: string) => {
    const params = new URLSearchParams({ city: '厦门市' })
    if (selectedPlaceId) params.set('selected_place_id', selectedPlaceId)
    if (state) params.set('user_state', state)
    if (query) params.set('query', query)
    if (district) params.set('district', district)
    return request<MapOverviewView>(`/api/travel/map?${params.toString()}`)
  },
  place: (id: string) => request<PlacePreview & Record<string, unknown>>(`/api/travel/places/${id}`),
  updatePlace: (id: string, action: string) => request(`/api/travel/places/${id}/${action}`, { method: 'POST' }),
  routes: () => request<RouteDraftView[]>('/api/travel/route-drafts'),
  createRoute: (name: string, city: string) => request<RouteDraftView>('/api/travel/route-drafts', {
    method: 'POST', headers: jsonHeaders, body: JSON.stringify({ name, city, place_ids: [] }),
  }),
  updateRoute: (routeId: string, placeIds: string[]) =>
    request<RouteDraftView>(`/api/travel/route-drafts/${routeId}/items`, {
      method: 'PUT',
      headers: jsonHeaders,
      body: JSON.stringify({ place_ids: placeIds }),
    }),
  providers: () => request<Record<string, Record<string, string>>>('/api/settings/providers'),
  saveProvider: (role: string, payload: Record<string, string>) =>
    request<Record<string, string | boolean>>(`/api/settings/providers/${role}`, {
      method: 'PUT',
      headers: jsonHeaders,
      body: JSON.stringify(payload),
    }),
  testProvider: (role: string, payload: Record<string, string>) =>
    request<{ status: string; message: string }>(`/api/settings/providers/${role}/test`, {
      method: 'POST',
      headers: jsonHeaders,
      body: JSON.stringify(payload),
    }),
  sources: (query?: string) => request<SourceView[]>(`/api/sources${query ? `?query=${encodeURIComponent(query)}` : ''}`),
  source: (id: string) => request<Record<string, unknown>>(`/api/sources/${id}`),
  todos: () => request<TodoView[]>('/api/todos'),
  profile: () => request<ProfileView>('/api/profile'),
  saveProfile: (payload: ProfileView) => request<ProfileView>('/api/profile', { method: 'PUT', headers: jsonHeaders, body: JSON.stringify(payload) }),
  generalSettings: () => request<Record<string, string | number>>('/api/settings/general'),
  saveGeneralSettings: (payload: Record<string, string | number>) => request<Record<string, string | number>>('/api/settings/general', { method: 'PUT', headers: jsonHeaders, body: JSON.stringify(payload) }),
  logs: (level?: string, query?: string) => {
    const params = new URLSearchParams()
    if (level) params.set('level', level)
    if (query) params.set('query', query)
    return request<LogEventView[]>(`/api/logs${params.size ? `?${params}` : ''}`)
  },
}
