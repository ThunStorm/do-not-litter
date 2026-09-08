import { LocateFixed, Maximize, Minus, Plus } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import type { MapMarker } from '../../lib/types'
import { AmapLayer, type MapController } from './AmapLayer'

interface MapCanvasProps {
  markers: MapMarker[]
  selectedId: string | null
  onSelect: (id: string) => void
  viewport: { bbox: number[]; zoom: number }
  onViewportChange: (viewport: { bbox: number[]; zoom: number }) => void
  onStartPlaceSearch: () => void
  chinaReset: number
}

export function MapCanvas({ markers, selectedId, onSelect, viewport, onViewportChange, onStartPlaceSearch, chinaReset }: MapCanvasProps) {
  const controller = useRef<MapController>(null)
  const [ready, setReady] = useState(false)
  useEffect(() => { if (chinaReset) controller.current?.fitChina() }, [chinaReset])
  return (
    <div className="map-canvas" aria-label="中国大陆地点地图总览">
      <AmapLayer ref={controller} markers={markers} selectedId={selectedId} onSelect={onSelect} viewport={viewport} onReady={setReady} onViewportChange={onViewportChange} />
      <div className="map-canvas__tools">
        <button aria-label="定位" disabled={!ready} onClick={() => controller.current?.locate()}><LocateFixed /></button>
        <button aria-label="放大" disabled={!ready} onClick={() => controller.current?.zoomIn()}><Plus /></button>
        <button aria-label="缩小" disabled={!ready} onClick={() => controller.current?.zoomOut()}><Minus /></button>
        <button className="fit-all" disabled={!ready} onClick={() => controller.current?.fitChina()}><Maximize />全国视野</button>
      </div>
      <span className="map-attribution">高德地图 · GCJ-02</span>
      <button className="map-add-marker button button--primary" disabled={!ready} onClick={onStartPlaceSearch}><Plus />添加地点</button>
    </div>
  )
}
