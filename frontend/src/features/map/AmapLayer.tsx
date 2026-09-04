import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react'

import { api } from '../../lib/api'
import type { MapMarker } from '../../lib/types'

export interface MapController {
  zoomIn: () => void
  zoomOut: () => void
  locate: () => void
  fitChina: () => void
  enterAddMode: () => void
  clearDraft: () => void
}

interface AmapLayerProps {
  markers: MapMarker[]
  clusters: Array<Record<string, unknown>>
  selectedId: string | null
  onSelect: (id: string) => void
  viewport: { bbox: number[]; zoom: number }
  onReady: (ready: boolean) => void
  onViewportChange: (viewport: { bbox: number[]; zoom: number }) => void
  onDraftLocation: (location: { longitude: number; latitude: number }) => void
}

type AmapMarker = { on: (event: string, callback: () => void) => void }
type AmapLngLat = { getLng: () => number; getLat: () => number }
type AmapBounds = { getSouthWest: () => AmapLngLat; getNorthEast: () => AmapLngLat }
type AmapEvent = { lnglat?: { getLng: () => number; getLat: () => number } }
type AmapMap = {
  add: (items: AmapMarker[]) => void
  remove: (items: AmapMarker[]) => void
  destroy: () => void
  on: (event: string, callback: (event: AmapEvent) => void) => void
  off: (event: string, callback: (event: AmapEvent) => void) => void
  getBounds: () => AmapBounds
  getZoom: () => number
  setZoomAndCenter: (zoom: number, center: [number, number]) => void
  setBounds: (bounds: unknown, options?: Record<string, unknown>) => void
  resize: () => void
  zoomIn: () => void
  zoomOut: () => void
  setFitView: (items: AmapMarker[]) => void
}
type AmapCluster = { setMap: (map: AmapMap | null) => void }
type AmapRuntime = {
  Map: new (container: HTMLElement, options: Record<string, unknown>) => AmapMap
  Marker: new (options: Record<string, unknown>) => AmapMarker
  MarkerCluster?: new (map: AmapMap, markers: AmapMarker[], options?: Record<string, unknown>) => AmapCluster
  Pixel: new (x: number, y: number) => unknown
  Bounds?: new (southWest: [number, number], northEast: [number, number]) => unknown
}

declare global {
  interface Window {
    AMap?: AmapRuntime
    _AMapSecurityConfig?: { securityJsCode: string }
  }
}

let loader: Promise<AmapRuntime> | undefined

function loadAmap(key: string, securityCode: string) {
  if (window.AMap) return Promise.resolve(window.AMap)
  if (loader) return loader
  if (securityCode) window._AMapSecurityConfig = { securityJsCode: securityCode }
  loader = new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = `https://webapi.amap.com/maps?v=2.0&plugin=AMap.MarkerCluster&key=${encodeURIComponent(key)}`
    script.async = true
    script.onload = () => window.AMap ? resolve(window.AMap) : reject(new Error('高德地图运行时未就绪'))
    script.onerror = () => reject(new Error('高德地图脚本加载失败'))
    document.head.appendChild(script)
  })
  return loader
}

function sameViewport(left: { bbox: number[]; zoom: number }, right: { bbox: number[]; zoom: number }) {
  return Math.abs(left.zoom - right.zoom) < 0.05 && left.bbox.every((value, index) => Math.abs(value - right.bbox[index]) < 0.01)
}

function fitChina(map: AmapMap, AMap: AmapRuntime) {
  if (AMap.Bounds) map.setBounds(new AMap.Bounds([73.5, 18], [135.1, 53.6]), { padding: [32, 32, 32, 32] })
  else map.setZoomAndCenter(4, [104.3, 35.8])
}

export const AmapLayer = forwardRef<MapController, AmapLayerProps>(function AmapLayer({ markers, clusters, selectedId, onSelect, viewport, onReady, onViewportChange, onDraftLocation }, ref) {
  const container = useRef<HTMLDivElement>(null)
  const mapRef = useRef<AmapMap | null>(null)
  const runtimeRef = useRef<AmapRuntime | null>(null)
  const mapMarkersRef = useRef<AmapMarker[]>([])
  const clusterMarkersRef = useRef<AmapMarker[]>([])
  const draftMarkerRef = useRef<AmapMarker | null>(null)
  const markerElementsRef = useRef(new Map<string, HTMLButtonElement>())
  const lastViewportRef = useRef(viewport)
  const selectedIdRef = useRef(selectedId)
  const draftModeRef = useRef(false)
  const draftLocationRef = useRef(onDraftLocation)
  const [error, setError] = useState('')
  const [mapVersion, setMapVersion] = useState(0)
  const [config, setConfig] = useState<{ js_key: string; security_code: string; default_viewport: { zoom: number } } | null>(null)

  selectedIdRef.current = selectedId
  draftLocationRef.current = onDraftLocation

  useImperativeHandle(ref, () => ({
    zoomIn: () => mapRef.current?.zoomIn(),
    zoomOut: () => mapRef.current?.zoomOut(),
    locate: () => navigator.geolocation?.getCurrentPosition((position) => mapRef.current?.setZoomAndCenter(Math.max(mapRef.current.getZoom(), 14), [position.coords.longitude, position.coords.latitude])),
    fitChina: () => {
      const map = mapRef.current
      const AMap = runtimeRef.current
      if (map && AMap) fitChina(map, AMap)
    },
    enterAddMode: () => { draftModeRef.current = true },
    clearDraft: () => {
      const map = mapRef.current
      if (map && draftMarkerRef.current) map.remove([draftMarkerRef.current])
      draftMarkerRef.current = null
    },
  }), [])

  useEffect(() => {
    let active = true
    api.mapBootstrap().then((value) => { if (active) setConfig(value) }).catch(() => { if (active) setError('地图配置读取失败') })
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!config?.js_key || !container.current || mapRef.current) return
    let cancelled = false
    let syncTimer: number | undefined
    let syncViewport: ((event: AmapEvent) => void) | undefined
    let chooseLocation: ((event: AmapEvent) => void) | undefined
    let resizeObserver: ResizeObserver | undefined
    loadAmap(config.js_key, config.security_code).then((AMap) => {
      if (cancelled || !container.current) return
      runtimeRef.current = AMap
      const [west, south, east, north] = viewport.bbox
      const map = new AMap.Map(container.current, { zoom: viewport.zoom || config.default_viewport.zoom, center: [(west + east) / 2, (south + north) / 2], mapStyle: 'amap://styles/whitesmoke' })
      mapRef.current = map
      lastViewportRef.current = viewport
      if (viewport.bbox[0] <= 73.5 && viewport.bbox[2] >= 135.1) {
        fitChina(map, AMap)
      }
      setMapVersion((value) => value + 1)
      syncViewport = () => {
        window.clearTimeout(syncTimer)
        syncTimer = window.setTimeout(() => {
          const bounds = map.getBounds()
          const southWest = bounds.getSouthWest()
          const northEast = bounds.getNorthEast()
          const next = { bbox: [southWest.getLng(), southWest.getLat(), northEast.getLng(), northEast.getLat()], zoom: map.getZoom() }
          lastViewportRef.current = next
          onViewportChange(next)
        }, 250)
      }
      chooseLocation = (event: AmapEvent) => {
        if (!draftModeRef.current || !event.lnglat) return
        draftModeRef.current = false
        if (draftMarkerRef.current) map.remove([draftMarkerRef.current])
        draftMarkerRef.current = new AMap.Marker({ position: [event.lnglat.getLng(), event.lnglat.getLat()], title: '待添加地点' })
        map.add([draftMarkerRef.current])
        draftLocationRef.current({ longitude: event.lnglat.getLng(), latitude: event.lnglat.getLat() })
      }
      map.on('moveend', syncViewport)
      map.on('zoomend', syncViewport)
      map.on('click', chooseLocation)
      resizeObserver = new ResizeObserver(() => {
        map.resize()
        if (lastViewportRef.current.bbox[0] <= 73.5 && lastViewportRef.current.bbox[2] >= 135.1) {
          fitChina(map, AMap)
        }
      })
      resizeObserver.observe(container.current)
      onReady(true)
    }).catch((reason) => {
      setError(reason instanceof Error ? reason.message : '高德地图加载失败')
      onReady(false)
    })
    return () => {
      cancelled = true
      window.clearTimeout(syncTimer)
      const map = mapRef.current
      if (map && syncViewport) {
        map.off('moveend', syncViewport)
        map.off('zoomend', syncViewport)
        if (chooseLocation) map.off('click', chooseLocation)
      }
      resizeObserver?.disconnect()
      map?.destroy()
      mapRef.current = null
      onReady(false)
    }
  // The map is intentionally created once per mounted, configured layer.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config?.js_key, config?.security_code])

  useEffect(() => {
    const map = mapRef.current
    const AMap = runtimeRef.current
    if (!map || !AMap) return
    map.remove(mapMarkersRef.current)
    map.remove(clusterMarkersRef.current)
    markerElementsRef.current.clear()
    const mapMarkers = markers.map((marker) => {
      const element = document.createElement('button')
      element.className = `amap-marker${marker.id === selectedIdRef.current ? ' is-selected' : ''}`
      element.type = 'button'
      element.setAttribute('aria-label', `查看 ${marker.name}`)
      markerElementsRef.current.set(marker.id, element)
      const item = new AMap.Marker({ position: [marker.longitude, marker.latitude], content: element, offset: new AMap.Pixel(-13, -26), title: marker.name })
      item.on('click', () => onSelect(marker.id))
      return item
    })
    const clusterMarkers = clusters.map((cluster) => {
      const longitude = Number(cluster.longitude)
      const latitude = Number(cluster.latitude)
      const count = Number(cluster.count)
      const element = document.createElement('button')
      element.className = 'amap-cluster'
      element.type = 'button'
      element.textContent = String(count)
      element.setAttribute('aria-label', `${count} 个地点，点击放大查看`)
      const item = new AMap.Marker({ position: [longitude, latitude], content: element, offset: new AMap.Pixel(-17, -17) })
      item.on('click', () => map.setZoomAndCenter(Math.min(map.getZoom() + 2, 20), [longitude, latitude]))
      return item
    })
    mapMarkersRef.current = mapMarkers
    clusterMarkersRef.current = clusterMarkers
    map.add(mapMarkers)
    map.add(clusterMarkers)
    return () => {
      map.remove(mapMarkers)
      map.remove(clusterMarkers)
    }
  }, [clusters, mapVersion, markers, onSelect])

  useEffect(() => {
    for (const [id, element] of markerElementsRef.current) element.classList.toggle('is-selected', id === selectedId)
  }, [selectedId])

  useEffect(() => {
    const map = mapRef.current
    if (!map || sameViewport(viewport, lastViewportRef.current)) return
    const [west, south, east, north] = viewport.bbox
    lastViewportRef.current = viewport
    map.setZoomAndCenter(viewport.zoom, [(west + east) / 2, (south + north) / 2])
  }, [viewport])

  if (error) return <p className="map-runtime-state" role="status">{error}。请前往设置检查高德地图配置。</p>
  if (config && !config.js_key) return <p className="map-runtime-state" role="status">尚未配置高德 JS API Key。请前往设置完成地图配置。</p>
  return <div className="amap-layer" ref={container} aria-label="高德地图底图" />
})
