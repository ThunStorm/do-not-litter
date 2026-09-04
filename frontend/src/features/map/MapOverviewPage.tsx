import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight, Download, EyeOff, ListOrdered, MapPinCheck, RotateCcw, Search, Trash2 } from 'lucide-react'
import { useCallback, useDeferredValue, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../../lib/api'
import { MapCanvas } from './MapCanvas'

const placeTypes = ['SCENIC_AREA', 'RESTAURANT', 'NEIGHBORHOOD', 'MUSEUM', 'PARK', 'HOTEL', 'TRANSPORT', 'LANDMARK']

export function MapOverviewPage() {
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState<string>()
  const [state, setState] = useState('')
  const [searchOpen, setSearchOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [placeType, setPlaceType] = useState('')
  const [bestMonth, setBestMonth] = useState('')
  const [bestTimeSlot, setBestTimeSlot] = useState('')
  const [visibility, setVisibility] = useState<'VISIBLE' | 'HIDDEN' | 'ALL'>('VISIBLE')
  const [routeId, setRouteId] = useState('')
  const [poiQuery, setPoiQuery] = useState('')
  const [chinaReset, setChinaReset] = useState(0)
  const [deletedPlaceId, setDeletedPlaceId] = useState<string>()
  const [draft, setDraft] = useState<{ longitude: number; latitude: number } | null>(null)
  const [customName, setCustomName] = useState('')
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
  const overview = useQuery({ queryKey: ['map', selectedId, state, deferredQuery, placeType, bestMonth, bestTimeSlot, visibility, routeId, viewport], queryFn: () => api.map({ selectedPlaceId: selectedId, state, query: deferredQuery, placeType, bestMonth, bestTimeSlot, visibility, routeId, bbox: viewport.bbox, zoom: viewport.zoom }) })
  const routes = useQuery({ queryKey: ['routes'], queryFn: api.routes })
  const reviewCount = useQuery({ queryKey: ['place-review-count'], queryFn: api.placeReviewCount })
  const selected = overview.data?.markers.find((item) => item.id === overview.data?.selected_place_id)
  const markerIds = useMemo(() => overview.data?.markers.map((item) => item.id) ?? [], [overview.data?.markers])
  const activeIndex = Math.max(0, markerIds.indexOf(overview.data?.selected_place_id ?? ''))
  const route = routes.data?.find((item) => item.id === routeId)
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
  const nearby = useQuery({ queryKey: ['nearby-pois', draft], queryFn: () => api.nearbyPois(draft!.longitude, draft!.latitude), enabled: Boolean(draft) })
  const searchPois = useQuery({ queryKey: ['map-poi-search', poiQuery], queryFn: () => api.searchMapPois(poiQuery), enabled: poiQuery.trim().length > 1 })
  const addPlace = useMutation({ mutationFn: api.createManualPlace, onSuccess: (value) => { setSelectedId(value.place_id); setDraft(null); setCustomName(''); void queryClient.invalidateQueries({ queryKey: ['map'] }) } })

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
      <header className="map-page__header">
        <div><h1>旅行地图</h1><p>全国地点 · 当前视野 {overview.data?.visible_places ?? 0}/{overview.data?.total_places ?? 0}</p></div>
        <div className="map-page__actions"><Link className={`icon-button map-review-button${reviewCount.data?.count ? ' has-pending' : ''}`} to="/place-reviews" aria-label={reviewCount.data?.count ? `待确认地点，${reviewCount.data.count} 项` : '暂无待确认地点'}><MapPinCheck />{reviewCount.data?.count ? <b>{reviewCount.data.count}</b> : null}</Link><button className="icon-button" aria-label="导出地点 GeoJSON" onClick={() => void exportGeoJson()}><Download /></button><button className="icon-button" aria-label="回到全国视野" onClick={resetChinaView}><RotateCcw /></button><button className="icon-button" aria-label="搜索地点" onClick={() => setSearchOpen((value) => !value)}><Search /></button></div>
      </header>
      {searchOpen && <div className="map-search"><Search /><input autoFocus value={query} onChange={(event) => { setQuery(event.target.value); setSelectedId(undefined) }} placeholder="搜索地点或地址" /><span>{overview.data?.visible_places ?? 0} 个结果</span></div>}
      <div className="map-filters">
        <select value={state} aria-label="地点状态" onChange={(event) => setState(event.target.value)}><option value="">状态：全部</option><option value="SAVED">想去</option><option value="PLANNED">已计划</option><option value="VISITED">去过</option><option value="DISMISSED">不感兴趣</option></select>
        <select value={placeType} aria-label="地点类型" onChange={(event) => setPlaceType(event.target.value)}><option value="">类型：全部</option>{placeTypes.map((value) => <option key={value} value={value}>{value}</option>)}</select>
        <select value={bestMonth} aria-label="适宜月份" onChange={(event) => setBestMonth(event.target.value)}><option value="">适宜时间</option>{Array.from({ length: 12 }, (_, index) => <option key={index} value={String(index + 1)}>{index + 1} 月</option>)}<option value="">清除月份</option></select>
        <select value={bestTimeSlot} aria-label="适宜时段" onChange={(event) => setBestTimeSlot(event.target.value)}><option value="">时段：全部</option><option value="SUNSET">日落</option><option value="MORNING">上午</option><option value="AFTERNOON">下午</option><option value="EVENING">晚间</option><option value="NIGHT">夜间</option></select>
        <select value={routeId} aria-label="路线筛选" onChange={(event) => setRouteId(event.target.value)}><option value="">路线：全部</option>{routes.data?.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
        <select value={visibility} aria-label="地图可见性" onChange={(event) => setVisibility(event.target.value as 'VISIBLE' | 'HIDDEN' | 'ALL')}><option value="VISIBLE">仅显示正常地点</option><option value="ALL">包含隐藏地点</option><option value="HIDDEN">仅隐藏地点</option></select>
      </div>
      <div className="map-page__stage">
        <MapCanvas
          markers={overview.data?.markers ?? []}
          clusters={overview.data?.clusters ?? []}
          selectedId={overview.data?.selected_place_id ?? null}
          onSelect={setSelectedId}
          viewport={viewport}
          onViewportChange={persistViewport}
          onDraftLocation={setDraft}
          chinaReset={chinaReset}
        />
        <Link className="route-badge" to="/routes"><ListOrdered />路线清单 <strong>{routes.data?.reduce((count, item) => count + item.places.length, 0) ?? 0}</strong></Link>
      </div>
      {deletedPlaceId && <div className="map-delete-toast" role="status">用户创建地点已移除 <button onClick={() => restoreManual.mutate(deletedPlaceId)} disabled={restoreManual.isPending}>恢复</button></div>}
      {draft && <section className="map-add-flow"><h2>搜索并创建地点</h2><p>已在地图上选点；优先复用高德 POI。</p><input value={poiQuery} onChange={(event) => setPoiQuery(event.target.value)} placeholder="搜索地点名称" />{searchPois.isPending && <p>正在搜索地点…</p>}{(poiQuery ? searchPois.data : nearby.data)?.map((poi) => <button key={poi.provider_id} onClick={() => addPlace.mutate({ mode: 'AMAP_POI', poi_id: poi.provider_id, place_type: 'LANDMARK', longitude: draft.longitude, latitude: draft.latitude })}><strong>{poi.name}</strong><span>{poi.address}</span></button>)}<div className="map-add-flow__custom"><input value={customName} onChange={(event) => setCustomName(event.target.value)} placeholder="都不是：输入自定义名称" /><button className="button button--outline" disabled={!customName || addPlace.isPending} onClick={() => addPlace.mutate({ mode: 'CUSTOM', name: customName, place_type: 'LANDMARK', longitude: draft.longitude, latitude: draft.latitude })}>创建自定义地点</button></div><button className="text-action" onClick={() => { setDraft(null); setPoiQuery('') }}>取消</button></section>}
      {selected && <section className="place-preview">
        <div className="place-preview__handle" />
        <div className="place-preview__nav"><span><strong>{activeIndex + 1}</strong> / {markerIds.length}</span><div><button onClick={() => moveSelection(-1)} aria-label="上一地点"><ChevronLeft /></button><button onClick={() => moveSelection(1)} aria-label="下一地点"><ChevronRight /></button></div></div>
        <h2>{selected.name}</h2><p>{selected.address}</p><p className="place-preview__summary">{String(selected.brief?.feature ?? selected.summary)}</p><p className="place-preview__meta">{selected.origin === 'USER_CREATED' ? '用户创建地点' : '视频地点'} · {selected.source_count} 个来源</p>
        <div className="place-preview__route">{routes.data?.length ? <><select value={routeId} aria-label="选择加入的路线" onChange={(event) => setRouteId(event.target.value)}><option value="">选择路线</option>{routes.data.map((item) => <option key={item.id} value={item.id}>{item.name}{item.places.some((place) => place.id === selected.id) ? '（已加入）' : ''}</option>)}</select><button className="button button--outline" onClick={() => addToRoute.mutate()} disabled={!route || route.places.some((place) => place.id === selected.id) || addToRoute.isPending}>加入路线</button></> : <button className="button button--outline" onClick={() => quickCreateRoute.mutate()} disabled={quickCreateRoute.isPending}>新建路线并加入</button>}</div>
        <div className="place-preview__actions">{selected.visibility === 'HIDDEN' ? <button className="button button--outline" onClick={() => restoreMarker.mutate(selected.id)}>恢复显示</button> : <button className="button button--outline" onClick={() => hideMarker.mutate(selected.id)}><EyeOff />隐藏</button>}{selected.origin === 'USER_CREATED' && <button className="button button--outline" onClick={() => deleteManual.mutate(selected.id)}><Trash2 />删除地点</button>}<Link className="button button--primary" to={`/places/${selected.id}`} state={{ fromMap: true }}>编辑地点</Link></div>
      </section>}
    </div>
  )
}
