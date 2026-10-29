import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import { api } from '../../lib/api'
import { CoverTextPanel } from './CoverTextPanel'

afterEach(() => vi.restoreAllMocks())
it('separates unapplied extraction, highlights source region, and defaults to local OCR', async () => {
  vi.spyOn(api, 'videoCoverText').mockResolvedValue({ applied_to_current_note: false, notice: '', latest_extraction: { status: 'READY', cover_id: 'cover', cover_hash: 'a'.repeat(64), regions: [{ text: '8月份目的地推荐', bbox: [.1, .3, .7, .2], confidence: 1 }] } })
  const queue = vi.spyOn(api, 'queueCoverText').mockResolvedValue({ job_id: 'job-cover' })
  render(<MemoryRouter><QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><CoverTextPanel noteId="note" available /></QueryClientProvider></MemoryRouter>)
  fireEvent.click(screen.getByText('封面文字'))
  expect(await screen.findByText(/尚未用于当前笔记/)).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: '8月份目的地推荐' }))
  expect(screen.getByRole('button', { name: '8月份目的地推荐' })).toHaveAttribute('aria-pressed', 'true')
  fireEvent.click(screen.getByRole('button', { name: '提取封面文字' }))
  await waitFor(() => expect(queue).toHaveBeenCalledWith('note', false))
  expect(await screen.findByRole('link', { name: '查看提取任务' })).toHaveAttribute('href', '/tasks/job-cover')
})
