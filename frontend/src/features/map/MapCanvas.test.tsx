import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { MapMarker } from '../../lib/types'
import { MapCanvas } from './MapCanvas'

const markers: MapMarker[] = [
  {
    id: 'place-1',
    marker_id: 'marker-1',
    place_id: 'place-1',
    origin: 'AI_EXTRACTED',
    visibility: 'VISIBLE',
    name: '八市钟丽君满煎糕',
    canonical_name: '八市钟丽君满煎糕',
    place_type: 'FOOD',
    latitude: 24.462,
    longitude: 118.078,
    user_state: 'SAVED',
    summary: '传统小吃',
    address: '厦门市',
    preview_image: null,
    brief: {},
    source_count: 1,
  },
  {
    id: 'place-2',
    marker_id: 'marker-2',
    place_id: 'place-2',
    origin: 'AI_EXTRACTED',
    visibility: 'VISIBLE',
    name: '沙坡尾',
    canonical_name: '沙坡尾',
    place_type: 'SCENIC',
    latitude: 24.44,
    longitude: 118.09,
    user_state: 'DISCOVERED',
    summary: '滨海街区',
    address: '厦门市',
    preview_image: null,
    brief: {},
    source_count: 1,
  },
]

describe('MapCanvas', () => {
  it('renders every place as an independent marker and switches selection', () => {
    const onSelect = vi.fn()
    render(<MapCanvas markers={markers} clusters={[]} selectedId="place-1" onSelect={onSelect} viewport={{ bbox: [73.5, 18, 135.1, 53.6], zoom: 4 }} onViewportChange={vi.fn()} />)

    expect(screen.getByRole('button', { name: '查看 八市钟丽君满煎糕' })).toHaveAttribute('aria-pressed', 'true')
    fireEvent.click(screen.getByRole('button', { name: '查看 沙坡尾' }))
    expect(onSelect).toHaveBeenCalledWith('place-2')
  })

  it('keeps the overview usable when there are no matching markers', () => {
    render(<MapCanvas markers={[]} clusters={[]} selectedId={null} onSelect={vi.fn()} viewport={{ bbox: [73.5, 18, 135.1, 53.6], zoom: 4 }} onViewportChange={vi.fn()} />)
    expect(screen.getByLabelText('中国大陆地点地图总览')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '适配全部' })).toBeInTheDocument()
  })
})
