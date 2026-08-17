import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowUp, ChevronRight, Cpu, Database, Link2, Server, Sparkles } from 'lucide-react'
import { FormEvent, useState } from 'react'
import { Link } from 'react-router-dom'

import { EmptyState, PageHeader } from '../../components/AppShell'
import { api } from '../../lib/api'
import type { ContentView, JobView } from '../../lib/types'

const contentTypeLabel = { RECRUITMENT: '招聘', TRAVEL: '旅行', UNSUPPORTED: '未支持' }

export function DashboardPage() {
  const queryClient = useQueryClient()
  const [captureValue, setCaptureValue] = useState('')
  const dashboard = useQuery({ queryKey: ['dashboard'], queryFn: api.dashboard, refetchInterval: 5000 })
  const status = useQuery({ queryKey: ['status'], queryFn: api.status })
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
            <NodeMetric icon={Server} label="节点" value="至简 Mac mini" detail="后端 · AI Worker · 数据存储" />
            <NodeMetric icon={Cpu} label="硬件与系统" value="Apple M4 · 16 GB" detail="macOS · arm64" />
            <NodeMetric icon={Database} label="服务" value="FastAPI · SQLite" detail="Worker · Playwright" />
            <NodeMetric
              icon={Sparkles}
              label="本地 AI"
              value="Ollama Metal"
              detail={String((status.data?.runtime as Record<string, string> | undefined)?.asr ?? 'whisper.cpp Metal')}
            />
          </div>
        </section>
      </div>
    </div>
  )
}

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
        {item.content_type === 'RECRUITMENT' ? '职' : '行'}
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
