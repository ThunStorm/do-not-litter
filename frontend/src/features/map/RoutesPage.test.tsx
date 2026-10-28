import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { expect, it, vi } from 'vitest'
import { api } from '../../lib/api'
import { RoutesPage } from './RoutesPage'
vi.mock('../../lib/api', () => ({ api: { routes: vi.fn(), routeGuides: vi.fn(), copyRouteGuide: vi.fn() } }))
it('keeps source stops, uncertainty and navigation boundary visible and copies only confirmed stops', async () => {
  vi.mocked(api.routes).mockResolvedValue([])
  vi.mocked(api.routeGuides).mockResolvedValue([{ id: 'note:rg', guide_id: 'rg', name: '骑行来源', note_id: 'note', version_id: 'v1', mode: 'CYCLING', sequence_kind: 'EXPLICIT_SEQUENCE', display_notice: '站点顺序示意，非道路导航', review_status: 'NEEDS_REVIEW', stops: [{ raw_name: '码头', place_id: 'p1', review_status: 'CONFIRMED' }, { raw_name: '古镇', place_id: 'p2', review_status: 'CONFIRMED' }], evidence: { quote: '推荐骑行码头到古镇', segment_ids: ['s'] }, conditions: [], evidence_url: '/video-notes/note', source_title: '来源视频' }])
  vi.mocked(api.copyRouteGuide).mockResolvedValue({ id: 'route' })
  render(<QueryClientProvider client={new QueryClient()}><MemoryRouter><RoutesPage /></MemoryRouter></QueryClientProvider>)
  expect(await screen.findByText('骑行来源 · 骑行')).toBeVisible()
  expect(screen.getByText('站点顺序示意，非道路导航')).toBeVisible()
  expect(screen.getByText(/作者明确站序：码头 → 古镇/)).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: '复制为个人路线' }))
  await waitFor(() => expect(api.copyRouteGuide).toHaveBeenCalledWith('note', 'rg', 'v1'))
  expect(await screen.findByRole('status')).toHaveTextContent('已复制')
})
