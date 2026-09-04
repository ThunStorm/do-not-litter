import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight, Download, EyeOff, ListOrdered, RotateCcw, Search } from 'lucide-react'
import { useCallback, useDeferredValue, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../../lib/api'
import { MapCanvas } from './MapCanvas'

const stateFilters = [
  { label: '全部', value: '' },
  { label: '想去', value: 'SAVED' },
  { label: '去过', value: 'VISITED' },
  { label: '计划', value: 'PLANNED' },
]

export function MapOverviewPage() {
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState<string>()
  const [state, setState] = useState('')
  const [searchOpen, setSearchOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [placeType, setPlaceType] = useState('')
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
  const overview = useQuery({ queryKey: ['map', selectedId, state, deferredQuery, placeType, viewport], queryFn: () => api.map({ selectedPlaceId: selectedId, state, query: deferredQuery, placeType, bbox: viewport.bbox, zoom: viewport.zoom }) })
  const routes = useQuery({ queryKey: ['routes'], queryFn: api.routes })
  const selected = overview.data?.markers.find((item) => item.id === overview.data?.selected_place_id)
  const markerIds = useMemo(() => overview.data?.markers.map((item) => item.id) ?? [], [overview.data?.markers])
  const activeIndex = Math.max(0, markerIds.indexOf(overview.data?.selected_place_id ?? ''))
  const route = routes.data?.[0]
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
  const hideMarker = useMutation({ mutationFn: (markerId: string) => api.deleteMapMarker(markerId), onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['map'] }) })
  const nearby = useQuery({ queryKey: ['nearby-pois', draft], queryFn: () => api.nearbyPois(draft!.longitude, draft!.latitude), enabled: Boolean(draft) })
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
        <div className="map-page__actions"><Link className="map-review-link" to="/place-reviews">待确认</Link><button className="icon-button" aria-label="导出地点 GeoJSON" onClick={() => void exportGeoJson()}><Download /></button><button className="icon-button" aria-label="回到全国视野" onClick={resetChinaView}><RotateCcw /></button><button className="icon-button" aria-label="搜索地点" onClick={() => setSearchOpen((value) => !value)}><Search /></button></div>
      </header>
      {searchOpen && <div className="map-search"><Search /><input autoFocus value={query} onChange={(event) => { setQuery(event.target.value); setSelectedId(undefined) }} placeholder="搜索地点或地址" /><span>{overview.data?.visible_places ?? 0} 个结果</span></div>}
      <div className="map-filters">
        {stateFilters.map((filter) => <button key={filter.label} className={state === filter.value ? 'is-active' : ''} onClick={() => { setState(filter.value); setSelectedId(undefined) }}>{filter.label}</button>)}
        <button className={placeType ? 'is-active' : ''} aria-pressed={Boolean(placeType)} onClick={() => { setPlaceType((value) => value ? '' : 'SCENIC_AREA'); setSelectedId(undefined) }}>景区</button>
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
        />
        <Link className="route-badge" to="/routes"><ListOrdered />路线清单 <strong>{route?.places.length ?? 0}</strong></Link>
      </div>
      {draft && <section className="map-add-flow"><h2>选择附近地点</h2><p>已在地图上选点；优先选择高德 POI。</p>{nearby.isPending && <p>正在搜索附近地点…</p>}{nearby.isError && <p>附近搜索失败，请改为自定义地点或重新点选。</p>}{nearby.data?.length === 0 && <p>附近没有可用 POI，可创建自定义地点。</p>}{nearby.data?.map((poi) => <button key={poi.provider_id} onClick={() => addPlace.mutate({ mode: 'AMAP_POI', poi_id: poi.provider_id, place_type: 'LANDMARK', longitude: draft.longitude, latitude: draft.latitude })}><strong>{poi.name}</strong><span>{poi.address}</span></button>)}<div className="map-add-flow__custom"><input value={customName} onChange={(event) => setCustomName(event.target.value)} placeholder="附近都不对：输入自定义名称" /><button className="button button--outline" disabled={!customName || addPlace.isPending} onClick={() => addPlace.mutate({ mode: 'CUSTOM', name: customName, place_type: 'LANDMARK', longitude: draft.longitude, latitude: draft.latitude })}>创建自定义地点</button></div><button className="text-action" onClick={() => setDraft(null)}>取消</button></section>}
      {selected && <section className="place-preview">
        <div className="place-preview__handle" />
        <div className="place-preview__nav"><span><strong>{activeIndex + 1}</strong> / {markerIds.length}</span><div><button onClick={() => moveSelection(-1)} aria-label="上一地点"><ChevronLeft /></button><button onClick={() => moveSelection(1)} aria-label="下一地点"><ChevronRight /></button></div></div>
        <h2>{selected.name}</h2><p>{selected.address}</p><p className="place-preview__summary">{String(selected.brief?.feature ?? selected.summary)}</p><p className="place-preview__meta">{selected.origin === 'USER' ? '用户 Marker' : '视频地点'} · {selected.source_count} 个来源</p>
        <div className="place-preview__actions"><button className="button button--outline" onClick={() => addToRoute.mutate()} disabled={!route || addToRoute.isPending}>加入路线清单</button>{selected.marker_id && selected.visibility === 'VISIBLE' && <button className="button button--outline" onClick={() => hideMarker.mutate(selected.marker_id ?? '')}><EyeOff />隐藏</button>}<Link className="button button--primary" to={`/places/${selected.id}`} state={{ fromMap: true }}>查看详情</Link></div>
      </section>}
    </div>
  )
}
