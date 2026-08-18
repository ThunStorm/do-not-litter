import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Ban, Check, Circle, RotateCcw } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'

import { api } from '../../lib/api'

export function TaskDetailPage() {
  const { jobId = '' } = useParams()
  const queryClient = useQueryClient()
  const job = useQuery({ queryKey: ['job', jobId], queryFn: () => api.job(jobId), refetchInterval: 3000 })
  const retry = useMutation({ mutationFn: () => api.retryJob(jobId), onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['job', jobId] }) })
  const cancel = useMutation({ mutationFn: () => api.cancelJob(jobId), onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['job', jobId] }) })
  if (!job.data) return <div className="detail-loading">正在读取任务…</div>
  return <div className="task-detail page-frame"><header className="detail-topbar"><Link to="/tasks"><ArrowLeft />返回任务</Link><span>运行详情</span><div><button onClick={() => cancel.mutate()} disabled={!['RUNNING', 'QUEUED'].includes(job.data.status)}><Ban />取消</button><button onClick={() => retry.mutate()}><RotateCcw />重试</button></div></header><section className="task-hero"><h1>{job.data.title}</h1><p><span className="status-dot" />{statusLabel(job.data.status)} · {job.data.progress}%</p><div className="progress-track"><span style={{ width: `${job.data.progress}%` }} /></div></section><div className="task-detail-grid"><section className="panel"><div className="panel__heading"><h2>运行时间线</h2></div>{job.data.steps.map((step) => <div className="timeline-row" key={String(step.name)}>{step.status === 'COMPLETED' ? <Check /> : <Circle />}<div><strong>{stepLabel(String(step.name))}</strong><span>{statusLabel(String(step.status))} · {String(step.progress)}%</span></div></div>)}</section><aside className="panel task-summary"><h2>运行摘要</h2><dl><dt>任务类型</dt><dd>{jobTypeLabel(job.data.job_type)}</dd><dt>当前步骤</dt><dd>{stepLabel(job.data.current_step)}</dd><dt>重试次数</dt><dd>{String((job.data as unknown as { retry_count?: number }).retry_count ?? 0)}</dd><dt>Worker</dt><dd>Mac mini</dd></dl></aside></div></div>
}

function jobTypeLabel(type: string) { return ({ RECRUITMENT: '招聘', TRAVEL: '旅行', UNKNOWN: '待识别' } as Record<string, string>)[type] ?? type }
function stepLabel(step: string) { return ({ RECEIVED: '已接收', RESOLVE: '解析来源', EXTRACT: '提取信息', SEGMENT: '文本分段', MATERIALIZE: '生成结果' } as Record<string, string>)[step] ?? step }
function statusLabel(status: string) { return ({ QUEUED: '排队中', RUNNING: '处理中', COMPLETED: '已完成', FAILED: '失败', NEEDS_USER: '需确认', CANCELED: '已取消' } as Record<string, string>)[status] ?? status }
