import { RecommendationSummary } from '../../components/RecommendationSummary'
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight, Download, MapPinCheck, RotateCcw, X } from 'lucide-react'
import { useCallback, useDeferredValue, useEffect, useMemo, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'

import type { MapMarker } from '../../lib/types'
import { api } from '../../lib/api'
import { subscribeTravelChanges } from '../../lib/travelChanges'
import { IconButton } from '../../components/ui/IconButton'
import { FilterPopover } from '../../components/ui/FilterPopover'
import { FilterMenu } from '../../components/ui/FilterMenu'
import { SearchField } from '../../components/ui/SearchField'
import { placeText } from './placePresentation'
import { TravelBrief } from './TravelBrief'
import { clusterSummary, matchingCluster } from './clusterSummary'
import { MapCanvas } from './MapCanvas'
import { labelPlaceType, seasonLabels, segmentLabels, timeLabels, stateLabels } from './placeLabels'

const placeTypes = ['SCENIC_AREA', 'RESTAURANT', 'NEIGHBORHOOD', 'MUSEUM', 'PARK', 'HOTEL', 'TRANSPORT', 'LANDMARK']
const options = (labels: Record<string, string>) => [{ value: '', label: '全部' }, ...Object.entries(labels).map(([value, label]) => ({ value, label }))]
function FilterChoices({ label, value, values, onChange }: { label: string; value: string; values: Array<{ value: string; label: string }>; onChange: (value: string) => void }) {
  return <fieldset className="map-filter-choices"><legend>{label}</legend>{values.map((item) => <button type="button" key={item.value} aria-pressed={item.value === value} onClick={() => onChange(item.value)}>{item.label}</button>)}</fieldset>
}
function readMapState(): Record<string, string> {
  try {
    const value: unknown = JSON.parse(sessionStorage.getItem('zhijian-map-filters') || '{}')
    return value && typeof value === 'object' && !Array.isArray(value) ? Object.fromEntries(Object.entries(value).filter(([, entry]) => typeof entry === 'string')) : {}
  } catch { return {} }
}
function readViewport() {
  try {
    const value = JSON.parse(sessionStorage.getItem('zhijian-map-viewport') || 'null')
    if (value?.bbox?.length === 4 && value.bbox.every(Number.isFinite) && Number.isFinite(value.zoom)) return value as { bbox: number[]; zoom: number }
  } catch { /* Ignore an obsolete saved viewport. */ }
  return { bbox: [73.5, 18, 135.1, 53.6], zoom: 4 }
}

export function MapOverviewPage() {
  const queryClient = useQueryClient()
  const location = useLocation()
  const focusPlaceId = new URLSearchParams(location.search).get('place')
  const [cluster, setCluster] = useState<MapMarker[] | null>(null)
  const selectPlace = useCallback((id: string) => { setCluster(null); setSelectedId(id) }, [])
  const selectCluster = useCallback((markers: MapMarker[]) => { setSelectedId(undefined); setCluster(markers) }, [])
  const updateClusters = useCallback((groups: MapMarker[][]) => { setCluster((current) => current ? matchingCluster(groups, current) : null) }, [])
  const [saved] = useState(() => focusPlaceId ? {} : readMapState())
  useEffect(() => subscribeTravelChanges(queryClient), [queryClient])
  const [selectedId, setSelectedId] = useState<string | undefined>(focusPlaceId || saved.selectedId || undefined)
  const [state, setState] = useState(saved.state || '')
  const [query, setQuery] = useState(saved.query || '')
  const [placeType, setPlaceType] = useState(saved.placeType || '')
  const [season, setSeason] = useState(saved.season || '')
  const [month, setMonth] = useState(saved.month || '')
  const [monthSegment, setMonthSegment] = useState(saved.monthSegment || '')
  const [dayTimeSlot, setDayTimeSlot] = useState(saved.dayTimeSlot || '')
  const [visitWindowState, setVisitWindowState] = useState(saved.visitWindowState || '')
  const [recommendationTier, setRecommendationTier] = useState(saved.recommendationTier || '')
  const [visibility, setVisibility] = useState<'VISIBLE' | 'HIDDEN' | 'ALL'>('VISIBLE')
  const [targetRouteId, setTargetRouteId] = useState('')
  const [routeId, setRouteId] = useState(saved.routeId || '')
  const [poiQuery, setPoiQuery] = useState('')
  const [chinaReset, setChinaReset] = useState(0)
  const [addOpen, setAddOpen] = useState(false)
  const [viewport, setViewport] = useState(() => focusPlaceId ? { bbox: [73.5, 18, 135.1, 53.6], zoom: 4 } : readViewport())
  useEffect(() => { sessionStorage.setItem('zhijian-map-filters', JSON.stringify({ selectedId, state, query, placeType, season, month, monthSegment, dayTimeSlot, visitWindowState, recommendationTier, routeId })) }, [selectedId, state, query, placeType, season, month, monthSegment, dayTimeSlot, visitWindowState, recommendationTier, routeId])
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
  const overview = useQuery({ placeholderData: keepPreviousData, staleTime: 0, refetchOnWindowFocus: 'always', refetchInterval: 15_000, refetchIntervalInBackground: false, queryKey: ['map', selectedId, state, deferredQuery, placeType, season, month, monthSegment, dayTimeSlot, visitWindowState, recommendationTier, visibility, routeId, viewport], queryFn: () => api.map({ selectedPlaceId: selectedId, state, query: deferredQuery, placeType, season, month, monthSegment, dayTimeSlot, visitWindowState, recommendationTier, visibility, routeId, bbox: viewport.bbox, zoom: viewport.zoom }) })
  const routes = useQuery({ queryKey: ['routes'], queryFn: api.routes })
  const reviewCount = useQuery({ queryKey: ['place-review-count'], queryFn: api.placeReviewCount })
  const selected = overview.data?.markers.find((item) => item.id === selectedId)
  const markerIds = useMemo(() => overview.data?.markers.map((item) => item.id) ?? [], [overview.data?.markers])
  const activeIndex = Math.max(0, markerIds.indexOf(overview.data?.selected_place_id ?? ''))
  const route = routes.data?.find((item) => item.id === targetRouteId)
  useEffect(() => { if (targetRouteId && routes.data && !route) setTargetRouteId('') }, [route, targetRouteId, routes.data])
  useEffect(() => { const cancel = (event: KeyboardEvent) => { if (event.key === 'Escape') { setAddOpen(false); setPoiQuery(''); setSelectedId(undefined); setCluster(null) } }; window.addEventListener('keydown', cancel); return () => window.removeEventListener('keydown', cancel) }, [])
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
      if (created) setTargetRouteId(created.id)
      void queryClient.invalidateQueries({ queryKey: ['routes'] })
    },
  })
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

  const timeCount = [season, month, monthSegment, dayTimeSlot, visitWindowState].filter(Boolean).length
  const moreCount = [recommendationTier, routeId, visibility !== 'VISIBLE' ? visibility : ''].filter(Boolean).length
  const hasFilters = !!(state || query || placeType || timeCount || moreCount)
  const clearFilters = () => { setState(''); setQuery(''); setPlaceType(''); setSeason(''); setMonth(''); setMonthSegment(''); setDayTimeSlot(''); setVisitWindowState(''); setRecommendationTier(''); setRouteId(''); setVisibility('VISIBLE') }
  const groupSummary = cluster ? clusterSummary(cluster) : null

  return (
    <div className="map-page">
      <header className="map-toolbar">
        <SearchField className="map-toolbar__search" label="搜索地点或地址" value={query} onChange={(event) => { setQuery(event.target.value); setSelectedId(undefined) }} placeholder="搜索地点或地址" />
        <div className="map-toolbar__filters">
          <FilterMenu label="状态" value={state} onChange={setState} options={options({ SAVED: '想去', PLANNED: '已计划', VISITED: '去过', DISMISSED: '不感兴趣' })} />
          <FilterMenu label="类型" value={placeType} onChange={setPlaceType} options={[{ value: '', label: '全部' }, ...placeTypes.map((value) => ({ value, label: labelPlaceType(value) }))]} />
          <FilterPopover label={timeCount ? `出行时间 · ${timeCount}` : '出行时间'} active={!!timeCount}>
            <FilterChoices label="季节" value={season} onChange={setSeason} values={options(seasonLabels)} />
            <FilterChoices label="月份" value={month} onChange={setMonth} values={[{ value: '', label: '全部' }, ...Array.from({ length: 12 }, (_, i) => ({ value: String(i + 1), label: `${i + 1}月` }))]} />
            <FilterChoices label="旬段" value={monthSegment} onChange={setMonthSegment} values={options(segmentLabels)} />
            <FilterChoices label="时段" value={dayTimeSlot} onChange={setDayTimeSlot} values={options(timeLabels)} />
            <FilterChoices label="适宜度" value={visitWindowState} onChange={setVisitWindowState} values={options({ BEST: '最佳', GOOD: '适合', CAUTION: '需注意', CLOSED: '关闭/受限', UNKNOWN: '待明确' })} />
            <p>未选月份时查看已有推荐窗口；默认全年不计为最佳。组合条件须来自同一时间窗口。</p>
          </FilterPopover>
          <FilterPopover label={moreCount ? `更多 · ${moreCount}` : '更多'} active={!!moreCount}>
            <FilterChoices label="推荐" value={recommendationTier} onChange={setRecommendationTier} values={options({ PRIORITY: '优先关注', WORTH_CONSIDERING: '值得考虑', GENERAL: '一般', MISMATCH: '不符合偏好' })} />
            <FilterChoices label="路线" value={routeId} onChange={setRouteId} values={[{ value: '', label: '全部路线' }, ...(routes.data ?? []).map((item) => ({ value: item.id, label: item.name }))]} />
            <FilterChoices label="地图可见性" value={visibility} onChange={(value) => setVisibility(value as typeof visibility)} values={[{ value: 'VISIBLE', label: '正常显示' }, { value: 'HIDDEN', label: '已隐藏' }, { value: 'ALL', label: '全部' }]} />
            <Link to="/routes">管理路线清单</Link><div className="map-filter-tools"><button className="button button--outline" onClick={() => void exportGeoJson()}>导出地点</button><button className="button button--outline" onClick={resetChinaView}>全国视野</button></div>
          </FilterPopover>
        </div>
        <div className="map-toolbar__actions"><Link className="button button--outline" to="/places">地点管理</Link><Link className={`icon-button map-review-button${reviewCount.data?.count ? ' has-pending' : ''}`} to="/place-reviews" aria-label="待确认地点"><MapPinCheck />{reviewCount.data?.count ? <b>{reviewCount.data.count}</b> : null}</Link><button className="icon-button" aria-label="导出地点 GeoJSON" onClick={() => void exportGeoJson()}><Download /></button><button className="icon-button" aria-label="回到全国视野" onClick={resetChinaView}><RotateCcw /></button></div>
      </header>
      <div className="map-results" role="status">{overview.isError ? <>地点加载失败 <button className="text-action" onClick={() => void overview.refetch()}>重试</button></> : overview.isPending ? '正在加载地点…' : <>{overview.data?.visible_places ?? 0} 个地点 · 当前地图区域{overview.isFetching ? ' · 更新中' : ''}{!overview.data?.markers.length ? ' · 无匹配结果，试试清除筛选或回到全国视野' : ''}</>}{hasFilters ? <button className="text-action" onClick={clearFilters}>清除全部筛选</button> : null}</div>
      <div className="map-page__stage">
        <MapCanvas
          markers={overview.data?.markers ?? []}
          selectedId={selected?.id ?? null}
          onSelect={selectPlace}
          onClusterSelect={selectCluster}
          onClustersChange={updateClusters}
          viewport={viewport}
          onViewportChange={persistViewport}
          onStartPlaceSearch={() => { setAddOpen(true); setPoiQuery('') }}
          chinaReset={chinaReset}
        />

      </div>
      {addOpen && <section className="map-add-flow"><header><h2>搜索并确认地点</h2><p>使用高德全国 POI 搜索；确认前不会创建 Marker。</p><input autoFocus value={poiQuery} onChange={(event) => setPoiQuery(event.target.value)} placeholder="输入地点名称，例如：天安门" /></header><div className="map-add-results">{poiQuery.trim().length < 2 ? <p>请输入至少两个字开始搜索。</p> : null}{searchPois.isFetching ? <p>正在搜索地点…</p> : null}{searchPois.isError ? <p role="alert">搜索失败，请检查高德 Web 服务配置。</p> : null}{poiQuery.trim().length >= 2 && !searchPois.isFetching && !searchPois.data?.length ? <p>没有找到匹配地点，请尝试完整名称。</p> : null}{searchPois.data?.map((poi) => <button key={poi.provider_id} onClick={() => addPlace.mutate({ mode: 'AMAP_POI', poi_id: poi.provider_id, place_type: 'LANDMARK', longitude: poi.longitude, latitude: poi.latitude })}><strong>{poi.name}</strong><span>{[poi.city, poi.address].filter(Boolean).join(' · ')}</span></button>)}</div><footer><button className="text-action" onClick={() => { setAddOpen(false); setPoiQuery('') }}>取消</button></footer></section>}
      {cluster && <section className="place-preview cluster-preview" aria-label="聚合地点预览">
        <div className="place-preview__handle" /><header className="cluster-preview__header"><h2>这一区域的 {cluster.length} 个地点</h2><IconButton label="关闭聚合预览" onClick={() => setCluster(null)}><X /></IconButton></header>
        {groupSummary && <section className="cluster-preview__source"><p>区域看点</p><ul>{groupSummary.highlights.map((text) => <li key={text}>{placeText(text)}</li>)}</ul><details className="place-preview__evidence"><summary>查看更多</summary><p>这些地点的看点来自同一篇笔记。</p><Link to={`/video-notes/${groupSummary.note.note_id}`}>{groupSummary.note.title}</Link></details></section>}
        <ul className="cluster-preview__places">{cluster.map((marker) => <li key={marker.id}><button onClick={() => selectPlace(marker.id)}><strong>{marker.name}</strong><RecommendationSummary value={marker.recommendation_summary} compact /><span>{placeText(marker.travel_brief?.timing) || '适合时节待补充。'}</span></button></li>)}</ul>
      </section>}
      {selected && <section className={`place-preview${selected.longitude > (viewport.bbox[0] + viewport.bbox[2]) / 2 ? ' place-preview--left' : ''}`} aria-label="地点预览">
        <div className="place-preview__handle" />
        <div className="place-preview__nav"><span><strong>{activeIndex + 1}</strong> / {markerIds.length}</span><div><button onClick={() => moveSelection(-1)} aria-label="上一地点"><ChevronLeft /></button><button onClick={() => moveSelection(1)} aria-label="下一地点"><ChevronRight /></button><button onClick={() => setSelectedId(undefined)} aria-label="关闭地点预览"><X /></button></div></div>
        <h2>{selected.name}</h2><RecommendationSummary value={selected.recommendation_summary} />
        <p>{labelPlaceType(selected.place_type)} · {stateLabels[selected.user_state] ?? selected.user_state}</p>
        <p className="place-preview__address">{selected.address}</p>
        {selected.preview_image ? <img className="place-preview__image" src={selected.preview_image} alt={`${selected.name}的视频截图`} /> : null}
        <TravelBrief brief={selected.travel_brief} />
        <details className="place-preview__evidence" key={selected.id}><summary>查看更多</summary>
          <p className="place-preview__meta">{selected.origin === 'USER_CREATED' ? '用户创建' : '地点来源'} · {selected.source_count} 个独立来源</p>
          {selected.travel_brief?.inherited && <p>时节采用同篇笔记中关联地点的共同景观背景，未继承具体日期或时刻。</p>}
          {selected.source_notes?.map((note) => <p key={`${note.note_id}-${note.version_id}`}><Link to={`/video-notes/${note.note_id}`}>{note.title}</Link></p>)}
          {selected.visit_window_evidence?.map((item, i) => <blockquote key={i}><small>{item.source_kind === 'TITLE_METADATA' ? '视频标题' : item.source_kind === 'USER' ? '人工补充' : item.source_kind === 'SEMANTIC_CONTEXT' ? '同笔记共同景观的时节背景' : '正文原句'}</small><p>{item.source_text}</p></blockquote>)}
          <Link to={`/places/${selected.id}#time-evidence`} state={{ fromMap: true }}>完整地点与来源</Link>
        </details>
        <details className="place-preview__route-disclosure" key={`route-${selected.id}`}><summary>加入路线</summary><div className="place-preview__route">{routes.data?.length ? <><FilterMenu label="目标路线" value={targetRouteId} onChange={setTargetRouteId} options={[{ value: '', label: '选择路线' }, ...routes.data.map((item) => ({ value: item.id, label: item.name }))]} /><button className="button button--outline" onClick={() => addToRoute.mutate()} disabled={!route || route.places.some((place) => place.id === selected.id) || addToRoute.isPending}>{route?.places.some((place) => place.id === selected.id) ? '已加入' : addToRoute.isPending ? '加入中…' : '加入路线'}</button></> : <button className="button button--outline" onClick={() => quickCreateRoute.mutate()} disabled={routes.isPending || routes.isError || quickCreateRoute.isPending}>新建路线并加入</button>}</div></details>
        {addToRoute.isError || quickCreateRoute.isError || routes.isError ? <p role="alert">路线加载或添加失败，请重试。</p> : null}
        {(addToRoute.isSuccess || quickCreateRoute.isSuccess) && route?.places.some((place) => place.id === selected.id) ? <p role="status">已加入路线</p> : null}
        <div className="place-preview__actions"><Link className="button button--primary" to={`/places/${selected.id}`} state={{ fromMap: true }}>查看详情</Link></div>
      </section>}
    </div>
  )
}
