import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronRight } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { EmptyState, PageHeader } from '../../components/AppShell'
import { BulkSelectionToolbar } from '../../components/ui/BulkSelection'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { api } from '../../lib/api'
import { useBulkSelection } from '../../lib/useBulkSelection'
import { stepLabel } from './taskTimeline'

export function TasksPage() {
  const jobs = useQuery({ queryKey: ['jobs'], queryFn: api.jobs, refetchInterval: 4000 })
  const queryClient = useQueryClient()
  const [deleteOpen, setDeleteOpen] = useState(false)
  const deletableIds = (jobs.data ?? []).filter((job) => isTerminal(job.status)).map((job) => job.id)
  const selection = useBulkSelection(deletableIds)
  const remove = useMutation({
    mutationFn: () => api.deleteJobs(selection.selectedIds),
    onSuccess: () => {
      selection.clear()
      setDeleteOpen(false)
      void queryClient.invalidateQueries({ queryKey: ['jobs'] })
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      void queryClient.invalidateQueries({ queryKey: ['todos'] })
    },
  })
  return <div className="page-frame">
    <PageHeader title="任务" />
    <section className="panel task-table">
      <div className="panel__heading">
        <div className="bulk-heading-title"><h2>全部任务</h2><span>{jobs.data?.length ?? 0}</span></div>
        <BulkSelectionToolbar label="可删除任务" visibleCount={deletableIds.length} selectedCount={selection.selectedIds.length} allSelected={selection.allSelected} pending={remove.isPending} onToggleAll={selection.toggleAll} onClear={selection.clear} onDelete={() => setDeleteOpen(true)} />
      </div>
      {jobs.data?.length ? jobs.data.map((job) => <div className="task-table__item selectable-row" key={job.id}>
        {isTerminal(job.status) ? <label className="task-table__selection-slot"><input type="checkbox" checked={selection.isSelected(job.id)} onChange={() => selection.toggle(job.id)} aria-label={`选择任务 ${job.title}`} /></label> : <span className="task-table__selection-slot" aria-hidden="true" />}
        <Link className="task-table__row" to={`/tasks/${job.id}`}>
          <div className="task-table__identity"><strong title={job.title}>{job.title}</strong><span>{jobTypeLabel(job.job_type)} · {stepLabel(job.current_step)}{job.status === 'RUNNING' ? ` · ${activityLabel(job.last_activity_at)}前有活动` : ''}</span></div>
          <div className="task-table__progress"><span>{job.current_step_status === 'RUNNING' ? '当前步骤' : statusLabel(job.status)} <b>{job.progress}%</b></span><div className="progress-track"><i style={{ width: `${job.progress}%` }} /></div></div>
          <em className={job.status === 'FAILED' ? 'task-status--error' : job.runtime_state === 'STALLED' ? 'task-status--attention' : ''}>{job.runtime_state === 'STALLED' ? '可能停滞' : statusLabel(job.status)}<small>{job.status === 'RUNNING' ? job.runtime_state === 'STALLED' ? `${activityLabel(job.last_activity_at)}未更新` : `正在${stepLabel(job.current_step)}` : '查看详情'}</small></em>
          <ChevronRight />
        </Link>
      </div>) : <EmptyState title="暂无任务" detail="投递内容后会生成可追踪的处理过程" />}
    </section>
    {deleteOpen && <ConfirmDialog title="删除任务历史" description={`删除 ${selection.selectedIds.length} 条任务的步骤与运行事件；已生成内容会保留。`} confirmLabel={`删除 ${selection.selectedIds.length} 条任务`} danger pending={remove.isPending} error={remove.error instanceof Error ? remove.error.message : ''} onCancel={() => setDeleteOpen(false)} onConfirm={() => remove.mutate()} />}
  </div>
}

function jobTypeLabel(type: string) { return ({ RECRUITMENT: '招聘', TRAVEL: '旅行', UNKNOWN: '待识别' } as Record<string, string>)[type] ?? type }
function statusLabel(status: string) { return ({ QUEUED: '排队中', RUNNING: '处理中', COMPLETED: '已完成', PARTIAL_SUCCESS: '部分完成', FAILED: '失败', NEEDS_USER: '需确认', CANCELLED: '已取消' } as Record<string, string>)[status] ?? status }
function activityLabel(value: string | null) { if (!value) return '等待任务心跳'; const seconds = Math.max(0, Math.round((Date.now() - new Date(value).getTime()) / 1000)); return seconds < 60 ? `${seconds} 秒` : seconds < 3600 ? `${Math.floor(seconds / 60)} 分钟` : `${Math.floor(seconds / 3600)} 小时` }
function isTerminal(status: string) { return ['COMPLETED', 'PARTIAL_SUCCESS', 'FAILED', 'CANCELLED', 'NEEDS_USER'].includes(status) }
