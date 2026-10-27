import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { expect, it, vi } from 'vitest'

import { api } from '../../lib/api'
import { PlaceReviewCard } from './PlaceReviewCard'

vi.mock('../../lib/api', () => ({ api: { confirmPlaceReview: vi.fn() } }))
it('reports the confirmed place id and offers a map location link', async () => {
  vi.mocked(api.confirmPlaceReview).mockResolvedValue({ place_id: 'p-new', mention_id: 'm-new', resolution_status: 'CONFIRMED' })
  const done = vi.fn()
  const client = new QueryClient()
  const invalidations = vi.spyOn(client, 'invalidateQueries')
  const review = { mention_id: 'm-new', name: '翠湖', revision: 0, visit_intent: 'NOT_RECOMMENDED', recommendation_summary: { status: 'NOT_RECOMMENDED', source_opinions: [] }, candidates: [{ provider_id: 'poi', name: '翠湖公园', address: '昆明', score: 90, match_reasons: ['名称匹配'] }], review_context: {}, source_context: { canonical_url: 'https://www.bilibili.com/video/BVfixture', video_title: '公园推荐', start_ms: 0, end_ms: 1000, transcript_context: [], quote: '翠湖' } }
  render(<QueryClientProvider client={client}><MemoryRouter><PlaceReviewCard review={review as never} onConfirmed={done} /></MemoryRouter></QueryClientProvider>)
  fireEvent.click(screen.getByRole('button', { name: '确认地点位置' }))
  await waitFor(() => expect(done).toHaveBeenCalledWith('p-new'))
  expect(await screen.findByRole('link', { name: '在地图查看' })).toHaveAttribute('href', '/map?place=p-new')
  expect(screen.getByText('不推荐')).toBeInTheDocument()
  expect(invalidations).toHaveBeenCalledWith({ queryKey: ['map'] })
})
