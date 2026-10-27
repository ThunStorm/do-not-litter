import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { expect, it, vi } from 'vitest'

import { api } from '../../lib/api'
import { PlaceReviewCard } from './PlaceReviewCard'

vi.mock('../../lib/api', () => ({ api: { confirmPlaceReview: vi.fn(), searchPlaceReview: vi.fn() } }))
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


it('keeps search open and uses the new revision for a subsequent confirmation', async () => {
  vi.mocked(api.searchPlaceReview).mockResolvedValue({ revision: 1, candidates: [{ provider_id: 'new-poi', name: '玉龙雪山', address: '丽江', city: '丽江', district: '', typecode: '110202', score: 90, match_reasons: ['名称匹配'] }] })
  vi.mocked(api.confirmPlaceReview).mockResolvedValue({ place_id: 'p-new', mention_id: 'm-new', resolution_status: 'CONFIRMED' })
  const review = { mention_id: 'm-new', name: '玉龙雪山', suggested_name: '玉龙雪山', revision: 0, candidates: [], review_context: {}, source_context: { canonical_url: '', video_title: '视频', transcript_context: [] } }
  render(<QueryClientProvider client={new QueryClient()}><MemoryRouter><PlaceReviewCard review={review as never} /></MemoryRouter></QueryClientProvider>)
  fireEvent.click(screen.getByRole('button', { name: '搜索 POI' }))
  fireEvent.click(screen.getByRole('button', { name: '重新搜索' }))
  expect(await screen.findByText('搜索到 1 个候选')).toBeInTheDocument()
  expect(screen.getByText('手动搜索结果')).toBeInTheDocument()
  expect(screen.getByRole('textbox', { name: '搜索 POI 名称' })).toHaveValue('玉龙雪山')
  fireEvent.click(screen.getByRole('button', { name: '确认地点位置' }))
  await waitFor(() => expect(api.confirmPlaceReview).toHaveBeenLastCalledWith('m-new', 'new-poi', 1))
})

it('keeps the search input visible and explains an empty response or error', async () => {
  vi.mocked(api.searchPlaceReview).mockResolvedValueOnce({ revision: 1, candidates: [] }).mockRejectedValueOnce(new Error('请求失败：409'))
  const review = { mention_id: 'm-new', name: '景区', suggested_name: '景区', revision: 0, candidates: [], review_context: {}, source_context: { canonical_url: '', video_title: '视频', transcript_context: [] } }
  render(<QueryClientProvider client={new QueryClient()}><MemoryRouter><PlaceReviewCard review={review as never} /></MemoryRouter></QueryClientProvider>)
  fireEvent.click(screen.getByRole('button', { name: '搜索 POI' }))
  fireEvent.click(screen.getByRole('button', { name: '重新搜索' }))
  expect(await screen.findByText('没有找到匹配地点，请尝试其他名称。')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: '重新搜索' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('地点信息已更新')
  expect(screen.getByRole('textbox', { name: '搜索 POI 名称' })).toBeInTheDocument()
})

it('locks editing and competing actions while a search is pending', async () => {
  let finish: (value: { revision: number; candidates: [] }) => void = () => {}
  vi.mocked(api.searchPlaceReview).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve }))
  const calls = vi.mocked(api.searchPlaceReview).mock.calls.length
  const review = { mention_id: 'pending', name: '翠湖', suggested_name: '翠湖', revision: 0, candidates: [{ provider_id: 'p', name: '翠湖公园', address: '昆明', score: 90, match_reasons: [] }], review_context: {}, source_context: { canonical_url: '', video_title: '来源', transcript_context: [] } }
  render(<QueryClientProvider client={new QueryClient()}><MemoryRouter><PlaceReviewCard review={review as never} /></MemoryRouter></QueryClientProvider>)
  fireEvent.click(screen.getByRole('button', { name: '搜索 POI' }))
  const form = screen.getByRole('textbox', { name: '搜索 POI 名称' }).closest('form')!
  fireEvent.submit(form)
  expect(await screen.findByRole('button', { name: '正在搜索…' })).toBeDisabled()
  expect(screen.getByRole('textbox', { name: '搜索 POI 名称' })).toBeDisabled()
  expect(screen.getByRole('button', { name: '确认地点位置' })).toBeDisabled()
  expect(screen.getByRole('button', { name: '不是地点' })).toBeDisabled()
  expect(screen.getByRole('button', { name: '取消' })).toBeDisabled()
  fireEvent.submit(form)
  expect(api.searchPlaceReview).toHaveBeenCalledTimes(calls + 1)
  finish({ revision: 1, candidates: [] })
  expect(await screen.findByText('没有找到匹配地点，请尝试其他名称。')).toBeInTheDocument()
  expect(screen.getByRole('textbox', { name: '搜索 POI 名称' })).toBeEnabled()
})
