import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight, Download, EyeOff, ListOrdered, MapPinCheck, RotateCcw, Search, Trash2 } from 'lucide-react'
import { useCallback, useDeferredValue, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../../lib/api'
import { FilterMenu } from '../../components/ui/FilterMenu'
import { MapCanvas } from './MapCanvas'
import { labelPlaceType, seasonLabels, segmentLabels, timeLabels } from './placeLabels'

const placeTypes = ['SCENIC_AREA', 'RESTAURANT', 'NEIGHBORHOOD', 'MUSEUM', 'PARK', 'HOTEL', 'TRANSPORT', 'LANDMARK']

export function MapOverviewPage() {
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState<string>()
  const [state, setState] = useState('')
  const [query, setQuery] = useState('')
  const [placeType, setPlaceType] = useState('')
  const [season, setSeason] = useState('')
  const [month, setMonth] = useState('')
  const [monthSegment, setMonthSegment] = useState('')
  const [dayTimeSlot, setDayTimeSlot] = useState('')
  const [visitWindowState, setVisitWindowState] = useState('')
  const [recommendationTier, setRecommendationTier] = useState('')
  const [visibility] = useState<'VISIBLE' | 'HIDDEN' | 'ALL'>('VISIBLE')
  const [routeId, setRouteId] = useState('')
  const [poiQuery, setPoiQuery] = useState('')
  const [chinaReset, setChinaReset] = useState(0)
  const [deletedPlaceId, setDeletedPlaceId] = useState<string>()
  const [addOpen, setAddOpen] = useState(false)
  const [viewport, setViewport] = useState(() => {
    const stored = sessionStorage.getItem('zhijian-map-viewport')
    return stored ? JSON.parse(stored) as { bbox: number[]; zoom: number } : { bbox: [73.5, 18, 135.1, 53.6], zoom: 4 }
  })
  const deferredQuery = useDeferredValue(query)
  const persistViewport = useCallback((next: { bbox: number[]; zoom: number }) => {
    if (next.bbox.length !== 4 || next.bbox.some((value) => !Number.isFinite(value)) || !Number.isFinite(next.zoom)) return
    setViewport((current) => {
      const unchanged = Math.abs(current.zoom - next.zoom) < .05 && current.bbox.every((value, index) => Math.abs(value - next.bbox[index]) < .01)
      if (unchanged) return current
      sessionStorage.setItem('zhijian-map-viewport', JSON.stringify(next))
      return next
    })
  }, [])
  const overview = useQuery({ queryKey: ['map', selectedId, state, deferredQuery, placeType, season, month, monthSegment, dayTimeSlot, visitWindowState, recommendationTier, visibility, routeId, viewport], queryFn: () => api.map({ selectedPlaceId: selectedId, state, query: deferredQuery, placeType, season, month, monthSegment, dayTimeSlot, visitWindowState, recommendationTier, visibility, routeId, bbox: viewport.bbox, zoom: viewport.zoom }) })
  const routes = useQuery({ queryKey: ['routes'], queryFn: api.routes })
  const reviewCount = useQuery({ queryKey: ['place-review-count'], queryFn: api.placeReviewCount })
  const selected = overview.data?.markers.find((item) => item.id === overview.data?.selected_place_id)
  const markerIds = useMemo(() => overview.data?.markers.map((item) => item.id) ?? [], [overview.data?.markers])
  const activeIndex = Math.max(0, markerIds.indexOf(overview.data?.selected_place_id ?? ''))
  const route = routes.data?.find((item) => item.id === routeId)
  useEffect(() => { if (routeId && routes.data && !route) setRouteId('') }, [route, routeId, routes.data])
  useEffect(() => { const cancel = (event: KeyboardEvent) => { if (event.key === 'Escape') { setAddOpen(false); setPoiQuery('') } }; window.addEventListener('keydown', cancel); return () => window.removeEventListener('keydown', cancel) }, [])
  const addToRoute = useMutation({
    mutationFn: async () => {
      if (!selected || !route) return
      const ids = [...route.places.map((place) => place.id), selected.id]
      await api.updateRoute(route.id, [...new Set(ids)])
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['routes'] })
      void queryClient.invalidateQueries({ queryKey: ['map'] })
    },
  })
  const quickCreateRoute = useMutation({
    mutationFn: async () => {
      if (!selected) return null
      const created = await api.createRoute('新的路线清单', '')
      await api.updateRoute(created.id, [selected.id])
      return created
    },
    onSuccess: (created) => {
      if (created) setRouteId(created.id)
      void queryClient.invalidateQueries({ queryKey: ['routes'] })
    },
  })
  const hideMarker = useMutation({ mutationFn: (id: string) => api.hidePlaceMarker(id), onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['map'] }) })
  const restoreMarker = useMutation({ mutationFn: (id: string) => api.restorePlaceMarker(id), onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['map'] }) })
  const deleteManual = useMutation({ mutationFn: (id: string) => api.deleteManualPlace(id), onSuccess: (_value, placeId) => { setDeletedPlaceId(placeId); setSelectedId(undefined); void queryClient.invalidateQueries({ queryKey: ['map'] }) } })
  const restoreManual = useMutation({ mutationFn: (id: string) => api.restoreManualPlace(id), onSuccess: () => { setDeletedPlaceId(undefined); void queryClient.invalidateQueries({ queryKey: ['map'] }) } })
  const searchPois = useQuery({ queryKey: ['map-poi-search', poiQuery], queryFn: () => api.searchMapPois(poiQuery), enabled: poiQuery.trim().length > 1 })
  const addPlace = useMutation({ mutationFn: api.createManualPlace, onSuccess: (value) => { setSelectedId(value.place_id); setAddOpen(false); setPoiQuery(''); void queryClient.invalidateQueries({ queryKey: ['map'] }); void queryClient.invalidateQueries({ queryKey: ['places'] }) } })

  function moveSelection(offset: number) {
    if (!markerIds.length) return
    const next = (activeIndex + offset + markerIds.length) % markerIds.length
    setSelectedId(markerIds[next])
  }

  function resetChinaView() {
    const next = { bbox: [73.5, 18, 135.1, 53.6], zoom: 4 }
    setViewport(next)
    sessionStorage.setItem('zhijian-map-viewport', JSON.stringify(next))
    setSelectedId(undefined)
    setChinaReset((value) => value + 1)
  }

  async function exportGeoJson() {
    const response = await fetch('/api/travel/export?format=geojson', { method: 'POST', credentials: 'include' })
    if (!response.ok) return
    const url = URL.createObjectURL(await response.blob())
    const link = document.createElement('a')
    link.href = url
    link.download = 'zhijian-places.geojson'
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="map-page">
      <header className="map-toolbar"><div className="map-toolbar__search"><Search /><input value={query} onChange={(event) => { setQuery(event.target.value); setSelectedId(undefined) }} placeholder="搜索地点或地址" /></div><div className="map-toolbar__filters"><FilterMenu label="状态" value={state} onChange={setState} options={[{ value: '', label: '全部' }, { value: 'SAVED', label: '想去' }, { value: 'PLANNED', label: '已计划' }, { value: 'VISITED', label: '去过' }, { value: 'DISMISSED', label: '不感兴趣' }]} /><FilterMenu label="类型" value={placeType} onChange={setPlaceType} options={[{ value: '', label: '全部' }, ...placeTypes.map((value) => ({ value, label: labelPlaceType(value) }))]} /><FilterMenu label="季节" value={season} onChange={setSeason} options={[{ value: '', label: '全部' }, ...Object.entries(seasonLabels).map(([value, label]) => ({ value, label }))]} /><FilterMenu label="月份" value={month} onChange={setMonth} options={[{ value: '', label: '全部' }, ...Array.from({ length: 12 }, (_, index) => ({ value: String(index + 1), label: `${index + 1}月` }))]} /><FilterMenu label="适宜度" value={visitWindowState} onChange={setVisitWindowState} options={[{ value: '', label: '全部' }, { value: 'BEST', label: '本月最佳' }, { value: 'GOOD', label: '本月适合' }, { value: 'CAUTION', label: '需注意' }, { value: 'CLOSED', label: '关闭/受限' }, { value: 'UNKNOWN', label: '时间未知' }]} /><FilterMenu label="推荐" value={recommendationTier} onChange={setRecommendationTier} options={[{ value: '', label: '全部地点' }, { value: 'PRIORITY', label: '优先关注' }, { value: 'WORTH_CONSIDERING', label: '值得考虑' }, { value: 'GENERAL', label: '一般' }, { value: 'MISMATCH', label: '不符合偏好' }]} /><FilterMenu label="旬段" value={monthSegment} onChange={setMonthSegment} options={[{ value: '', label: '全部' }, ...Object.entries(segmentLabels).map(([value, label]) => ({ value, label }))]} /><FilterMenu label="时段" value={dayTimeSlot} onChange={setDayTimeSlot} options={[{ value: '', label: '全部' }, ...Object.entries(timeLabels).map(([value, label]) => ({ value, label }))]} /><FilterMenu label="路线" value={routeId} onChange={setRouteId} options={[{ value: '', label: '全部路线' }, ...(routes.data ?? []).map((item) => ({ value: item.id, label: item.name }))]} /></div><div className="map-toolbar__actions"><Link className="button button--outline" to="/places">地点管理</Link><Link className={`icon-button map-review-button${reviewCount.data?.count ? ' has-pending' : ''}`} to="/place-reviews" aria-label="待确认地点"><MapPinCheck />{reviewCount.data?.count ? <b>{reviewCount.data.count}</b> : null}</Link><button className="icon-button" aria-label="导出地点 GeoJSON" onClick={() => void exportGeoJson()}><Download /></button><button className="icon-button" aria-label="回到全国视野" onClick={resetChinaView}><RotateCcw /></button></div></header>
      <div className="map-page__stage">
        <MapCanvas
          markers={overview.data?.markers ?? []}
          selectedId={overview.data?.selected_place_id ?? null}
          onSelect={setSelectedId}
          viewport={viewport}
          onViewportChange={persistViewport}
          onStartPlaceSearch={() => { setAddOpen(true); setPoiQuery('') }}
          chinaReset={chinaReset}
        />
        <Link className="route-badge" to="/routes"><ListOrdered />路线清单 <strong>{routes.data?.reduce((count, item) => count + item.places.length, 0) ?? 0}</strong></Link>
      </div>
      {deletedPlaceId && <div className="map-delete-toast" role="status">用户创建地点已移除 <button onClick={() => restoreManual.mutate(deletedPlaceId)} disabled={restoreManual.isPending}>恢复</button></div>}
      {addOpen && <section className="map-add-flow"><header><h2>搜索并确认地点</h2><p>使用高德全国 POI 搜索；确认前不会创建 Marker。</p><input autoFocus value={poiQuery} onChange={(event) => setPoiQuery(event.target.value)} placeholder="输入地点名称，例如：天安门" /></header><div className="map-add-results">{poiQuery.trim().length < 2 ? <p>请输入至少两个字开始搜索。</p> : null}{searchPois.isFetching ? <p>正在搜索地点…</p> : null}{searchPois.isError ? <p role="alert">搜索失败，请检查高德 Web 服务配置。</p> : null}{poiQuery.trim().length >= 2 && !searchPois.isFetching && !searchPois.data?.length ? <p>没有找到匹配地点，请尝试完整名称。</p> : null}{searchPois.data?.map((poi) => <button key={poi.provider_id} onClick={() => addPlace.mutate({ mode: 'AMAP_POI', poi_id: poi.provider_id, place_type: 'LANDMARK', longitude: poi.longitude, latitude: poi.latitude })}><strong>{poi.name}</strong><span>{[poi.city, poi.address].filter(Boolean).join(' · ')}</span></button>)}</div><footer><button className="text-action" onClick={() => { setAddOpen(false); setPoiQuery('') }}>取消</button></footer></section>}
      {selected && <section className="place-preview">
        <div className="place-preview__handle" />
        <div className="place-preview__nav"><span><strong>{activeIndex + 1}</strong> / {markerIds.length}</span><div><button onClick={() => moveSelection(-1)} aria-label="上一地点"><ChevronLeft /></button><button onClick={() => moveSelection(1)} aria-label="下一地点"><ChevronRight /></button></div></div>
        <h2>{selected.name}</h2><p>{selected.address}</p><p className="place-preview__summary">{String(selected.brief?.feature ?? selected.summary)}</p><p className="place-preview__meta">{selected.visit_window_summary ?? '时间未知'} · {selected.visit_window_reason ?? '尚无可追溯的适宜时间证据'}</p>{selected.recommendation?.label ? <p className="place-preview__meta">{selected.recommendation.label} · {selected.recommendation.reasons?.[0]?.text}</p> : null}<p className="place-preview__meta">{selected.origin === 'USER_CREATED' ? '用户创建地点' : '视频地点'} · {selected.source_count} 个来源</p>
        <div className="place-preview__route">{routes.data?.length ? <><FilterMenu label="加入路线" value={routeId} onChange={setRouteId} options={[{ value: '', label: '选择路线' }, ...routes.data.map((item) => ({ value: item.id, label: item.name }))]} /><button className="button button--outline" onClick={() => addToRoute.mutate()} disabled={!route || route.places.some((place) => place.id === selected.id) || addToRoute.isPending}>加入路线</button></> : <button className="button button--outline" onClick={() => quickCreateRoute.mutate()} disabled={quickCreateRoute.isPending}>新建路线并加入</button>}</div>
        <div className="place-preview__actions">{selected.visibility === 'HIDDEN' ? <button className="button button--outline" onClick={() => restoreMarker.mutate(selected.id)}>恢复显示</button> : <button className="button button--outline" onClick={() => hideMarker.mutate(selected.id)}><EyeOff />隐藏</button>}{selected.origin === 'USER_CREATED' && <button className="button button--outline" onClick={() => deleteManual.mutate(selected.id)}><Trash2 />删除地点</button>}<Link className="button button--primary" to={`/places/${selected.id}`} state={{ fromMap: true }}>编辑地点</Link></div>
      </section>}
    </div>
  )
}
