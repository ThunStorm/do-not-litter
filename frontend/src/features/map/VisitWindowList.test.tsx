import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
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
    expect(screen.getByText('视频标题中的时间线索').closest('li')).toHaveTextContent('原始出处0')
    expect(screen.getByText('视频原句').closest('li')).toHaveTextContent('原始出处1')
    expect(screen.getAllByRole('button', { name: '移除' })).toHaveLength(1)
    fireEvent.click(screen.getByRole('button', { name: '移除' }))
    expect(remove).toHaveBeenCalledWith('window-2')
    expect(screen.queryByText('window-0')).toBeNull()
  })
})

it('keeps theme evidence immutable and links its note', () => {
  const item: PlaceVisitWindow = { id: 'theme-window', provenance: 'THEME_CONTEXT', source_kind: 'THEME_CONTEXT', note_id: 'note-theme', month: null, season: null, month_segment: null, day_time_slot: null, period_type: 'BEST_VISIT', suitability: 'RECOMMENDED', source_text: '暑假推荐几个小城', segment_ids: ['intro'], confidence: 0.8, status: 'ACTIVE' }
  render(<MemoryRouter><VisitWindowList windows={[item]} onRemove={vi.fn()} /></MemoryRouter>)
  expect(screen.getByText('视频推荐主题')).toBeVisible()
  expect(screen.getByRole('link', { name: '查看主题来源' })).toHaveAttribute('href', '/video-notes/note-theme')
  expect(screen.queryByRole('button', { name: '移除' })).toBeNull()
})
