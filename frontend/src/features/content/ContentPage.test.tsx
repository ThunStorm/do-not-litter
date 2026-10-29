import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'

import { api } from '../../lib/api'
import { ContentPage } from './ContentPage'

afterEach(() => vi.restoreAllMocks())

it('passes categories and searches to the API and labels video notes correctly', async () => {
  const content = vi.spyOn(api, 'content').mockResolvedValue([{ id: 'content-video', content_type: 'VIDEO_NOTE', title: '真实视频笔记', summary: '', status: 'COMPLETED', user_state: 'DISCOVERED', structured: {}, updated_at: '' }])
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={client}><MemoryRouter><ContentPage /></MemoryRouter></QueryClientProvider>)
  await screen.findByText('真实视频笔记')
  expect(screen.getByText('视频笔记 · 已完成')).toBeVisible()
  fireEvent.click(screen.getByRole('tab', { name: '旅行' }))
  await waitFor(() => expect(content).toHaveBeenLastCalledWith('TRAVEL', ''))
  fireEvent.click(screen.getByRole('tab', { name: '视频笔记' }))
  await waitFor(() => expect(content).toHaveBeenLastCalledWith('VIDEO_NOTE', ''))
  fireEvent.change(screen.getByPlaceholderText('搜索标题、地点或来源'), { target: { value: '视频' } })
  await waitFor(() => expect(content).toHaveBeenLastCalledWith('VIDEO_NOTE', '视频'))
  content.mockResolvedValue([])
  fireEvent.click(screen.getByRole('tab', { name: '招聘' }))
  await screen.findByText('没有符合条件的内容')
  expect(content).toHaveBeenLastCalledWith('RECRUITMENT', '视频')
  client.clear()
})
