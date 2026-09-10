import type {
  ContentView,
  DashboardView,
  JobView,
  MapOverviewView,
  PlaceListView,
  PlacePreview,
  ProfileView,
  RouteDraftView,
  SourceDetailView,
  SourceView,
  StatusView,
  TodoView,
  TranscriptProcessingView,
  LogEventView,
  LogsView,
  ModelProfileView,
  ModelRoutingView,
  AIStagePolicy,
  AIStageView,
  AIUsageView,
  DomainPackView,
  PromptSupplementsView,
  VideoNoteDetail,
  VideoNoteView,
  VideoScreenshotView,
} from './types'

const jsonHeaders = { 'Content-Type': 'application/json' }

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { credentials: 'include', ...init })
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string | { message?: string } } | null
    const detail = typeof payload?.detail === 'string' ? payload.detail : payload?.detail?.message
    throw new Error(detail ?? `请求失败：${response.status}`)
  }
  return response.json() as Promise<T>
}

export type PlaceReview = {
  mention_id: string
  name: string
  raw_name: string
  suggested_name: string
  place_type: string
  reason: string
  confidence: number
  resolution_status: 'REVIEW' | 'UNRESOLVED'
  revision: number
  candidates: Array<{ provider_id: string; name: string; address: string; city: string; district: string; typecode: string; score: number; match_reasons: string[]; match_explanation?: { nearby_context?: string[]; cross_place_context?: string[] } }>
  source_context: { video_note_id: string | null; video_title: string; canonical_url: string; quote: string; segment_ids: string[]; start_ms: number | null; end_ms: number | null; section: { id: string; heading: string; summary: string } | null; transcript_context: Array<{ id: string; text: string; start_ms: number | null; end_ms: number | null; is_evidence: boolean }>; transcript_expired: boolean; screenshot: { id: string; caption: string; image_url: string } | null }
}

export type VideoPlace = {
  id: string
  name: string
  quote: string
  resolution_status: string
  place_id: string | null
  start_ms: number | null
  target_section_id: string | null
  place: { name: string; address: string } | null
  insights: Array<{ insight_type: string; value_text: string; segment_ids: string[]; source_quote: string; target_section_id: string | null }>
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
  job: (id: string) => request<JobView & { steps: Array<{ name: string; status: string; progress: number; error: string | null; started_at: string | null; finished_at: string | null; input: Record<string, unknown>; output: Record<string, unknown> }>; events: LogEventView[] }>(`/api/jobs/${id}`),
  jobAiUsage: (id: string) => request<AIUsageView>(`/api/jobs/${id}/ai-usage`),
  retryJob: (id: string, sourceEventId?: string) => request(`/api/jobs/${id}/retry${sourceEventId ? `?source_event_id=${encodeURIComponent(sourceEventId)}` : ''}`, { method: 'POST' }),
  replayOptions: (id: string) => request<{ step_replay_available: boolean; replay_from_step: string | null; replayable_until: string | null; remaining_seconds: number; reused_steps: string[]; rerun_steps: string[]; reason: string | null; code: string | null; full_replay_available: boolean; full_replay_reason: string | null; login_required: boolean; skip_step_available: boolean; skip_step_reason: string | null }>(`/api/jobs/${id}/replay-options`),
  retryJobFromStep: (id: string, stepName: string) => request(`/api/jobs/${id}/retry-from-step`, { method: 'POST', headers: jsonHeaders, body: JSON.stringify({ step_name: stepName }) }),
  skipJobLoginStep: (id: string) => request(`/api/jobs/${id}/skip-login-step`, { method: 'POST' }),
  retryJobFull: (id: string) => request<{ status: string; job_id: string; replaced_job_id: string; stopped_active_job: boolean }>(`/api/jobs/${id}/retry-full`, { method: 'POST' }),
  cancelJob: (id: string) => request(`/api/jobs/${id}/cancel`, { method: 'POST' }),
  deleteJob: (id: string) => request<{ status: string; id: string }>(`/api/jobs/${id}`, { method: 'DELETE' }),
  content: (type?: string, query?: string) => {
    const params = new URLSearchParams()
    if (type) params.set('content_type', type)
    if (query) params.set('query', query)
    const suffix = params.size ? `?${params.toString()}` : ''
    return request<ContentView[]>(`/api/content${suffix}`)
  },
  contentDetail: (id: string) => request<ContentView & Record<string, unknown>>(`/api/content/${id}`),
  deleteContent: (id: string) => request<{ status: string; id: string }>(`/api/content/${id}`, { method: 'DELETE' }),
  capture: (value: string) => {
    const payload = { text: value }
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
  map: (options: { selectedPlaceId?: string; state?: string; origin?: string; query?: string; placeType?: string; bestMonth?: string; bestSeason?: string; bestTimeSlot?: string; season?: string; month?: string; monthSegment?: string; dayTimeSlot?: string; visitWindowState?: string; recommendationTier?: string; routeId?: string; sourceId?: string; visibility?: 'VISIBLE' | 'HIDDEN' | 'ALL'; bbox?: number[]; zoom?: number } = {}) => {
    const params = new URLSearchParams()
    if (options.selectedPlaceId) params.set('selected_place_id', options.selectedPlaceId)
    if (options.state) params.set('user_state', options.state)
    if (options.origin) params.set('origin', options.origin)
    if (options.query) params.set('query', options.query)
    if (options.placeType) params.set('place_type', options.placeType)
    if (options.bestMonth) params.set('best_month', options.bestMonth)
    if (options.bestSeason) params.set('best_season', options.bestSeason)
    if (options.bestTimeSlot) params.set('best_time_slot', options.bestTimeSlot)
    if (options.season) params.set('season', options.season)
    if (options.month) params.set('month', options.month)
    if (options.monthSegment) params.set('month_segment', options.monthSegment)
    if (options.dayTimeSlot) params.set('day_time_slot', options.dayTimeSlot)
    if (options.visitWindowState) params.set('visit_window_state', options.visitWindowState)
    if (options.recommendationTier) params.set('recommendation_tier', options.recommendationTier)
    if (options.routeId) params.set('route_id', options.routeId)
    if (options.sourceId) params.set('source_id', options.sourceId)
    if (options.visibility) params.set('visibility', options.visibility)
    if (options.bbox) params.set('bbox', options.bbox.join(','))
    if (options.zoom) params.set('zoom', String(options.zoom))
    return request<MapOverviewView>(`/api/travel/map?${params.toString()}`)
  },
  mapBootstrap: () => request<{ js_key: string; security_code: string; security_code_configured: boolean; web_service_configured: boolean; default_viewport: { bbox: number[]; zoom: number }; diagnostics: string[] }>('/api/travel/map/bootstrap'),
  createMapMarker: (payload: { longitude: number; latitude: number; custom_name: string; place_type?: string; summary?: string }) => request<{ marker_id: string; place_id: string }>('/api/travel/map/markers', { method: 'POST', headers: jsonHeaders, body: JSON.stringify(payload) }),
  deleteMapMarker: (markerId: string) => request<{ marker_id: string; visibility: string }>(`/api/travel/map/markers/${markerId}`, { method: 'DELETE' }),
  restoreMapMarker: (markerId: string) => request<{ marker_id: string; visibility: string }>(`/api/travel/map/markers/${markerId}/restore`, { method: 'POST' }),
  placeReviews: (videoNoteId?: string) => request<PlaceReview[]>(`/api/travel/place-reviews${videoNoteId ? `?video_note_id=${encodeURIComponent(videoNoteId)}` : ''}`),
  placeReviewCount: () => request<{ count: number }>('/api/travel/place-reviews/count'),
  confirmPlaceReview: (mentionId: string, poiId: string, expectedRevision: number) => request(`/api/travel/place-mentions/${mentionId}/confirm`, { method: 'POST', headers: jsonHeaders, body: JSON.stringify({ provider: 'AMAP', poi_id: poiId, expected_revision: expectedRevision }) }),
  updatePlaceMention: (mentionId: string, action: 'reject' | 'restore') => request(`/api/travel/place-mentions/${mentionId}/${action}`, { method: 'POST' }),
  searchPlaceReview: (mentionId: string, query: string, expectedRevision: number) => request<{ revision: number; candidates: Array<{ provider_id: string; name: string; address: string; score: number; match_reasons: string[] }> }>(`/api/travel/place-mentions/${mentionId}/poi-search`, { method: 'POST', headers: jsonHeaders, body: JSON.stringify({ query, expected_revision: expectedRevision }) }),
  nearbyPois: (longitude: number, latitude: number) => request<Array<{ provider_id: string; name: string; address: string; longitude: number; latitude: number }>>('/api/travel/map/nearby-pois', { method: 'POST', headers: jsonHeaders, body: JSON.stringify({ longitude, latitude }) }),
  searchMapPois: (query: string) => request<Array<{ provider_id: string; name: string; address: string; city?: string; longitude: number; latitude: number }>>('/api/travel/map/place-search', { method: 'POST', headers: jsonHeaders, body: JSON.stringify({ query, expected_revision: 0 }) }),
  createManualPlace: (payload: { mode: 'CUSTOM' | 'AMAP_POI'; name?: string; place_type: string; longitude: number; latitude: number; note?: string; poi_id?: string }) => request<{ place_id: string }>('/api/travel/places', { method: 'POST', headers: jsonHeaders, body: JSON.stringify(payload) }),
  places: (params = '') => request<PlaceListView>(`/api/travel/places${params ? `?${params}` : ''}`),
  place: (id: string) => request<PlacePreview & Record<string, unknown>>(`/api/travel/places/${id}`),
  placeHistory: (id: string) => request<LogEventView[]>(`/api/travel/places/${id}/history`),
  updatePlaceNote: (id: string, markdown: string, expectedRevision: number) => request(`/api/travel/places/${id}/note`, { method: 'PUT', headers: jsonHeaders, body: JSON.stringify({ markdown, expected_revision: expectedRevision }) }),
  updatePlaceOverlay: (id: string, payload: { display_name: string; override_place_type: string; custom_tags: string[]; expected_revision: number }) => request(`/api/travel/places/${id}/overlay`, { method: 'PATCH', headers: jsonHeaders, body: JSON.stringify(payload) }),
  hidePlaceMarker: (id: string) => request(`/api/travel/places/${id}/marker/hide`, { method: 'POST' }),
  restorePlaceMarker: (id: string) => request(`/api/travel/places/${id}/marker/restore`, { method: 'POST' }),
  deleteManualPlace: (id: string) => request(`/api/travel/places/${id}/user-created`, { method: 'DELETE' }),
  placeDeletionImpact: (id: string) => request<Record<string, number | string | boolean>>(`/api/travel/places/${id}/deletion-impact`),
  hardDeletePlace: (id: string) => request(`/api/travel/places/${id}/hard`, { method: 'DELETE' }),
  hardDeletePlaces: (placeIds: string[]) => request(`/api/travel/places/bulk-hard-delete`, { method: 'DELETE', headers: jsonHeaders, body: JSON.stringify({ place_ids: placeIds }) }),
  bulkPlaces: (payload: { place_ids: string[]; action: string; value?: string }) => request('/api/travel/places/bulk', { method: 'PATCH', headers: jsonHeaders, body: JSON.stringify(payload) }),
  createVisitWindow: (id: string, payload: Record<string, unknown>) => request(`/api/travel/places/${id}/visit-windows`, { method: 'POST', headers: jsonHeaders, body: JSON.stringify(payload) }),
  deleteVisitWindow: (id: string, windowId: string) => request(`/api/travel/places/${id}/visit-windows/${windowId}`, { method: 'DELETE' }),
  createPlaceInsight: (id: string, payload: { insight_type: string; value_key: string; value_text: string }) => request(`/api/travel/places/${id}/insights`, { method: 'POST', headers: jsonHeaders, body: JSON.stringify(payload) }),
  deletePlaceInsight: (placeId: string, insightId: string) => request(`/api/travel/places/${placeId}/insights/${insightId}`, { method: 'DELETE' }),
  restoreManualPlace: (id: string) => request(`/api/travel/places/${id}/user-created/restore`, { method: 'POST' }),
  updatePlace: (id: string, action: string) => request(`/api/travel/places/${id}/${action}`, { method: 'POST' }),
  createPlacePreference: (id: string, eventType: 'LIKE' | 'DISLIKE') => request(`/api/travel/places/${id}/preferences`, { method: 'POST', headers: jsonHeaders, body: JSON.stringify({ event_type: eventType }) }),
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
  updateRouteMetadata: (routeId: string, name: string, city: string) => request<RouteDraftView>(`/api/travel/route-drafts/${routeId}`, { method: 'PATCH', headers: jsonHeaders, body: JSON.stringify({ name, city }) }),
  deleteRoute: (routeId: string) => request<{ id: string; status: string }>(`/api/travel/route-drafts/${routeId}`, { method: 'DELETE' }),
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
  modelProfiles: () => request<ModelProfileView[]>('/api/settings/model-profiles'),
  createModelProfile: (payload: Record<string, unknown>) => request<ModelProfileView>('/api/settings/model-profiles', { method: 'POST', headers: jsonHeaders, body: JSON.stringify(payload) }),
  updateModelProfile: (id: string, payload: Record<string, unknown>) => request<ModelProfileView>(`/api/settings/model-profiles/${id}`, { method: 'PUT', headers: jsonHeaders, body: JSON.stringify(payload) }),
  deleteModelProfile: (id: string) => request<{ status: string; id: string }>(`/api/settings/model-profiles/${id}`, { method: 'DELETE' }),
  testModelProfile: (id: string) => request<{ status: string; message: string }>(`/api/settings/model-profiles/${id}/test`, { method: 'POST' }),
  testModelProfileDraft: (payload: Record<string, unknown>) => request<{ status: string; message: string }>('/api/settings/model-profiles/test-draft', { method: 'POST', headers: jsonHeaders, body: JSON.stringify(payload) }),
  probeModelProfileDraft: (payload: Record<string, unknown>) => request<{ status: string; message: string; probe_results: Record<string, string>; capabilities: string[]; supports_json_mode: boolean }>('/api/settings/model-profiles/probe-draft', { method: 'POST', headers: jsonHeaders, body: JSON.stringify(payload) }),
  probeModelProfile: (id: string) => request<ModelProfileView>(`/api/settings/model-profiles/${id}/probe`, { method: 'POST' }),
  modelRouting: () => request<ModelRoutingView>('/api/settings/model-routing'),
  saveModelRouting: (payload: ModelRoutingView) => request<ModelRoutingView>('/api/settings/model-routing', { method: 'PUT', headers: jsonHeaders, body: JSON.stringify(payload) }),
  aiStages: () => request<AIStageView[]>('/api/ai/stages'),
  aiStagePolicies: () => request<AIStagePolicy[]>('/api/ai/stage-policies'),
  saveAiStagePolicy: (stage: string, payload: AIStagePolicy) => request<AIStagePolicy>(`/api/ai/stage-policies/${stage}`, { method: 'PUT', headers: jsonHeaders, body: JSON.stringify(payload) }),
  resetAiStagePolicy: (stage: string) => request<AIStagePolicy>(`/api/ai/stage-policies/${stage}`, { method: 'DELETE' }),
  domainPacks: () => request<DomainPackView[]>('/api/ai/domain-packs'),
  createDomainPack: (payload: DomainPackView) => request<DomainPackView>('/api/ai/domain-packs', { method: 'POST', headers: jsonHeaders, body: JSON.stringify(payload) }),
  deleteDomainPack: (id: string) => request<{ status: string; id: string }>(`/api/ai/domain-packs/${id}`, { method: 'DELETE' }),
  transcriptProcessing: () => request<TranscriptProcessingView>('/api/settings/transcript-processing'),
  saveTranscriptProcessing: (payload: TranscriptProcessingView) => request<TranscriptProcessingView>('/api/settings/transcript-processing', { method: 'PUT', headers: jsonHeaders, body: JSON.stringify(payload) }),
  promptSupplements: () => request<PromptSupplementsView>('/api/settings/prompt-supplements'),
  savePromptSupplements: (payload: Pick<PromptSupplementsView, 'transcript_correction' | 'video_note_summary' | 'travel_place_extraction'>) => request<PromptSupplementsView>('/api/settings/prompt-supplements', { method: 'PUT', headers: jsonHeaders, body: JSON.stringify(payload) }),
  sources: (query?: string) => request<SourceView[]>(`/api/sources${query ? `?query=${encodeURIComponent(query)}` : ''}`),
  source: (id: string) => request<SourceDetailView>(`/api/sources/${id}`),
  deleteSource: (id: string) => request<{ status: string; id: string }>(`/api/sources/${id}`, { method: 'DELETE' }),
  todos: () => request<TodoView[]>('/api/todos'),
  profile: () => request<ProfileView>('/api/profile'),
  saveProfile: (payload: ProfileView) => request<ProfileView>('/api/profile', { method: 'PUT', headers: jsonHeaders, body: JSON.stringify(payload) }),
  generalSettings: () => request<Record<string, string | number>>('/api/settings/general'),
  saveGeneralSettings: (payload: Record<string, string | number>) => request<Record<string, string | number>>('/api/settings/general', { method: 'PUT', headers: jsonHeaders, body: JSON.stringify(payload) }),
  bilibiliSettings: () => request<{ cookie_saved: boolean; account_name: string | null; verified_at: string | null }>('/api/settings/bilibili'),
  startBilibiliLogin: () => request<{ session_id: string; qr_url: string; expires_at: string; status: string }>('/api/settings/bilibili/login', { method: 'POST' }),
  pollBilibiliLogin: (sessionId: string) => request<{ status: 'WAITING_SCAN' | 'WAITING_CONFIRM' | 'SUCCESS' | 'EXPIRED'; message: string; cookie_saved?: boolean; account_name?: string | null; verified_at?: string | null }>(`/api/settings/bilibili/login/${encodeURIComponent(sessionId)}`),
  amapSettings: () => request<{ js_key: string; security_code_saved: boolean; web_service_key_saved: boolean }>('/api/settings/amap'),
  saveAmapSettings: (payload: { js_key: string; security_code?: string; web_service_key?: string }) => request<{ js_key: string; security_code_saved: boolean; web_service_key_saved: boolean }>('/api/settings/amap', { method: 'PUT', headers: jsonHeaders, body: JSON.stringify(payload) }),
  testAmapSettings: () => request<{ status: string; message: string }>('/api/settings/amap/test', { method: 'POST' }),
  logs: (filters: { levels?: string[]; query?: string; component?: string; eventType?: string; jobId?: string; requestId?: string; entityId?: string; cursor?: string; from?: string; to?: string } = {}) => {
    const params = new URLSearchParams()
    filters.levels?.forEach((level) => params.append('level', level))
    if (filters.query) params.set('query', filters.query)
    if (filters.component) params.set('component', filters.component)
    if (filters.eventType) params.set('event_type', filters.eventType)
    if (filters.jobId) params.set('job_id', filters.jobId)
    if (filters.requestId) params.set('request_id', filters.requestId)
    if (filters.entityId) params.set('entity_id', filters.entityId)
    if (filters.cursor) params.set('cursor', filters.cursor)
    if (filters.from) params.set('from', filters.from)
    if (filters.to) params.set('to', filters.to)
    return request<LogsView>(`/api/logs${params.size ? `?${params}` : ''}`)
  },
  videoNotes: (query?: string) => request<VideoNoteView[]>(`/api/video-notes${query ? `?query=${encodeURIComponent(query)}` : ''}`),
  videoNote: (id: string) => request<VideoNoteDetail>(`/api/video-notes/${id}`),
  videoTranscript: (id: string) => request<{ text: string; correction_status: string; correction_coverage: number; segments: Array<{ id: string; text: string; raw_text: string; corrected_text: string; correction_status: string; start_ms: number; end_ms: number }> }>(`/api/video-notes/${id}/transcript`),
  videoTranscriptExportUrl: (id: string, version: 'raw' | 'corrected' = 'corrected') => `/api/video-notes/${id}/transcript/export?version=${version}`,
  videoScreenshots: (id: string) => request<VideoScreenshotView[]>(`/api/video-notes/${id}/screenshots`),
  videoPlaces: (id: string) => request<VideoPlace[]>(`/api/video-notes/${id}/places`),
  regenerateVideoNote: (id: string) => request<{ job_id: string }>(`/api/video-notes/${id}/regenerate`, { method: 'POST' }),
  deleteVideoNote: (id: string) => request<{ status: string }>(`/api/video-notes/${id}`, { method: 'DELETE' }),
}
