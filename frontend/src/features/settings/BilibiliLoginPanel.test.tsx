import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it, vi } from 'vitest'

import { api } from '../../lib/api'
import { BilibiliLoginPanel } from './BilibiliLoginPanel'

vi.mock('../../lib/api', () => ({
  api: {
    bilibiliSettings: vi.fn(),
    startBilibiliLogin: vi.fn(),
    pollBilibiliLogin: vi.fn(),
  },
}))

describe('BilibiliLoginPanel', () => {
  it('starts an embedded QR login without exposing a Cookie input', async () => {
    vi.mocked(api.bilibiliSettings).mockResolvedValue({
      cookie_saved: false,
      account_name: null,
      verified_at: null,
    })
    vi.mocked(api.startBilibiliLogin).mockResolvedValue({
      session_id: 'login-fixture',
      qr_url: 'https://passport.bilibili.com/fixture',
      expires_at: '2026-08-30T00:00:00Z',
      status: 'WAITING_SCAN',
    })
    vi.mocked(api.pollBilibiliLogin).mockResolvedValue({
      status: 'WAITING_SCAN',
      message: '等待扫码',
    })
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    render(<QueryClientProvider client={queryClient}><BilibiliLoginPanel /></QueryClientProvider>)

    expect(screen.queryByLabelText('Cookie 请求头值')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '扫码登录' }))

    await waitFor(() => expect(api.startBilibiliLogin).toHaveBeenCalledTimes(1))
    await waitFor(() => expect(api.pollBilibiliLogin).toHaveBeenCalledWith('login-fixture'))
    expect(screen.getByTitle('Bilibili 登录二维码')).toBeInTheDocument()
    expect(screen.getByText('打开哔哩哔哩 App 扫码')).toBeInTheDocument()
  })
})
