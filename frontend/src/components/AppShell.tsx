import {
  CheckSquare,
  FileText,
  Clapperboard,
  Folder,
  Home,
  Inbox,
  LayoutGrid,
  Plus,
  Settings,
  ScrollText,
  UserRound,
} from 'lucide-react'
import type { ReactNode } from 'react'
import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { NavLink } from 'react-router-dom'

import { Brand } from './Brand'
import { api } from '../lib/api'
import { formatBeijingTime } from '../lib/time'

const desktopNav = [
  { to: '/', label: '概览', icon: LayoutGrid },
  { to: '/content', label: '内容', icon: FileText },
  { to: '/video-notes', label: '视频笔记', icon: Clapperboard },
  { to: '/tasks', label: '任务', icon: CheckSquare },
  { to: '/sources', label: '来源', icon: Folder },
  { to: '/settings', label: '设置', icon: Settings },
  { to: '/logs', label: '日志', icon: ScrollText },
]

const mobileNav = [
  { to: '/', label: '首页', icon: Home },
  { to: '/content', label: '内容', icon: FileText },
  { to: '/capture', label: '投递', icon: Plus, primary: true },
  { to: '/todos', label: '待办', icon: CheckSquare },
  { to: '/profile', label: '我的', icon: UserRound },
]

export function AppShell({ children }: { children: ReactNode }) {
  const status = useQuery({ queryKey: ['status'], queryFn: api.status, refetchInterval: 30000 })
  const [runtimeOpen, setRuntimeOpen] = useState(false)
  const metrics = status.data?.metrics
  const workerAge = metrics?.worker.heartbeat_age_seconds
  const metricsFreshness = metrics?.freshness ?? 'PENDING'
  const ollamaState = status.data?.runtime_checks.find((item) => item.name === 'ollama')?.status ?? 'UNAVAILABLE'
  const workerState = workerAge === null || workerAge === undefined ? '暂未采集' : workerAge > 90 ? '疑似停滞' : workerAge > 30 ? '心跳延迟' : `${Math.max(0, Math.round(workerAge))} 秒前`
  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => { if (event.key === 'Escape') setRuntimeOpen(false) }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [])
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Brand />
        <nav className="sidebar__nav" aria-label="管理导航">
          {desktopNav.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} end={to === '/'} className="nav-link">
              <Icon size={21} strokeWidth={1.6} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <button className="sidebar__status" type="button" aria-label="查看 Mac mini 运行状态" aria-expanded={runtimeOpen} onClick={() => setRuntimeOpen((value) => !value)}>
          <span className="status-dot" />
          <div>
            <strong>Mac mini {status.data?.services.worker === 'RUNNING' ? '在线' : '需关注'}</strong>
            <span className="sidebar__status-note">所有内容仅存于本机</span>
            <span className="sidebar__metric"><b>CPU</b><i><em style={{ width: `${metrics?.cpu.percent ?? 0}%` }} /></i><small>{formatPercent(metrics?.cpu.percent)}</small></span>
            <span className="sidebar__metric"><b>内存</b><i><em style={{ width: `${metrics?.memory.percent ?? 0}%` }} /></i><small>{formatPercent(metrics?.memory.percent)}</small></span>
            <span className="sidebar__metric"><b>数据盘</b><i><em style={{ width: `${metrics?.disk.percent ?? 0}%` }} /></i><small>{formatPercent(metrics?.disk.percent)}</small></span>
            <span className={`sidebar__heartbeat ${metricsFreshness === 'STALE' || (workerAge !== null && workerAge !== undefined && workerAge > 30) ? 'sidebar__heartbeat--late' : ''}`}>{metricsFreshness === 'PENDING' ? '等待首个指标采样' : metricsFreshness === 'STALE' ? '指标延迟 · 等待下一次采样' : `采样 · ${formatSampleTime(metrics?.sampled_at)}`}</span>
          </div>
        </button>
        {runtimeOpen && <div className="runtime-popover" role="status"><button onClick={() => setRuntimeOpen(false)} aria-label="关闭运行状态">×</button><strong>Mac mini {status.data?.services.worker === 'RUNNING' ? '在线' : '需关注'}</strong><dl><div><dt>CPU</dt><dd>{formatPercent(metrics?.cpu.percent)}<small>{metrics?.cpu.source ?? '暂未采集'}</small></dd></div><div><dt>内存</dt><dd>{formatBytes(metrics?.memory.used_bytes)} / {formatBytes(metrics?.memory.total_bytes)}<small>{formatPercent(metrics?.memory.percent)} · 可回收 {formatBytes(metrics?.memory.available_bytes)}</small></dd></div><div><dt>压缩内存</dt><dd>{formatBytes(metrics?.memory.compressed_bytes)}<small>缓存 {formatBytes(metrics?.memory.cached_bytes)}</small></dd></div><div><dt>数据盘</dt><dd>{formatBytes(metrics?.disk.used_bytes)} / {formatBytes(metrics?.disk.total_bytes)}<small>可用 {formatBytes(metrics?.disk.total_bytes && metrics?.disk.used_bytes ? metrics.disk.total_bytes - metrics.disk.used_bytes : null)}</small></dd></div><div><dt>服务</dt><dd className="runtime-popover__services">API {serviceLabel(status.data?.services.api)} · Worker {serviceLabel(status.data?.services.worker)} · SQLite {serviceLabel(status.data?.services.sqlite)} · Ollama {serviceLabel(ollamaState)}</dd></div></dl><small className="runtime-popover__footer">{metricsFreshness === 'PENDING' ? '等待首个指标采样' : `采样于 ${formatSampleTime(metrics?.sampled_at)} · ${metricsFreshness === 'STALE' ? '指标延迟' : '正常'}`}<br />Worker 心跳 · {workerState}</small></div>}
      </aside>
      <main className="app-main">{children}</main>
      <nav className="bottom-nav" aria-label="主要导航">
        {mobileNav.map(({ to, label, icon: Icon, primary }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={`bottom-nav__item ${primary ? 'bottom-nav__item--primary' : ''}`}
          >
            <span className="bottom-nav__icon"><Icon size={primary ? 28 : 23} strokeWidth={1.7} /></span>
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  )
}

function formatPercent(value: number | null | undefined) { return value === null || value === undefined ? '—' : `${Math.round(value)}%` }
function formatBytes(value: number | null | undefined) { if (value === null || value === undefined) return '—'; const gb = value / 1024 ** 3; return gb >= 1000 ? `${(gb / 1024).toFixed(1)} TB` : `${gb.toFixed(1)} GB` }
function formatSampleTime(value: string | null | undefined) { return formatBeijingTime(value) }
function serviceLabel(value: string | undefined) { return value === 'RUNNING' || value === 'READY' ? '正常' : value === 'STALE' ? '延迟' : '待检查' }

export function EmptyState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="empty-state">
      <Inbox size={28} strokeWidth={1.5} />
      <strong>{title}</strong>
      <span>{detail}</span>
    </div>
  )
}

export function PageHeader({ title, actions }: { title: string; actions?: ReactNode }) {
  return (
    <header className="page-header">
      <Brand compact />
      <h1>{title}</h1>
      <div className="page-header__actions">{actions}</div>
    </header>
  )
}
