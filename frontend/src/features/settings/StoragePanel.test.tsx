import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { api } from '../../lib/api'
import { StoragePanel } from './StoragePanel'

vi.mock('../../lib/api', () => ({ api: { storageStatus: vi.fn(), storagePlan: vi.fn(), logPolicyPreview: vi.fn(), logPolicyApply: vi.fn() } }))
it('keeps root plans pending and requires an impact preview before policy apply', async () => {
  const policy = { version: 1, compress: true, compression_delay_hours: 48, retention_days: 30, volume_bytes: 10485760, capacity_bytes: 1073741824, bootstrap_retention_days: 7, bootstrap_capacity_bytes: 134217728, low_space_bytes: 1073741824 }
  vi.mocked(api.storageStatus).mockResolvedValue({ root: '/existing/data', generation: 1, configured_generation: 1, registered: true, plan: {}, state: {}, exceptions: ['Keychain'], policy, handler_versions: [1], maintenance: {}, log_summary: { archived_bytes: 0, oldest_closed_at: null } } as never)
  vi.mocked(api.storagePlan).mockResolvedValue({ stage: 'SCANNING' })
  vi.mocked(api.logPolicyPreview).mockResolvedValue({ token: 'x'.repeat(64), delete_count: 2, delete_bytes: 1000, archived_bytes: 1000, oldest_closed_at: null })
  vi.mocked(api.logPolicyApply).mockResolvedValue({ message: '策略已应用' })
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><StoragePanel /></QueryClientProvider>)
  expect(await screen.findByText('/existing/data')).toBeVisible()
  expect(screen.queryByRole('button', { name: '应用此日志策略' })).not.toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('拟切换的服务器目录'), { target: { value: '/Volumes/资料/新目录' } })
  fireEvent.click(screen.getByRole('button', { name: '预检并保存待应用方案' }))
  await waitFor(() => expect(api.storagePlan).toHaveBeenCalledWith('/Volumes/资料/新目录'))
  expect(screen.getByText('/existing/data')).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: '预览清理影响' }))
  expect(await screen.findByText(/将清理 2 个封卷/)).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: '应用此日志策略' }))
  await waitFor(() => expect(api.logPolicyApply).toHaveBeenCalledWith(policy, 'x'.repeat(64)))
  expect(await screen.findByText('策略已应用')).toBeVisible()
})
