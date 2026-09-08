import { fireEvent, render, waitFor } from '@testing-library/react'
import { createRef } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { api } from '../../lib/api'
import type { MapMarker } from '../../lib/types'
import { AmapLayer, type MapController } from './AmapLayer'
import { groupMarkersByPixel } from './markerClustering'

vi.mock('../../lib/api', () => ({ api: { mapBootstrap: vi.fn() } }))

const markers: MapMarker[] = [{
  id: 'place-1', marker_id: 'marker-1', place_id: 'place-1', origin: 'AI_EXTRACTED', visibility: 'VISIBLE', name: '八市钟丽君满煎糕', canonical_name: '八市钟丽君满煎糕', place_type: 'FOOD', latitude: 24.462, longitude: 118.078, user_state: 'SAVED', summary: '传统小吃', address: '厦门市', preview_image: null, brief: {}, source_count: 1,
}]

describe('AmapLayer lifecycle', () => {
  it('clusters only while marker footprints overlap at the current zoom', () => {
    const nearby = { ...markers[0], id: 'place-2', longitude: 118.0781 }
    expect(groupMarkersByPixel([markers[0], nearby], 8)).toHaveLength(1)
    expect(groupMarkersByPixel([markers[0], nearby], 20)).toHaveLength(2)
  })

  it('keeps one map instance while data, selection, and viewport change', async () => {
    const map = {
      add: vi.fn(), remove: vi.fn(), destroy: vi.fn(), on: vi.fn(), off: vi.fn(), getBounds: vi.fn(), getZoom: vi.fn(() => 8), setZoomAndCenter: vi.fn(), zoomIn: vi.fn(), zoomOut: vi.fn(), setFitView: vi.fn(),
    }
    const AMap = {
      Map: vi.fn(() => map), Marker: vi.fn(() => ({ on: vi.fn() })), MarkerCluster: vi.fn(() => ({ setMap: vi.fn() })), Pixel: vi.fn(),
    }
    window.AMap = AMap as never
    vi.mocked(api.mapBootstrap).mockResolvedValue({ js_key: 'test-key', security_code: '', security_code_configured: false, web_service_configured: false, default_viewport: { bbox: [73.5, 18, 135.1, 53.6], zoom: 4 }, diagnostics: [] })
    const controller = createRef<MapController>()
    const props = { selectedId: null, onSelect: vi.fn(), onReady: vi.fn(), onViewportChange: vi.fn() }
    const view = render(<AmapLayer ref={controller} {...props} markers={markers} viewport={{ bbox: [73.5, 18, 135.1, 53.6], zoom: 4 }} />)

    await waitFor(() => expect(AMap.Map).toHaveBeenCalledTimes(1))
    await waitFor(() => expect(AMap.Marker).toHaveBeenCalledTimes(1))
    view.rerender(<AmapLayer ref={controller} {...props} markers={markers} selectedId="place-1" viewport={{ bbox: [73.5, 18, 135.1, 53.6], zoom: 4 }} />)
    expect(AMap.Marker).toHaveBeenCalledTimes(1)
    view.rerender(<AmapLayer ref={controller} {...props} markers={[...markers, { ...markers[0], id: 'place-2', name: '沙坡尾' }]} selectedId="place-2" viewport={{ bbox: [110, 20, 122, 30], zoom: 8 }} />)

    expect(AMap.Map).toHaveBeenCalledTimes(1)
    await waitFor(() => expect(map.setZoomAndCenter).toHaveBeenCalledWith(8, [116, 25]))
    controller.current?.zoomIn()
    controller.current?.zoomOut()
    controller.current?.fitChina()
    expect(map.zoomIn).toHaveBeenCalledOnce()
    expect(map.zoomOut).toHaveBeenCalledOnce()
    expect(map.setZoomAndCenter).toHaveBeenCalled()
  })

  it('opens the place preview when the rendered marker is clicked', async () => {
    const markerOptions: Array<{ content: HTMLButtonElement }> = []
    const map = { add: vi.fn(), remove: vi.fn(), destroy: vi.fn(), on: vi.fn(), off: vi.fn(), getBounds: vi.fn(), getZoom: vi.fn(() => 8), setZoomAndCenter: vi.fn(), zoomIn: vi.fn(), zoomOut: vi.fn(), setFitView: vi.fn() }
    window.AMap = { Map: vi.fn(() => map), Marker: vi.fn((options) => { markerOptions.push(options); return { on: vi.fn() } }), Pixel: vi.fn() } as never
    vi.mocked(api.mapBootstrap).mockResolvedValue({ js_key: 'test-key', security_code: '', security_code_configured: false, web_service_configured: false, default_viewport: { bbox: [73.5, 18, 135.1, 53.6], zoom: 4 }, diagnostics: [] })
    const onSelect = vi.fn()
    render(<AmapLayer markers={markers} selectedId={null} onSelect={onSelect} onReady={vi.fn()} onViewportChange={vi.fn()} viewport={{ bbox: [73.5, 18, 135.1, 53.6], zoom: 4 }} />)

    await waitFor(() => expect(markerOptions).toHaveLength(1))
    fireEvent.click(markerOptions[0].content)
    expect(onSelect).toHaveBeenCalledWith('place-1')
  })
})
