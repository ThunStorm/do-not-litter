import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowUp, Check, ChevronRight, Copy, Cpu, Database, KeyRound, Link2, RefreshCw, Server, Sparkles } from 'lucide-react'
import { FormEvent, useState } from 'react'
import { Link } from 'react-router-dom'

import { EmptyState, PageHeader } from '../../components/AppShell'
import { api } from '../../lib/api'
import type { ContentView, JobView } from '../../lib/types'

const contentTypeLabel = { RECRUITMENT: '招聘', TRAVEL: '旅行', VIDEO_NOTE: '视频笔记', UNSUPPORTED: '未支持' }

export function DashboardPage() {
  const queryClient = useQueryClient()
  const [captureValue, setCaptureValue] = useState('')
  const [copied, setCopied] = useState(false)
  const dashboard = useQuery({ queryKey: ['dashboard'], queryFn: api.dashboard, refetchInterval: 5000 })
  const status = useQuery({ queryKey: ['status'], queryFn: api.status, refetchInterval: 15000 })
  const lanToken = useQuery({ queryKey: ['lan-token'], queryFn: api.lanToken })
  const rotateToken = useMutation({ mutationFn: api.rotateLanToken, onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['lan-token'] }) })
  const capture = useMutation({
    mutationFn: api.capture,
    onSuccess: () => {
      setCaptureValue('')
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })

  function submitCapture(event: FormEvent) {
    event.preventDefault()
    const value = captureValue.trim()
    if (value) capture.mutate(value)
  }

  return (
    <div className="dashboard page-frame">
      <PageHeader title="概览" />
      <form className="capture-bar" onSubmit={submitCapture}>
        <Link2 size={22} strokeWidth={1.6} aria-hidden="true" />
        <input
          aria-label="粘贴链接或输入正文"
          placeholder="粘贴链接或输入正文"
          value={captureValue}
          onChange={(event) => setCaptureValue(event.target.value)}
        />
        <button className="capture-bar__submit" type="submit" aria-label="提交" disabled={capture.isPending}>
          <ArrowUp size={24} strokeWidth={1.7} />
        </button>
      </form>
      {capture.isError && <p className="form-error">{capture.error.message}</p>}

      <section className="pairing-card" aria-label="局域网配对信息">
        <div className="pairing-card__title"><KeyRound /><span><strong>手机局域网配对码</strong><small>{status.data?.lan_url ?? '正在读取局域网地址'}</small></span></div>
        <output aria-label="四位配对码">{lanToken.data?.display ?? '••••'}</output>
        <div className="pairing-card__actions"><button onClick={async () => { if (!lanToken.data) return; await navigator.clipboard.writeText(lanToken.data.token); setCopied(true); window.setTimeout(() => setCopied(false), 1600) }}>{copied ? <Check /> : <Copy />}{copied ? '已复制' : '复制'}</button><button onClick={() => rotateToken.mutate()} disabled={rotateToken.isPending}><RefreshCw className={rotateToken.isPending ? 'spin' : ''} />换一个</button></div>
      </section>

      <div className="dashboard-grid">
        <section className="panel panel--contents">
          <PanelHeading title="最近内容" to="/content" />
          <div className="content-rows">
            {dashboard.data?.contents.length ? (
              dashboard.data.contents.slice(0, 4).map((item) => <ContentRow key={item.id} item={item} />)
            ) : (
              <EmptyState title="还没有内容" detail="投递第一条链接后会出现在这里" />
            )}
          </div>
        </section>

        <section className="panel panel--jobs">
          <PanelHeading title="处理动态" to="/tasks" />
          <div className="job-list">
            {dashboard.data?.jobs.length ? (
              dashboard.data.jobs.slice(0, 3).map((job) => <JobRow key={job.id} job={job} />)
            ) : (
              <EmptyState title="当前没有任务" detail="系统准备就绪" />
            )}
          </div>
        </section>

        <section className="node-panel">
          <div className="node-panel__heading">
            <h2>后端节点</h2>
            <span><span className="status-dot" />可信局域网在线</span>
          </div>
          <div className="node-panel__grid">
            <NodeMetric icon={Server} label="节点" value={status.data?.hardware.machine_name ?? '读取中'} detail={`${status.data?.hardware.model ?? '—'} · ${status.data?.lan_url ?? '—'}`} />
            <NodeMetric icon={Cpu} label="硬件与系统" value={`${status.data?.hardware.chip ?? '读取中'} · ${status.data?.hardware.memory ?? '—'}`} detail={`${status.data?.system ?? '—'} ${status.data?.release ?? ''} · ${status.data?.architecture ?? '—'} · GPU ${status.data?.hardware.gpu_cores ?? '—'} 核`} />
            <NodeMetric icon={Database} label="服务" value={`API ${serviceLabel(status.data?.services.api)} · Worker ${serviceLabel(status.data?.services.worker)}`} detail={`SQLite · 可用空间 ${status.data?.hardware.disk.free_gb ?? '—'} GB`} />
            <NodeMetric
              icon={Sparkles}
              label="本地 AI"
              value={runtimeSummary(status.data?.runtime_checks)}
              detail={status.data?.runtime.asr ?? '正在检测 Whisper.cpp'}
            />
          </div>
        </section>
      </div>
    </div>
  )
}

function serviceLabel(status?: string) { return status === 'RUNNING' ? '运行中' : status === 'STALE' ? '无心跳' : '检测中' }
function runtimeSummary(checks?: Array<{ name: string; status: string }>) { const ready = checks?.filter((item) => item.status === 'READY').map((item) => item.name) ?? []; return ready.length ? ready.join(' · ') : '本地 AI 未就绪' }

function PanelHeading({ title, to }: { title: string; to: string }) {
  return (
    <div className="panel__heading">
      <h2>{title}</h2>
      <Link to={to}>查看全部 <ChevronRight size={16} /></Link>
    </div>
  )
}

function ContentRow({ item }: { item: ContentView }) {
  return (
    <Link className="content-row" to={`/content/${item.id}`}>
      <div className={`type-icon type-icon--${item.content_type.toLowerCase()}`} aria-hidden="true">
        {item.content_type === 'RECRUITMENT' ? '职' : item.content_type === 'VIDEO_NOTE' ? '影' : '行'}
      </div>
      <div className="content-row__main">
        <strong>{item.title}</strong>
        <span>{contentTypeLabel[item.content_type]} · 更新于 {formatDate(item.updated_at)}</span>
      </div>
      <span className={`state-label ${item.status === 'NEEDS_USER' ? 'state-label--review' : ''}`}>
        {item.status === 'NEEDS_USER' ? '需确认' : '已完成'}
      </span>
      <ChevronRight size={17} />
    </Link>
  )
}

function JobRow({ job }: { job: JobView }) {
  return (
    <Link className="job-row" to={`/tasks/${job.id}`}>
      <div className="job-row__heading">
        <strong>{job.title}</strong>
        <span>{job.status === 'COMPLETED' ? '已完成' : `预计 ${job.progress > 60 ? 2 : 6} 分钟`}</span>
      </div>
      <p>{stepLabel(job.current_step)} · {job.progress}%</p>
      <div className="progress-track" aria-label={`处理进度 ${job.progress}%`}>
        <span style={{ width: `${job.progress}%` }} />
      </div>
    </Link>
  )
}

function NodeMetric({ icon: Icon, label, value, detail }: { icon: typeof Server; label: string; value: string; detail: string }) {
  return (
    <div className="node-metric">
      <Icon size={22} strokeWidth={1.5} />
      <div><span>{label}</span><strong>{value}</strong><small>{detail}</small></div>
    </div>
  )
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(value))
}

function stepLabel(step: string) {
  return ({ RECEIVED: '已接收', RESOLVE: '解析中', SEGMENT: '分段中', EXTRACT: '提取中', MATERIALIZE: '整理中' } as Record<string, string>)[step] ?? step
}
