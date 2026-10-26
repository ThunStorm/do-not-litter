import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, expect, it, vi } from 'vitest'
import { api } from '../../lib/api'
import { PlaceDetailPage } from './PlaceDetailPage'

vi.mock('../../lib/api', () => ({ api: { place: vi.fn(), placeDestinations: vi.fn(), placeHistory: vi.fn(), updatePlaceOverlay: vi.fn(), updatePlaceNote: vi.fn() } }))
let detail: Record<string, unknown>
beforeEach(() => {
  vi.clearAllMocks()
  detail = { id: 'p', name: '雾凇岛', place_type: 'SCENIC_AREA', user_state: 'SAVED', address: '松花江畔', coordinates: [126.5, 43.8], coordinate_system: 'GCJ02', external_poi_id: 'poi-test',
    display: { name: '雾凇岛', place_type: 'SCENIC_AREA', tags: ['冬季'], revision: 0 }, note: { markdown: '', revision: 0 },
    travel_brief: { timing: '这组雾凇在视频中按冬季介绍。', highlights: ['视频提到，江边雾凇很有特色。'], warnings: ['视频提醒注意低温。'] },
    source_notes: [{ note_id: 'note-proof', version_id: 'v1', title: '吉林冬日记录' }], visit_windows: [],
    knowledge: { prices: [{ value_text: '视频提到，住宿成本较高。', state: 'SINGLE_SOURCE', current: true, observations: [] }], queues: [{ value_text: '需要提前预约。', state: 'CONFLICT', current: true, observations: [] }] }, visual_facts: [] }
  vi.mocked(api.place).mockImplementation(async () => detail as never)
  vi.mocked(api.placeDestinations).mockResolvedValue([])
  vi.mocked(api.placeHistory).mockResolvedValue([{ id: 'history', message: '修改了名称', created_at: '2026-10-25T00:00:00Z' }] as never)
  vi.mocked(api.updatePlaceOverlay).mockImplementation(async (_id, value) => { detail = { ...detail, display: { name: value.display_name, place_type: value.override_place_type, tags: value.custom_tags, revision: 1 } }; return {} as never })
  vi.mocked(api.updatePlaceNote).mockImplementation(async (_id, markdown) => { detail = { ...detail, note: { markdown, revision: 1 } }; return {} as never })
})
function show() { return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={['/places/p']}><Routes><Route path="/places/:placeId" element={<PlaceDetailPage />} /></Routes></MemoryRouter></QueryClientProvider>) }
it('expands reading sources and history and restores the bottom action group', async () => {
  show()
  expect(await screen.findByRole('heading', { name: '雾凇岛' })).toBeInTheDocument()
  expect(screen.getByText('冬季观赏雾凇。')).toBeVisible()
  expect(screen.getByText('注意低温。')).toBeVisible()
  expect(screen.getByText('住宿成本较高。')).toBeVisible()
  expect(screen.getByText(/资料存在差异/)).toBeVisible()
  expect(screen.getByRole('link', { name: '在高德中打开' })).toHaveAttribute('href', expect.stringContaining('126.5,43.8'))
  expect(screen.getByRole('link', { name: '吉林冬日记录' })).toBeVisible()
  expect(screen.getByRole('heading', { name: '时间依据' })).toBeVisible()
  expect(screen.getByRole('button', { name: '在地图中隐藏' })).toBeVisible()
  expect(await screen.findByRole('link', { name: '吉林冬日记录' })).toHaveAttribute('href', '/video-notes/note-proof')
  expect(await screen.findByText('修改了名称')).toBeVisible()
  expect(api.placeHistory).toHaveBeenCalledWith('p')
  const actions = screen.getByRole('group', { name: '地点操作' })
  expect(within(actions).getAllByRole('button').map((button) => button.textContent)).toEqual(['不感兴趣', '不喜欢', '喜欢', '去过', '想去'])
  expect(screen.getAllByRole('button', { name: '不感兴趣' })).toHaveLength(1)
  expect(screen.getByRole('region', { name: '编辑历史记录' }).closest('details')).toBeNull()
})
it('retains the edit and save flow behind the secondary entry', async () => {
  show()
  fireEvent.click(await screen.findByRole('button', { name: '编辑地点' }))
  fireEvent.change(screen.getByPlaceholderText('保留为空则使用地点原名'), { target: { value: '江边雾凇' } })
  fireEvent.change(screen.getByPlaceholderText('记录自己的到访建议、提醒或感受'), { target: { value: '个人保暖记录' } })
  fireEvent.click(screen.getByRole('button', { name: '保存修改' }))
  expect(await screen.findByRole('status')).toHaveTextContent('已保存')
  await waitFor(() => expect(api.updatePlaceOverlay).toHaveBeenCalledWith('p', expect.objectContaining({ display_name: '江边雾凇', expected_revision: 0 })))
  expect(api.updatePlaceNote).toHaveBeenCalledWith('p', '个人保暖记录', 0)
  await waitFor(() => expect(vi.mocked(api.placeHistory).mock.calls.length).toBeGreaterThanOrEqual(2))
  expect(await screen.findByRole('heading', { name: '江边雾凇' })).toBeInTheDocument()
  expect(screen.getByText('个人保暖记录')).toBeVisible()
})
