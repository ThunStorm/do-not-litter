import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  FileArchive,
  LoaderCircle,
  Save,
  Search,
  ShieldCheck,
} from 'lucide-react'
import { FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../lib/api'
import type { ProfileView } from '../lib/types'
import { EmptyState, PageHeader } from './AppShell'

export function SourcesPage() {
  const [query, setQuery] = useState('')
  const [selectedId, setSelectedId] = useState<string>()
  const sources = useQuery({ queryKey: ['sources', query], queryFn: () => api.sources(query) })
  const detail = useQuery({ queryKey: ['source', selectedId], queryFn: () => api.source(selectedId!), enabled: Boolean(selectedId) })
  useEffect(() => {
    if (sources.data?.length && !sources.data.some((source) => source.id === selectedId)) setSelectedId(sources.data[0].id)
  }, [selectedId, sources.data])
  const snapshots = (detail.data?.snapshots ?? []) as Array<Record<string, string>>
  const contents = (detail.data?.contents ?? []) as Array<Record<string, string>>
  return <div className="page-frame data-page"><PageHeader title="来源审计" />
    <div className="search-field"><Search /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索标题或原始地址" /></div>
    <div className="source-layout"><section className="panel source-list"><div className="panel__heading"><h2>全部来源</h2><span>{sources.data?.length ?? 0}</span></div>
      {sources.data?.length ? sources.data.map((source) => <button className={`source-row ${selectedId === source.id ? 'is-active' : ''}`} key={source.id} onClick={() => setSelectedId(source.id)}>
        <FileArchive /><span><strong>{source.title}</strong><small>{sourceTypeLabel(source.source_type)} · {authorityLabel(source.authority)} · {source.snapshot_count} 个快照</small><em>{source.locator}</em></span><ChevronRight />
      </button>) : <EmptyState title="还没有来源" detail="投递链接或文件后会生成可审计的原始来源" />}
    </section><section className="panel source-inspector"><div className="panel__heading"><h2>来源证据链</h2></div>
      {!selectedId ? <EmptyState title="选择一个来源" detail="查看快照、分段和生成内容之间的关系" /> : detail.isLoading ? <Loading /> : <div className="inspector-body">
        <h3>{String(detail.data?.title ?? '未命名来源')}</h3><a href={String(detail.data?.locator ?? '#')} target="_blank" rel="noreferrer">{String(detail.data?.locator ?? '')}</a>
        <dl><div><dt>来源权威级别</dt><dd>{authorityLabel(String(detail.data?.authority ?? 'UNKNOWN'))}</dd></div><div><dt>文本分段</dt><dd>{String(detail.data?.segment_count ?? 0)}</dd></div><div><dt>保留快照</dt><dd>{snapshots.length}</dd></div><div><dt>生成内容</dt><dd>{contents.length}</dd></div></dl>
        <h4>快照记录</h4>{snapshots.map((snapshot) => <div className="snapshot-row" key={snapshot.id}><ShieldCheck /><span><strong>{formatDate(snapshot.captured_at)}</strong><small>SHA-256 {snapshot.content_hash?.slice(0, 18)}…</small></span></div>)}
      </div>}
    </section></div>
  </div>
}

export function TodosPage() {
  const todos = useQuery({ queryKey: ['todos'], queryFn: api.todos })
  return <div className="page-frame data-page"><PageHeader title="待办" /><p className="page-lead">只集中需要您判断的事项，自动流程不会堆在这里。</p>
    <section className="panel todo-list"><div className="panel__heading"><h2>需要处理</h2><span>{todos.data?.length ?? 0}</span></div>
      {todos.data?.length ? todos.data.map((todo) => <Link className="todo-row" key={todo.id} to={todo.to}><AlertTriangle /><span><strong>{todo.title}</strong><small>{todo.detail}</small><em>{kindLabel(todo.kind)} · {formatDate(todo.created_at)}</em></span><ChevronRight /></Link>) : <EmptyState title="当前没有待办" detail="需要确认的岗位条件、失败任务和地点歧义会出现在这里" />}
    </section></div>
}

const emptyProfile: ProfileView = { name: '', education: '', major: '', graduation_year: '', graduate_status: '', household_registration: '', preferred_regions: ['北京市'] }

export function ProfilePage() {
  const profile = useQuery({ queryKey: ['profile'], queryFn: api.profile })
  const [values, setValues] = useState<ProfileView>(emptyProfile)
  const [message, setMessage] = useState('')
  useEffect(() => { if (profile.data) setValues(profile.data) }, [profile.data])
  const save = useMutation({ mutationFn: () => api.saveProfile(values), onSuccess: (data) => { setValues(data); setMessage('已保存到 Mac mini') }, onError: (error) => setMessage(error.message) })
  const update = (key: keyof ProfileView, value: string) => setValues((current) => ({ ...current, [key]: key === 'preferred_regions' ? value.split(/[，,]/).map((item) => item.trim()).filter(Boolean) : value }))
  return <div className="page-frame profile-page"><PageHeader title="我的档案" /><p className="page-lead">用于北京市公务员、事业单位等岗位的本地规则匹配，档案不会上传给第三方模型。</p>
    <form className="panel profile-form" onSubmit={(event: FormEvent) => { event.preventDefault(); save.mutate() }}><div className="panel__heading"><h2>报考信息</h2><button className="button button--primary" disabled={save.isPending}>{save.isPending ? <LoaderCircle className="spin" /> : <Save />}保存</button></div>
      <div className="field-grid"><label>姓名或称呼<input value={values.name} onChange={(event) => update('name', event.target.value)} /></label><label>最高学历<input value={values.education} onChange={(event) => update('education', event.target.value)} placeholder="本科 / 硕士" /></label><label>专业<input value={values.major} onChange={(event) => update('major', event.target.value)} /></label><label>毕业年份<input value={values.graduation_year} onChange={(event) => update('graduation_year', event.target.value)} inputMode="numeric" /></label><label>应届身份<input value={values.graduate_status} onChange={(event) => update('graduate_status', event.target.value)} placeholder="2026 应届 / 社会人员" /></label><label>户籍<input value={values.household_registration} onChange={(event) => update('household_registration', event.target.value)} /></label><label className="field-grid__wide">偏好地区<input value={values.preferred_regions.join('，')} onChange={(event) => update('preferred_regions', event.target.value)} placeholder="北京市，天津市" /></label></div>
      {message && <p className="form-success"><CheckCircle2 />{message}</p>}
    </form></div>
}

export function LogsPage() {
  const [level, setLevel] = useState('')
  const [query, setQuery] = useState('')
  const logs = useQuery({ queryKey: ['logs', level, query], queryFn: () => api.logs(level, query), refetchInterval: 5000 })
  const queryClient = useQueryClient()
  return <div className="page-frame logs-page"><PageHeader title="运行日志" actions={<button className="button button--outline" onClick={() => void queryClient.invalidateQueries({ queryKey: ['logs'] })}>立即刷新</button>} />
    <div className="log-toolbar"><div className="search-field"><Search /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索日志信息" /></div><select value={level} onChange={(event) => setLevel(event.target.value)}><option value="">全部级别</option><option>INFO</option><option>WARNING</option><option>ERROR</option></select></div>
    <section className="panel log-table"><div className="log-row log-row--head"><span>时间</span><span>级别</span><span>组件 / 事件</span><span>信息</span></div>
      {logs.data?.length ? logs.data.map((event) => <div className="log-row" key={event.id}><time>{formatDate(event.created_at)}</time><strong className={`log-level log-level--${event.level.toLowerCase()}`}>{event.level}</strong><span>{event.component}<small>{event.event_type}</small></span><p>{event.message}</p></div>) : <EmptyState title="暂无审计事件" detail="登录、配置、任务和系统操作会记录在这里" />}
    </section></div>
}

function Loading() { return <div className="loading-state"><LoaderCircle className="spin" />读取中</div> }
function formatDate(value?: string) { return value ? new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(new Date(value)) : '—' }
function kindLabel(kind: string) { return ({ CONTENT_REVIEW: '内容确认', JOB_FAILURE: '任务失败', JOB_REVIEW: '任务确认', PLACE_REVIEW: '地点确认' } as Record<string, string>)[kind] ?? kind }
function sourceTypeLabel(type: string) { return ({ URL: '网页链接', FILE: '本地文件', TEXT: '文本' } as Record<string, string>)[type] ?? type }
function authorityLabel(authority: string) { return ({ OFFICIAL: '官方来源', PLATFORM: '平台来源', UNKNOWN: '未判定' } as Record<string, string>)[authority] ?? authority }
