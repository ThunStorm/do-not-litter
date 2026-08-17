import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { MapMarker } from '../../lib/types'
import { MapCanvas } from './MapCanvas'

const markers: MapMarker[] = [
  {
    id: 'place-1',
    name: '八市钟丽君满煎糕',
    place_type: 'FOOD',
    latitude: 24.462,
    longitude: 118.078,
    user_state: 'SAVED',
    summary: '传统小吃',
  },
  {
    id: 'place-2',
    name: '沙坡尾',
    place_type: 'SCENIC',
    latitude: 24.44,
    longitude: 118.09,
    user_state: 'DISCOVERED',
    summary: '滨海街区',
  },
]

describe('MapCanvas', () => {
  it('renders every place as an independent marker and switches selection', () => {
    const onSelect = vi.fn()
    render(<MapCanvas markers={markers} selectedId="place-1" onSelect={onSelect} />)

    expect(screen.getByRole('button', { name: '查看 八市钟丽君满煎糕' })).toHaveAttribute('aria-pressed', 'true')
    fireEvent.click(screen.getByRole('button', { name: '查看 沙坡尾' }))
    expect(onSelect).toHaveBeenCalledWith('place-2')
  })

  it('keeps the overview usable when there are no matching markers', () => {
    render(<MapCanvas markers={[]} selectedId={null} onSelect={vi.fn()} />)
    expect(screen.getByLabelText('厦门地点地图总览')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '适配全部' })).toBeInTheDocument()
  })
})
