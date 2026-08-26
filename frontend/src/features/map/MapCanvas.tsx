import { LocateFixed, Maximize, Minus, Plus } from 'lucide-react'
import { useCallback, useState } from 'react'

import type { MapMarker } from '../../lib/types'
import { AmapLayer } from './AmapLayer'

interface MapCanvasProps {
  markers: MapMarker[]
  clusters: Array<Record<string, unknown>>
  selectedId: string | null
  onSelect: (id: string) => void
  viewport: { bbox: number[]; zoom: number }
  onViewportChange: (viewport: { bbox: number[]; zoom: number }) => void
}

const roads = [
  'M-20 110 C120 70 180 150 360 100 S650 80 900 130',
  'M40 -20 C80 160 210 250 180 520 S280 760 230 960',
  'M370 -40 C350 180 420 240 390 430 S460 720 520 950',
  'M650 -30 C590 190 680 300 620 480 S710 720 750 950',
  'M-20 310 C190 270 300 350 480 300 S720 250 880 330',
  'M-20 540 C160 500 280 570 450 520 S700 500 880 590',
  'M-20 760 C170 700 290 780 480 730 S700 710 880 800',
]

export function MapCanvas({ markers, clusters, selectedId, onSelect, viewport, onViewportChange }: MapCanvasProps) {
  const bounds = markerBounds(markers)
  const [amapReady, setAmapReady] = useState(false)
  const [zoom, setZoom] = useState(1)
  const [locationMessage, setLocationMessage] = useState('')
  const handleAmapReady = useCallback((ready: boolean) => setAmapReady(ready), [])
  return (
    <div className="map-canvas" aria-label="中国大陆地点地图总览">
      <svg className={`map-canvas__roads ${amapReady ? 'is-hidden' : ''}`} style={{ transform: `scale(${zoom})` }} viewBox="0 0 853 900" aria-hidden="true">
        <rect width="853" height="900" fill="#f4f3f0" />
        <path d="M690 0 H853 V900 H760 C700 760 780 650 720 520 C680 410 750 240 690 0Z" fill="#e8ecee" />
        {roads.map((road) => <path key={road} d={road} fill="none" stroke="#d4d2cd" strokeWidth="8" />)}
        {roads.map((road) => <path key={`inner-${road}`} d={road} fill="none" stroke="#faf9f6" strokeWidth="5" />)}
        <text x="310" y="420" fill="#817f79" fontSize="18" fontFamily="PingFang SC, sans-serif">中国大陆地图预览</text>
      </svg>
      <div className={`map-canvas__markers ${amapReady ? 'is-hidden' : ''}`} style={{ transform: `scale(${zoom})` }}>
        {clusters.map((cluster) => {
          const point = clusterPosition(cluster)
          return <span className="map-cluster" key={String(cluster.id)} style={{ left: `${point.left}%`, top: `${point.top}%` }}>{String(cluster.count)}</span>
        })}
        {markers.map((marker) => {
          const { left, top } = markerPosition(marker, bounds)
          const selected = marker.id === selectedId
          return (
            <button
              key={marker.id}
              className={`map-marker ${selected ? 'is-selected' : ''}`}
              style={{ left: `${left}%`, top: `${top}%` }}
              onClick={() => onSelect(marker.id)}
              aria-label={`查看 ${marker.name}`}
              aria-pressed={selected}
            ><span /></button>
          )
        })}
      </div>
      <AmapLayer markers={markers} selectedId={selectedId} onSelect={onSelect} viewport={viewport} onReady={handleAmapReady} onViewportChange={onViewportChange} />
      <div className="map-canvas__tools"><button aria-label="定位" onClick={() => navigator.geolocation?.getCurrentPosition((position) => setLocationMessage(`当前位置 ${position.coords.latitude.toFixed(4)}, ${position.coords.longitude.toFixed(4)}`), () => setLocationMessage('无法读取当前位置'))}><LocateFixed /></button><button aria-label="放大" onClick={() => setZoom((value) => Math.min(1.6, value + .15))}><Plus /></button><button aria-label="缩小" onClick={() => setZoom((value) => Math.max(.7, value - .15))}><Minus /></button><button className="fit-all" onClick={() => setZoom(1)}><Maximize />适配全部</button></div>
      {locationMessage && <span className="map-location-message" role="status">{locationMessage}</span>}
      <span className="map-attribution">高德地图 · GCJ-02</span>
    </div>
  )
}

function clusterPosition(cluster: Record<string, unknown>) {
  const longitude = Number(cluster.longitude)
  const latitude = Number(cluster.latitude)
  return {
    left: 6 + ((longitude - 73.5) / (135.1 - 73.5)) * 86,
    top: 8 + (1 - (latitude - 18) / (53.6 - 18)) * 80,
  }
}

function markerBounds(markers: MapMarker[]) {
  const latitudes = markers.map((item) => item.latitude)
  const longitudes = markers.map((item) => item.longitude)
  return {
    minLat: Math.min(...latitudes), maxLat: Math.max(...latitudes),
    minLng: Math.min(...longitudes), maxLng: Math.max(...longitudes),
  }
}

function markerPosition(marker: MapMarker, bounds: ReturnType<typeof markerBounds>) {
  const lngSpan = bounds.maxLng - bounds.minLng || 1
  const latSpan = bounds.maxLat - bounds.minLat || 1
  return {
    left: 12 + ((marker.longitude - bounds.minLng) / lngSpan) * 70,
    top: 12 + (1 - (marker.latitude - bounds.minLat) / latSpan) * 67,
  }
}
