import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight, ListOrdered, Search, SlidersHorizontal } from 'lucide-react'
import { useMemo, useState } from 'react'
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
  const overview = useQuery({ queryKey: ['map', selectedId, state], queryFn: () => api.map(selectedId, state) })
  const routes = useQuery({ queryKey: ['routes'], queryFn: api.routes })
  const selected = overview.data?.selected_preview
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

  function moveSelection(offset: number) {
    if (!markerIds.length) return
    const next = (activeIndex + offset + markerIds.length) % markerIds.length
    setSelectedId(markerIds[next])
  }

  return (
    <div className="map-page">
      <header className="map-page__header">
        <div><h1>地图总览</h1><p>厦门 · {overview.data?.total_places ?? 0} 个地点</p></div>
        <button className="icon-button" aria-label="搜索地点"><Search /></button>
      </header>
      <div className="map-filters">
        {stateFilters.map((filter) => <button key={filter.label} className={state === filter.value ? 'is-active' : ''} onClick={() => { setState(filter.value); setSelectedId(undefined) }}>{filter.label}</button>)}
        <button><SlidersHorizontal />区域</button>
      </div>
      <div className="map-page__stage">
        <MapCanvas markers={overview.data?.markers ?? []} selectedId={overview.data?.selected_place_id ?? null} onSelect={setSelectedId} />
        <Link className="route-badge" to="/routes"><ListOrdered />路线清单 <strong>{route?.places.length ?? 0}</strong></Link>
      </div>
      {selected && <section className="place-preview">
        <div className="place-preview__handle" />
        <div className="place-preview__nav"><span><strong>{activeIndex + 1}</strong> / {markerIds.length}</span><div><button onClick={() => moveSelection(-1)} aria-label="上一地点"><ChevronLeft /></button><button onClick={() => moveSelection(1)} aria-label="下一地点"><ChevronRight /></button></div></div>
        <h2>{selected.name}</h2><p>{selected.address}</p><p className="place-preview__summary">{selected.observations[0]?.value ?? selected.summary}</p>
        <div className="place-preview__actions"><button className="button button--outline" onClick={() => addToRoute.mutate()} disabled={!route || addToRoute.isPending}>加入路线清单</button><Link className="button button--primary" to={`/places/${selected.id}`} state={{ fromMap: true }}>查看详情</Link></div>
      </section>}
    </div>
  )
}
