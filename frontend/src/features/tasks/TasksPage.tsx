import { useQuery } from '@tanstack/react-query'
import { ChevronRight } from 'lucide-react'
import { Link } from 'react-router-dom'

import { EmptyState, PageHeader } from '../../components/AppShell'
import { api } from '../../lib/api'

export function TasksPage() {
  const jobs = useQuery({ queryKey: ['jobs'], queryFn: api.jobs, refetchInterval: 4000 })
  return <div className="page-frame"><PageHeader title="任务" /><section className="panel task-table"><div className="panel__heading"><h2>全部任务</h2><span>{jobs.data?.length ?? 0}</span></div>{jobs.data?.length ? jobs.data.map((job) => <Link className="task-table__row" key={job.id} to={`/tasks/${job.id}`}><div><strong>{job.title}</strong><span>{jobTypeLabel(job.job_type)} · {stepLabel(job.current_step)}</span></div><div className="task-table__progress"><span>{job.progress}%</span><div className="progress-track"><i style={{ width: `${job.progress}%` }} /></div></div><em>{statusLabel(job.status)}</em><ChevronRight /></Link>) : <EmptyState title="暂无任务" detail="投递内容后会在这里显示处理过程" />}</section></div>
}

function jobTypeLabel(type: string) { return ({ RECRUITMENT: '招聘', TRAVEL: '旅行', UNKNOWN: '待识别' } as Record<string, string>)[type] ?? type }
function stepLabel(step: string) { return ({ RECEIVED: '已接收', RESOLVE: '解析', EXTRACT: '提取', SEGMENT: '分段', MATERIALIZE: '整理' } as Record<string, string>)[step] ?? step }
function statusLabel(status: string) { return ({ QUEUED: '排队中', RUNNING: '处理中', COMPLETED: '已完成', FAILED: '失败', NEEDS_USER: '需确认', CANCELED: '已取消' } as Record<string, string>)[status] ?? status }
