import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronRight, Trash2 } from 'lucide-react'
import { Link } from 'react-router-dom'

import { EmptyState, PageHeader } from '../../components/AppShell'
import { api } from '../../lib/api'

export function TasksPage() {
  const jobs = useQuery({ queryKey: ['jobs'], queryFn: api.jobs, refetchInterval: 4000 })
  const queryClient = useQueryClient()
  const remove = useMutation({ mutationFn: api.deleteJob, onSuccess: () => { void queryClient.invalidateQueries({ queryKey: ['jobs'] }); void queryClient.invalidateQueries({ queryKey: ['dashboard'] }); void queryClient.invalidateQueries({ queryKey: ['todos'] }) } })
  return <div className="page-frame"><PageHeader title="任务" /><section className="panel task-table"><div className="panel__heading"><h2>全部任务</h2><span>{jobs.data?.length ?? 0}</span></div>{jobs.data?.length ? jobs.data.map((job) => <div className="task-table__item" key={job.id}><Link className="task-table__row" to={`/tasks/${job.id}`}><div className="task-table__identity"><strong title={job.title}>{job.title}</strong><span>{jobTypeLabel(job.job_type)} · {stepLabel(job.current_step)}{job.status === 'RUNNING' ? ` · ${activityLabel(job.last_activity_at)}前有活动` : ''}</span></div><div className="task-table__progress"><span>{job.current_step_status === 'RUNNING' ? '当前步骤' : statusLabel(job.status)} <b>{job.progress}%</b></span><div className="progress-track"><i style={{ width: `${job.progress}%` }} /></div></div><em className={job.status === 'FAILED' ? 'task-status--error' : job.runtime_state === 'STALLED' ? 'task-status--attention' : ''}>{job.runtime_state === 'STALLED' ? '可能停滞' : statusLabel(job.status)}<small>{job.status === 'RUNNING' ? job.runtime_state === 'STALLED' ? `${activityLabel(job.last_activity_at)}未更新` : '处理中' : '查看详情'}</small></em><ChevronRight /></Link>{isTerminal(job.status) && <button className="history-delete" aria-label={`删除任务 ${job.title}`} onClick={() => { if (window.confirm(`删除任务历史“${job.title}”吗？步骤与运行事件会被删除，已生成内容将保留。`)) remove.mutate(job.id) }} disabled={remove.isPending}><Trash2 /></button>}</div>) : <EmptyState title="暂无任务" detail="投递内容后会在这里显示处理过程" />}</section></div>
}

function jobTypeLabel(type: string) { return ({ RECRUITMENT: '招聘', TRAVEL: '旅行', UNKNOWN: '待识别' } as Record<string, string>)[type] ?? type }
function stepLabel(step: string) { return ({ RECEIVED: '已接收', RESOLVE: '解析', EXTRACT: '提取', SEGMENT: '分段', MATERIALIZE: '整理', VALIDATE_LINK: '校验链接', FETCH_METADATA: '获取元信息', FETCH_SUBTITLE: '获取字幕', DOWNLOAD_AUDIO: '下载音频', ASR: '语音识别', NORMALIZE_TRANSCRIPT: '归一化字幕', GENERATE_AI_NOTE: '生成 AI 笔记', EXTRACT_TRAVEL_FACTS: '提取地点', RESOLVE_POI: '解析地点', BUILD_PLACE_NOTES: '生成地点笔记', CLEAN_CACHE: '清理缓存' } as Record<string, string>)[step] ?? step }
function statusLabel(status: string) { return ({ QUEUED: '排队中', RUNNING: '处理中', COMPLETED: '已完成', PARTIAL_SUCCESS: '部分完成', FAILED: '失败', NEEDS_USER: '需确认', CANCELLED: '已取消' } as Record<string, string>)[status] ?? status }
function activityLabel(value: string | null) { if (!value) return '等待任务心跳'; const seconds = Math.max(0, Math.round((Date.now() - new Date(value).getTime()) / 1000)); return seconds < 60 ? `${seconds} 秒` : seconds < 3600 ? `${Math.floor(seconds / 60)} 分钟` : `${Math.floor(seconds / 3600)} 小时` }
function isTerminal(status: string) { return ['COMPLETED', 'PARTIAL_SUCCESS', 'FAILED', 'CANCELLED', 'NEEDS_USER'].includes(status) }
