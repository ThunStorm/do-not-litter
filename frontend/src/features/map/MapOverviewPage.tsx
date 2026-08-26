import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight, Download, EyeOff, ListOrdered, Plus, RotateCcw, Search } from 'lucide-react'
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
  const addMarker = useMutation({ mutationFn: (payload: { longitude: number; latitude: number; custom_name: string }) => api.createMapMarker(payload), onSuccess: (value) => { setSelectedId(value.place_id); void queryClient.invalidateQueries({ queryKey: ['map'] }) } })

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

  function addCurrentLocation() {
    navigator.geolocation?.getCurrentPosition((position) => {
      const name = window.prompt('为这个用户地点命名')
      if (name) addMarker.mutate({ longitude: position.coords.longitude, latitude: position.coords.latitude, custom_name: name })
    })
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
        <div><h1>中国大陆地点地图</h1><p>当前视野 · {overview.data?.visible_places ?? 0}/{overview.data?.total_places ?? 0} 个地点</p></div>
        <div><button className="icon-button" aria-label="导出地点 GeoJSON" onClick={() => void exportGeoJson()}><Download /></button><button className="icon-button" aria-label="回到全国视野" onClick={resetChinaView}><RotateCcw /></button><button className="icon-button" aria-label="搜索地点" onClick={() => setSearchOpen((value) => !value)}><Search /></button></div>
      </header>
      {searchOpen && <div className="map-search"><Search /><input autoFocus value={query} onChange={(event) => { setQuery(event.target.value); setSelectedId(undefined) }} placeholder="搜索地点或地址" /><span>{overview.data?.visible_places ?? 0} 个结果</span></div>}
      <div className="map-filters">
        {stateFilters.map((filter) => <button key={filter.label} className={state === filter.value ? 'is-active' : ''} onClick={() => { setState(filter.value); setSelectedId(undefined) }}>{filter.label}</button>)}
        <button className={placeType ? 'is-active' : ''} onClick={() => { setPlaceType((value) => value ? '' : 'SCENIC_AREA'); setSelectedId(undefined) }}>{placeType || '景区'}</button>
      </div>
      <div className="map-page__stage">
        <MapCanvas
          markers={overview.data?.markers ?? []}
          clusters={overview.data?.clusters ?? []}
          selectedId={overview.data?.selected_place_id ?? null}
          onSelect={setSelectedId}
          viewport={viewport}
          onViewportChange={persistViewport}
        />
        <Link className="route-badge" to="/routes"><ListOrdered />路线清单 <strong>{route?.places.length ?? 0}</strong></Link>
        <button className="map-add-marker button button--primary" onClick={addCurrentLocation} disabled={addMarker.isPending}><Plus />新增地点</button>
      </div>
      {selected && <section className="place-preview">
        <div className="place-preview__handle" />
        <div className="place-preview__nav"><span><strong>{activeIndex + 1}</strong> / {markerIds.length}</span><div><button onClick={() => moveSelection(-1)} aria-label="上一地点"><ChevronLeft /></button><button onClick={() => moveSelection(1)} aria-label="下一地点"><ChevronRight /></button></div></div>
        <h2>{selected.name}</h2><p>{selected.address}</p><p className="place-preview__summary">{String(selected.brief?.feature ?? selected.summary)}</p><p className="place-preview__meta">{selected.origin === 'USER' ? '用户 Marker' : '视频地点'} · {selected.source_count} 个来源</p>
        <div className="place-preview__actions"><button className="button button--outline" onClick={() => addToRoute.mutate()} disabled={!route || addToRoute.isPending}>加入路线清单</button>{selected.marker_id && selected.visibility === 'VISIBLE' && <button className="button button--outline" onClick={() => hideMarker.mutate(selected.marker_id ?? '')}><EyeOff />隐藏</button>}<Link className="button button--primary" to={`/places/${selected.id}`} state={{ fromMap: true }}>查看详情</Link></div>
      </section>}
    </div>
  )
}
