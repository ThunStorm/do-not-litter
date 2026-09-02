import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import { api } from '../../lib/api'
import { TaskDetailPage } from './TaskDetailPage'

vi.mock('../../lib/api', () => ({
  api: {
    job: vi.fn(),
    jobAiUsage: vi.fn(),
    replayOptions: vi.fn(),
    bilibiliSettings: vi.fn(),
    retryJobFromStep: vi.fn(),
    skipJobLoginStep: vi.fn(),
    retryJobFull: vi.fn(),
    cancelJob: vi.fn(),
    startBilibiliLogin: vi.fn(),
    pollBilibiliLogin: vi.fn(),
  },
}))

describe('TaskDetailPage login recovery', () => {
  it('offers QR login recovery and an explicit screenshot skip', async () => {
    vi.mocked(api.job).mockResolvedValue({
      id: 'job-login', job_type: 'TRAVEL', status: 'NEEDS_USER', current_step: 'DOWNLOAD_VIDEO_FOR_FRAMES', progress: 94, title: '测试视频', error: 'Bilibili 登录已失效', error_code: 'VIDEO_LOGIN_REQUIRED', created_at: '2026-08-30T00:00:00Z', started_at: '2026-08-30T00:00:00Z', finished_at: '2026-08-30T00:01:00Z', retry_count: 0, worker_id: null, heartbeat_at: null, last_activity_at: '2026-08-30T00:01:00Z', current_step_status: 'FAILED', current_step_started_at: '2026-08-30T00:00:30Z', current_step_message: null, runtime_state: 'IDLE', last_activity_age_seconds: 0, last_activity_source: null, completion_summary: null, model_step: null, provider: null, model: null,
      steps: [{ name: 'DOWNLOAD_VIDEO_FOR_FRAMES', status: 'FAILED', progress: 0, error: '登录失效', started_at: '2026-08-30T00:00:30Z', finished_at: '2026-08-30T00:01:00Z', input: {}, output: {} }],
      events: [],
    })
    vi.mocked(api.jobAiUsage).mockResolvedValue({ total: { calls: 0, input_tokens: 0, output_tokens: 0, cached_tokens: 0, duration_ms: 0 }, local: { calls: 0, input_tokens: 0, output_tokens: 0, cached_tokens: 0, duration_ms: 0 }, remote: { calls: 0, input_tokens: 0, output_tokens: 0, cached_tokens: 0, duration_ms: 0 }, by_stage: {}, by_model: {}, cache: { hits: 0 }, escalations: 0 })
    vi.mocked(api.replayOptions).mockResolvedValue({ step_replay_available: true, replay_from_step: 'DOWNLOAD_VIDEO_FOR_FRAMES', replayable_until: '2026-08-31T00:00:00Z', remaining_seconds: 86400, reused_steps: ['CORRECT_TRANSCRIPT'], rerun_steps: ['DOWNLOAD_VIDEO_FOR_FRAMES'], reason: null, code: null, full_replay_available: true, full_replay_reason: null, login_required: true, skip_step_available: true, skip_step_reason: null })
    vi.mocked(api.bilibiliSettings).mockResolvedValue({ cookie_saved: true, account_name: '旧登录', verified_at: '2026-08-29T00:00:00Z' })
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })

    render(<QueryClientProvider client={queryClient}><MemoryRouter initialEntries={['/tasks/job-login']}><Routes><Route path="/tasks/:jobId" element={<TaskDetailPage />} /></Routes></MemoryRouter></QueryClientProvider>)

    expect(await screen.findByText('登录状态失效，任务已安全暂停')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '跳过截图并继续' })).toBeEnabled()
    expect(screen.getByRole('button', { name: '扫码登录后可继续' })).toBeDisabled()
    expect(screen.queryByLabelText('Cookie 请求头值')).not.toBeInTheDocument()
  })
})
