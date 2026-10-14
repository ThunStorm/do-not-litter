import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { PlaceVisitWindow } from '../../lib/types'
import { VisitWindowList } from './VisitWindowList'

describe('VisitWindowList source boundaries', () => {
  it('labels title and transcript separately and removes only the manual window', () => {
    const remove = vi.fn()
    const windows = ['TITLE_CONTEXT', 'SOURCE_FACT', 'USER'].map((provenance, index): PlaceVisitWindow => ({
      id: `window-${index}`, provenance, month: 11, season: null, month_segment: null, day_time_slot: null,
      period_type: 'BEST_VISIT', suitability: 'RECOMMENDED', source_text: `原始出处${index}`, segment_ids: provenance === 'SOURCE_FACT' ? ['segment'] : [], confidence: 0.75, status: 'ACTIVE',
    }))
    render(<VisitWindowList windows={windows} onRemove={remove} />)
    expect(screen.getByText(/原始出处0 · 来自视频标题/)).toBeTruthy()
    expect(screen.getByText(/原始出处1 · 正文原句佐证/)).toBeTruthy()
    expect(screen.getAllByRole('button', { name: '移除' })).toHaveLength(1)
    fireEvent.click(screen.getByRole('button', { name: '移除' }))
    expect(remove).toHaveBeenCalledWith('window-2')
    expect(screen.queryByText('window-0')).toBeNull()
  })
})
