import { useQuery } from '@tanstack/react-query'
import { ChevronRight } from 'lucide-react'
import { Link } from 'react-router-dom'

import { EmptyState, PageHeader } from '../../components/AppShell'
import { api } from '../../lib/api'

export function TasksPage() {
  const jobs = useQuery({ queryKey: ['jobs'], queryFn: api.jobs, refetchInterval: 4000 })
  return <div className="page-frame"><PageHeader title="任务" /><section className="panel task-table"><div className="panel__heading"><h2>全部任务</h2><span>{jobs.data?.length ?? 0}</span></div>{jobs.data?.length ? jobs.data.map((job) => <Link className="task-table__row" key={job.id} to={`/tasks/${job.id}`}><div><strong>{job.title}</strong><span>{job.job_type} · {job.current_step}</span></div><div className="task-table__progress"><span>{job.progress}%</span><div className="progress-track"><i style={{ width: `${job.progress}%` }} /></div></div><em>{job.status}</em><ChevronRight /></Link>) : <EmptyState title="暂无任务" detail="投递内容后会在这里显示处理过程" />}</section></div>
}
