import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { useEffect } from 'react'
import type { MapMarker } from '../../lib/types'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, expect, it, vi } from 'vitest'

import { api } from '../../lib/api'
import { MapOverviewPage } from './MapOverviewPage'

vi.mock('./MapCanvas', () => ({ MapCanvas: function MapCanvas({ markers, onSelect, onClusterSelect, onClustersChange, onViewportChange }: { markers: MapMarker[]; onSelect: (id: string) => void; onClusterSelect?: (markers: MapMarker[]) => void; onClustersChange?: (groups: MapMarker[][]) => void; onViewportChange: (value: { bbox: number[]; zoom: number }) => void }) {
  useEffect(() => { onClustersChange?.(markers.length > 1 ? [markers] : []) }, [markers, onClustersChange])
  return <><button onClick={() => onSelect('p1')}>查看测试地点</button><button onClick={() => onClusterSelect?.(markers)}>测试聚合</button><button onClick={() => onViewportChange({ bbox: [73.5, 18, 135.1, 53.6], zoom: 5 })}>测试放大刷新</button><button onClick={() => onClustersChange?.([])}>测试聚合散开</button></>
} }))
vi.mock('../../lib/api', () => ({ api: { map: vi.fn(), routes: vi.fn(), placeReviewCount: vi.fn(), updateRoute: vi.fn() } }))
beforeEach(() => { sessionStorage.clear(); vi.clearAllMocks() })
it('keeps route destination separate from filtering and presents compact timing evidence', async () => {
  vi.mocked(api.map).mockImplementation(async (params) => ({ markers: [{ id: 'p1', name: '秋山', place_type: 'PARK', user_state: 'SAVED', address: '山路', source_count: 1, timing_status: 'EVIDENCE', visit_window_summary: '10月15–25日 · 最佳', travel_brief: { timing: '视频推荐十月十五到二十五看秋色。', warnings: ['视频提醒避开假期。'] }, visit_window_evidence: [{ source_kind: 'TRANSCRIPT', source_text: '十月十五到二十五最佳' }], recommendation: { reasons: [{ text: '重复时间', trace: { summary: '10月最佳' } }] } }], selected_place_id: params?.selectedPlaceId, visible_places: 1 }) as never)
  vi.mocked(api.routes).mockResolvedValue([{ id: 'r1', name: '秋游', places: [] }, { id: 'r2', name: '周末', places: [] }] as never)
  vi.mocked(api.placeReviewCount).mockResolvedValue({ count: 0 })
  vi.mocked(api.updateRoute).mockResolvedValue({} as never)
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter><MapOverviewPage /></MemoryRouter></QueryClientProvider>)
  fireEvent.click(screen.getByRole('button', { name: '查看测试地点' }))
  expect(await screen.findByText('推荐十月十五到二十五看秋色。')).toBeInTheDocument()
  expect(screen.getByText('避开假期。')).toBeInTheDocument()
  expect(screen.queryByText('10月15–25日 · 最佳')).not.toBeInTheDocument()
  expect(screen.queryByText('重复时间')).not.toBeInTheDocument()
  fireEvent.click(screen.getByText('加入路线', { selector: 'summary' }))
  fireEvent.click(await screen.findByRole('button', { name: '目标路线' }))
  fireEvent.click(screen.getByRole('option', { name: '周末' }))
  expect(vi.mocked(api.map).mock.calls.every(([params]) => !params?.routeId)).toBe(true)
  fireEvent.click(screen.getByRole('button', { name: '加入路线' }))
  await waitFor(() => expect(api.updateRoute).toHaveBeenCalledWith('r2', ['p1']))
  expect(screen.getByRole('link', { name: '查看详情' })).toHaveAttribute('href', '/places/p1')
  fireEvent.click(screen.getByRole('button', { name: '关闭地点预览' }))
  await waitFor(() => expect(screen.queryByRole('region', { name: '地点预览' })).not.toBeInTheDocument())
})
it('opens a confirmed place with national scope despite saved month and route filters', async () => {
  sessionStorage.setItem('zhijian-map-filters', JSON.stringify({ month: '10', routeId: 'old-route', query: '厦门' }))
  sessionStorage.setItem('zhijian-map-viewport', JSON.stringify({ bbox: [118, 24, 119, 25], zoom: 12 }))
  vi.mocked(api.map).mockImplementation(async (params) => ({ markers: [{ id: 'new-place', name: '新确认地点', place_type: 'PARK', user_state: 'SAVED', source_count: 1 }], selected_place_id: params?.selectedPlaceId, visible_places: 1 }) as never)
  vi.mocked(api.routes).mockResolvedValue([])
  vi.mocked(api.placeReviewCount).mockResolvedValue({ count: 0 })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={['/map?place=new-place']}><MapOverviewPage /></MemoryRouter></QueryClientProvider>)
  expect(await screen.findByRole('heading', { name: '新确认地点' })).toBeInTheDocument()
  expect(api.map).toHaveBeenCalledWith(expect.objectContaining({ selectedPlaceId: 'new-place', month: '', routeId: '', query: '', zoom: 4, bbox: [73.5, 18, 135.1, 53.6] }))
})

it('retains a cluster through viewport loading and closes it when the real group breaks up', async () => {
  const markers = ['p1', 'p2'].map((id) => ({ id, name: id, source_count: 1, travel_brief: { timing: '视频介绍冬季雾凇。' } })) as MapMarker[]
  let resolveRefresh: (value: never) => void = () => {}
  vi.mocked(api.map).mockResolvedValueOnce({ markers, selected_place_id: null } as never).mockImplementation(() => new Promise((resolve) => { resolveRefresh = resolve }))
  vi.mocked(api.routes).mockResolvedValue([])
  vi.mocked(api.placeReviewCount).mockResolvedValue({ count: 0 })
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter><MapOverviewPage /></MemoryRouter></QueryClientProvider>)
  await waitFor(() => expect(api.map).toHaveBeenCalledTimes(1))
  await waitFor(() => expect(screen.getByRole('button', { name: '测试聚合' })).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: '测试聚合' }))
  expect(await screen.findByRole('region', { name: '聚合地点预览' })).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: '测试放大刷新' }))
  await waitFor(() => expect(api.map).toHaveBeenCalledTimes(2))
  expect(screen.getByRole('region', { name: '聚合地点预览' })).toBeInTheDocument()
  resolveRefresh({ markers, selected_place_id: null } as never)
  fireEvent.click(screen.getByRole('button', { name: '测试聚合散开' }))
  await waitFor(() => expect(screen.queryByRole('region', { name: '聚合地点预览' })).not.toBeInTheDocument())
})
