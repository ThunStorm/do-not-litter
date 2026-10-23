import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, expect, it, vi } from 'vitest'
import { api } from '../../lib/api'
import type { AIStagePolicy, StageLimitsPreview } from '../../lib/types'
import { StagePolicyEditor } from './SettingsPage'

vi.mock('../../lib/api', () => ({api: {stageLimitsPreview: vi.fn(), saveAiStagePolicy: vi.fn()}}))
afterEach(() => {cleanup(); vi.clearAllMocks()})
const policy = {stage: 'TRANSCRIPT_CORRECTION', capability: 'TRANSCRIPT_CORRECTION', execution_mode: 'REMOTE_ONLY', domain_pack_ids: [], timeout_seconds: null, wall_time_seconds: null, chunk_size: null, batch_size: null, domain: null} as unknown as AIStagePolicy
const preview = (p: AIStagePolicy): StageLimitsPreview => ({limits_policy_version: 2, request_timeouts: [{profile_id:'model',name:'候选模型',seconds:p.timeout_seconds ?? 300,source:p.timeout_seconds ? 'STAGE_POLICY':'MODEL_PROFILE',initial_ceiling_seconds:p.timeout_seconds ?? 300}],wall_time_seconds:null,job_wall_time_seconds:1800,chunk_chars:p.chunk_size ?? 5000,batch_size:p.batch_size ?? 24})

it('previews draft limits without saving and saves correction batches in the stage policy', async () => {
  vi.mocked(api.stageLimitsPreview).mockImplementation(async p => preview(p))
  vi.mocked(api.saveAiStagePolicy).mockResolvedValue(policy)
  render(<QueryClientProvider client={new QueryClient()}><StagePolicyEditor policy={policy} profiles={[]} packs={[]} /></QueryClientProvider>)
  expect(api.stageLimitsPreview).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button',{name:'高级参数'}))
  await screen.findByText(/单次 300 秒，来源：模型默认/)
  fireEvent.change(screen.getByLabelText('单次请求超时（秒，留空继承）'),{target:{value:'660'}})
  await screen.findByText(/单次 660 秒，来源：阶段设置/)
  fireEvent.change(screen.getByLabelText('每批校对字符预算'),{target:{value:'3000'}})
  fireEvent.change(screen.getByLabelText('每批最多转写段（Segment）'),{target:{value:'16'}})
  expect(api.saveAiStagePolicy).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button',{name:'保存阶段'}))
  await waitFor(() => expect(api.saveAiStagePolicy).toHaveBeenCalledWith('TRANSCRIPT_CORRECTION',expect.objectContaining({timeout_seconds:660,chunk_size:3000,batch_size:16})))
  expect(screen.queryByText('转写分段参数')).not.toBeInTheDocument()
})

it('names the place-extraction model stage and distinguishes its downstream materialization', async () => {
  const mapPolicy = {...policy,stage:'GROUND_MAP',capability:'STRUCTURED_EXTRACTION'}
  vi.mocked(api.stageLimitsPreview).mockImplementation(async p => preview(p))
  render(<QueryClientProvider client={new QueryClient()}><StagePolicyEditor policy={mapPolicy} profiles={[]} packs={[]} /></QueryClientProvider>)
  expect(screen.getByRole('heading',{name:'证据地图（提取地点与事实）'})).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button',{name:'高级参数'}))
  await screen.findByText(/任务页“提取地点”的主要模型调用在这里/)
  expect(screen.queryByLabelText('每批最多转写段（Segment）')).not.toBeInTheDocument()
})
