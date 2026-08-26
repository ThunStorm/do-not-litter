import { useEffect, useRef, useState } from 'react'

import { api } from '../../lib/api'
import type { MapMarker } from '../../lib/types'

interface AmapLayerProps {
  markers: MapMarker[]
  selectedId: string | null
  onSelect: (id: string) => void
  viewport: { bbox: number[]; zoom: number }
  onReady: (ready: boolean) => void
  onViewportChange: (viewport: { bbox: number[]; zoom: number }) => void
}

type AmapMarker = { on: (event: string, callback: () => void) => void }
type AmapLngLat = { getLng: () => number; getLat: () => number }
type AmapBounds = { getSouthWest: () => AmapLngLat; getNorthEast: () => AmapLngLat }
type AmapMap = {
  add: (items: AmapMarker[]) => void
  destroy: () => void
  on: (event: string, callback: () => void) => void
  getBounds: () => AmapBounds
  getZoom: () => number
}
type AmapRuntime = {
  Map: new (container: HTMLElement, options: Record<string, unknown>) => AmapMap
  Marker: new (options: Record<string, unknown>) => AmapMarker
  Pixel: new (x: number, y: number) => unknown
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
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${encodeURIComponent(key)}`
    script.async = true
    script.onload = () => window.AMap ? resolve(window.AMap) : reject(new Error('高德地图运行时未就绪'))
    script.onerror = () => reject(new Error('高德地图脚本加载失败'))
    document.head.appendChild(script)
  })
  return loader
}

export function AmapLayer({ markers, selectedId, onSelect, viewport, onReady, onViewportChange }: AmapLayerProps) {
  const container = useRef<HTMLDivElement>(null)
  const [error, setError] = useState('')
  const [config, setConfig] = useState<{ js_key: string; security_code: string; default_viewport: { zoom: number } } | null>(null)

  useEffect(() => {
    let active = true
    api.mapBootstrap().then((value) => { if (active) setConfig(value) }).catch(() => { if (active) setError('地图配置读取失败') })
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!config?.js_key || !container.current) return
    let map: AmapMap | undefined
    let cancelled = false
    loadAmap(config.js_key, config.security_code)
      .then((AMap) => {
        if (cancelled || !container.current) return
        const [west, south, east, north] = viewport.bbox
        map = new AMap.Map(container.current, {
          zoom: viewport.zoom || config.default_viewport.zoom,
          center: [(west + east) / 2, (south + north) / 2],
          mapStyle: 'amap://styles/whitesmoke',
        })
        const syncViewport = () => {
          if (!map) return
          const bounds = map.getBounds()
          const southWest = bounds.getSouthWest()
          const northEast = bounds.getNorthEast()
          onViewportChange({ bbox: [southWest.getLng(), southWest.getLat(), northEast.getLng(), northEast.getLat()], zoom: map.getZoom() })
        }
        map.on('moveend', syncViewport)
        map.on('zoomend', syncViewport)
        const mapMarkers = markers.map((marker) => {
          const selected = marker.id === selectedId
          const element = document.createElement('button')
          element.className = `amap-marker${selected ? ' is-selected' : ''}`
          element.type = 'button'
          element.setAttribute('aria-label', `查看 ${marker.name}`)
          const item = new AMap.Marker({
            position: [marker.longitude, marker.latitude],
            content: element,
            offset: new AMap.Pixel(-13, -26),
            title: marker.name,
          })
          item.on('click', () => onSelect(marker.id))
          return item
        })
        map.add(mapMarkers)
        onReady(true)
      })
      .catch((reason) => {
        setError(reason instanceof Error ? reason.message : '高德地图加载失败')
        onReady(false)
      })
    return () => {
      cancelled = true
      map?.destroy()
      onReady(false)
    }
  }, [config, markers, onReady, onSelect, onViewportChange, selectedId, viewport])

  if (!config?.js_key || error) return null
  return <div className="amap-layer" ref={container} aria-label="高德地图底图" />
}
