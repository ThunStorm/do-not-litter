import { useEffect, useRef, useState } from 'react'

import type { MapMarker } from '../../lib/types'

interface AmapLayerProps {
  markers: MapMarker[]
  selectedId: string | null
  onSelect: (id: string) => void
  onReady: (ready: boolean) => void
}

type AmapMarker = { on: (event: string, callback: () => void) => void }
type AmapMap = { add: (items: AmapMarker[]) => void; destroy: () => void; setFitView: () => void }
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

export function AmapLayer({ markers, selectedId, onSelect, onReady }: AmapLayerProps) {
  const container = useRef<HTMLDivElement>(null)
  const [error, setError] = useState('')
  const apiKey = import.meta.env.VITE_AMAP_JS_KEY as string | undefined
  const securityCode = import.meta.env.VITE_AMAP_SECURITY_CODE as string | undefined

  useEffect(() => {
    if (!apiKey || !container.current) return
    let map: AmapMap | undefined
    let cancelled = false
    loadAmap(apiKey, securityCode ?? '')
      .then((AMap) => {
        if (cancelled || !container.current) return
        map = new AMap.Map(container.current, { zoom: 12, mapStyle: 'amap://styles/whitesmoke' })
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
        if (mapMarkers.length) map.setFitView()
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
  }, [apiKey, markers, onReady, onSelect, securityCode, selectedId])

  if (!apiKey || error) return null
  return <div className="amap-layer" ref={container} aria-label="高德地图底图" />
}
