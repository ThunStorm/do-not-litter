import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertTriangle,
  CheckCircle2,
  Copy,
  ChevronRight,
  Download,
  FileArchive,
  Filter,
  LoaderCircle,
  Pause,
  Play,
  Save,
  Search,
  ShieldCheck,
  Trash2,
  X,
} from 'lucide-react'
import { FormEvent, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { api } from '../lib/api'
import { formatBeijingTime } from '../lib/time'
import type { ProfileView } from '../lib/types'
import { EmptyState, PageHeader } from './AppShell'
import { BulkSelectionToolbar } from './ui/BulkSelection'
import { ConfirmDialog } from './ui/ConfirmDialog'
import { useBulkSelection } from '../lib/useBulkSelection'

export function SourcesPage() {
  const queryClient = useQueryClient()
  const [query, setQuery] = useState('')
  const [selectedId, setSelectedId] = useState<string>()
  const [batchDeleteOpen, setBatchDeleteOpen] = useState(false)
  const [evidenceDeleteOpen, setEvidenceDeleteOpen] = useState(false)
  const [batchResult, setBatchResult] = useState<{ deleted: number; skipped: number } | null>(null)
  const sources = useQuery({ queryKey: ['sources', query], queryFn: () => api.sources(query) })
  const detail = useQuery({ queryKey: ['source', selectedId], queryFn: () => api.source(selectedId!), enabled: Boolean(selectedId) })
  const selection = useBulkSelection((sources.data ?? []).map((source) => source.id))
  const remove = useMutation({ mutationFn: () => api.deleteSources(selection.selectedIds), onSuccess: (result) => { selection.clear(); setBatchDeleteOpen(false); setBatchResult({ deleted: result.deleted_ids.length, skipped: result.skipped.length }); void queryClient.invalidateQueries({ queryKey: ['sources'] }); void queryClient.invalidateQueries({ queryKey: ['content'] }); void queryClient.invalidateQueries({ queryKey: ['video-notes'] }); void queryClient.removeQueries({ queryKey: ['source'] }) } })
  const removeEvidenceChain = useMutation({ mutationFn: () => api.deleteSourceEvidenceChain(selectedId!), onSuccess: () => { setEvidenceDeleteOpen(false); setSelectedId(undefined); void queryClient.invalidateQueries({ queryKey: ['sources'] }); void queryClient.invalidateQueries({ queryKey: ['content'] }); void queryClient.invalidateQueries({ queryKey: ['video-notes'] }); void queryClient.invalidateQueries({ queryKey: ['dashboard'] }); void queryClient.removeQueries({ queryKey: ['source'] }) } })
  useEffect(() => {
    if (!sources.data?.length) setSelectedId(undefined)
    else if (!sources.data.some((source) => source.id === selectedId)) setSelectedId(sources.data[0].id)
  }, [selectedId, sources.data])
  const snapshots = detail.data?.snapshots ?? []
  const contents = detail.data?.contents ?? []
  const deletion = detail.data?.deletion
  return <><div className="page-frame data-page"><PageHeader title="来源审计" />
    <div className="search-field"><Search /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索标题或原始地址" /></div>
    {batchResult && <p className="source-bulk-result">批量删除完成：删除孤立来源 {batchResult.deleted} 条，因关联内容、笔记或任务跳过 {batchResult.skipped} 条。</p>}
    <div className="source-layout"><section className="panel source-list"><div className="panel__heading"><div className="bulk-heading-title"><h2>全部来源</h2><span>{sources.data?.length ?? 0}</span></div><BulkSelectionToolbar label="来源" visibleCount={sources.data?.length ?? 0} selectedCount={selection.selectedIds.length} allSelected={selection.allSelected} pending={remove.isPending} onToggleAll={selection.toggleAll} onClear={selection.clear} onDelete={() => setBatchDeleteOpen(true)} /></div>
      {sources.data?.length ? sources.data.map((source) => <div className="source-row-wrap selectable-row" key={source.id}><label className="bulk-row-checkbox"><input type="checkbox" checked={selection.isSelected(source.id)} onChange={() => selection.toggle(source.id)} aria-label={`选择来源 ${source.title}`} /></label><button className={`source-row source-row--selectable ${selectedId === source.id ? 'is-active' : ''}`} onClick={() => setSelectedId(source.id)}>
        <FileArchive /><span><strong>{source.title}</strong><small>{sourceTypeLabel(source.source_type)} · {authorityLabel(source.authority)} · {source.snapshot_count} 个快照</small><em>{source.locator}</em></span><ChevronRight />
      </button></div>) : <EmptyState title="还没有来源" detail="投递链接或文件后会生成可审计的原始来源" />}
    </section><section className="panel source-inspector"><div className="panel__heading"><h2>来源证据链</h2>{selectedId && <button className="button button--outline source-delete" disabled={Boolean(deletion?.active_job_count) || removeEvidenceChain.isPending} title={deletion?.active_job_count ? '请先结束关联活跃任务' : '删除来源证据链'} onClick={() => setEvidenceDeleteOpen(true)}><Trash2 />删除记录</button>}</div>
      {!selectedId ? <EmptyState title="选择一个来源" detail="查看快照、分段和生成内容之间的关系" /> : detail.isLoading ? <Loading /> : <div className="inspector-body">
        <h3>{String(detail.data?.title ?? '未命名来源')}</h3><a href={String(detail.data?.locator ?? '#')} target="_blank" rel="noreferrer">{String(detail.data?.locator ?? '')}</a>
        <dl><div><dt>来源权威级别</dt><dd>{authorityLabel(String(detail.data?.authority ?? 'UNKNOWN'))}</dd></div><div><dt>文本分段</dt><dd>{String(detail.data?.segment_count ?? 0)}</dd></div><div><dt>保留快照</dt><dd>{snapshots.length}</dd></div><div><dt>生成内容</dt><dd>{contents.length}</dd></div></dl>
        {deletion && !deletion.allowed && <p className="source-delete-note">删除受限：关联内容 {deletion.content_count} 条、视频笔记 {deletion.video_note_count} 条、活跃任务 {deletion.active_job_count} 个。请先从对应页面处理。</p>}
        <h4>快照记录</h4>{snapshots.map((snapshot) => <div className="snapshot-row" key={snapshot.id}><ShieldCheck /><span><strong>{formatDate(snapshot.captured_at)}</strong><small>SHA-256 {snapshot.content_hash?.slice(0, 18)}…</small></span></div>)}
      </div>}
    </section></div>
  </div>{batchDeleteOpen && <ConfirmDialog title="批量删除来源" description={`将尝试删除 ${selection.selectedIds.length} 条来源；有关联内容、视频笔记或活跃任务的来源会跳过，且不会删除关联内容。`} confirmLabel={`删除 ${selection.selectedIds.length} 条来源`} danger pending={remove.isPending} error={remove.error instanceof Error ? remove.error.message : ''} onCancel={() => setBatchDeleteOpen(false)} onConfirm={() => remove.mutate()} />}{evidenceDeleteOpen && <ConfirmDialog title="删除来源证据链" description={`确认后将删除此来源的 ${deletion?.content_count ?? 0} 条关联内容、${deletion?.video_note_count ?? 0} 条视频笔记及快照/分段；地点和路线保留。`} confirmLabel="确认同步删除" danger pending={removeEvidenceChain.isPending} error={removeEvidenceChain.error instanceof Error ? removeEvidenceChain.error.message : ''} onCancel={() => setEvidenceDeleteOpen(false)} onConfirm={() => removeEvidenceChain.mutate()} />}</>
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
  const [params, setParams] = useSearchParams()
  const [levels, setLevels] = useState<string[]>([])
  const [query, setQuery] = useState('')
  const [component, setComponent] = useState('')
  const [eventType, setEventType] = useState('')
  const [requestId, setRequestId] = useState('')
  const [entityId, setEntityId] = useState('')
  const [range, setRange] = useState('1h')
  const [customFrom, setCustomFrom] = useState('')
  const [customTo, setCustomTo] = useState('')
  const [following, setFollowing] = useState(true)
  const [selectedId, setSelectedId] = useState<string>()
  const [copiedLogId, setCopiedLogId] = useState<string>()
  const jobId = params.get('job_id') ?? ''
  const from = range === '15m' ? new Date(Date.now() - 15 * 60_000).toISOString() : range === '1h' ? new Date(Date.now() - 60 * 60_000).toISOString() : range === '24h' ? new Date(Date.now() - 24 * 60 * 60_000).toISOString() : range === '7d' ? new Date(Date.now() - 7 * 24 * 60 * 60_000).toISOString() : range === 'custom' && customFrom ? new Date(customFrom).toISOString() : undefined
  const to = range === 'custom' && customTo ? new Date(customTo).toISOString() : undefined
  const logs = useQuery({ queryKey: ['logs', levels, query, component, eventType, jobId, requestId, entityId, range, customFrom, customTo], queryFn: () => api.logs({ levels, query, component, eventType, jobId, requestId, entityId, from, to }), refetchInterval: following ? 5000 : false })
  const status = useQuery({ queryKey: ['status'], queryFn: api.status, refetchInterval: 5000 })
  const queryClient = useQueryClient()
  const selected = logs.data?.items.find((event) => event.id === selectedId)
  const eventJob = useQuery({ queryKey: ['log-event-job', selected?.entity_id], queryFn: () => api.job(selected?.entity_id ?? ''), enabled: Boolean(selected?.entity_type === 'job' && selected?.entity_id) })
  const rerun = useMutation({ mutationFn: () => api.retryJob(selected?.entity_id ?? '', selected?.id), onSuccess: () => { void queryClient.invalidateQueries({ queryKey: ['logs'] }); void eventJob.refetch() } })
  const toggleLevel = (value: string) => setLevels((current) => current.includes(value) ? current.filter((item) => item !== value) : [...current, value])
  const reset = () => { setLevels([]); setQuery(''); setComponent(''); setEventType(''); setRequestId(''); setEntityId(''); setRange('1h'); setCustomFrom(''); setCustomTo(''); setParams({}) }
  return <div className="page-frame logs-page"><PageHeader title="运行日志" actions={<div className="log-header-actions"><button className="button button--outline" onClick={() => setFollowing((value) => !value)}>{following ? <Pause /> : <Play />}{following ? '暂停跟随' : '恢复跟随'}</button><button className="button button--outline" onClick={() => void queryClient.invalidateQueries({ queryKey: ['logs'] })}>立即刷新</button></div>} />
    <section className="log-health"><div><span>API</span><strong className={status.data?.services.api === 'RUNNING' ? 'green-text' : 'amber-text'}>{status.data?.services.api ?? '读取中'}</strong></div><div><span>Worker</span><strong className={status.data?.services.worker === 'RUNNING' ? 'green-text' : 'amber-text'}>{status.data?.services.worker ?? '读取中'}</strong></div><div><span>执行器</span><strong className={status.data?.services.executor === 'DEADLINE_EXCEEDED' ? 'amber-text' : 'green-text'}>{({ IDLE: '空闲', RUNNING: '执行中', DEADLINE_EXCEEDED: '调用已超时' } as Record<string, string>)[status.data?.services.executor ?? ''] ?? '读取中'}</strong></div><div><span>筛选范围</span><strong>{range === 'all' ? '全部时间' : range}</strong></div><div><span>结果</span><strong>{logs.data?.items.length ?? 0} 条</strong></div></section>
    <div className="log-toolbar log-toolbar--operations"><div className="search-field"><Search /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索信息或事件" /></div><select aria-label="日志时间范围" value={range} onChange={(event) => setRange(event.target.value)}><option value="15m">最近 15 分钟</option><option value="1h">最近 1 小时</option><option value="24h">最近 24 小时</option><option value="7d">最近 7 天</option><option value="all">全部时间</option><option value="custom">自定义时间</option></select><select aria-label="日志组件" value={component} onChange={(event) => setComponent(event.target.value)}><option value="">全部组件</option>{[...new Set(logs.data?.items.map((event) => event.component) ?? [])].map((name) => <option key={name}>{name}</option>)}</select><select aria-label="日志事件类型" value={eventType} onChange={(event) => setEventType(event.target.value)}><option value="">全部事件</option>{[...new Set(logs.data?.items.map((event) => event.event_type) ?? [])].map((name) => <option key={name}>{name}</option>)}</select><button className="button button--outline" onClick={reset}><Filter />重置</button></div>
    {range === 'custom' && <div className="log-exact-filters"><label>开始<input type="datetime-local" value={customFrom} onChange={(event) => setCustomFrom(event.target.value)} /></label><label>结束<input type="datetime-local" value={customTo} onChange={(event) => setCustomTo(event.target.value)} /></label></div>}
    <div className="log-exact-filters"><label>Request ID<input value={requestId} onChange={(event) => setRequestId(event.target.value)} placeholder="精确筛选" /></label><label>实体 ID<input value={entityId} onChange={(event) => setEntityId(event.target.value)} placeholder="精确筛选" /></label></div>
    <div className="log-filter-row"><span>级别</span>{['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'].map((level) => <button className={levels.includes(level) ? 'is-active' : ''} key={level} onClick={() => toggleLevel(level)}>{level}</button>)}{jobId && <span className="log-filter-token">任务 {jobId.slice(0, 12)}… <button onClick={() => setParams({})} aria-label="清除任务筛选"><X /></button></span>}</div>
    <section className="panel log-table"><div className="log-row log-row--head"><span>时间</span><span>级别</span><span>组件 / 事件</span><span>关联对象</span><span>信息</span></div>
      {logs.data?.items.length ? logs.data.items.map((event) => <button className={`log-row ${selectedId === event.id ? 'log-row--selected' : ''}`} key={event.id} onClick={() => setSelectedId(event.id)}><time>{formatDate(event.created_at)}</time><strong className={`log-level log-level--${event.level.toLowerCase()}`}>{event.level}</strong><span>{event.component}<small>{event.event_type}</small></span><span className="log-entity">{event.entity_id ? event.entity_id.slice(0, 14) : '—'}<small>{event.request_id ? event.request_id.slice(0, 12) : event.entity_type ?? ''}</small></span><p>{event.message}</p></button>) : <EmptyState title="暂无匹配事件" detail="调整时间范围或筛选条件后再试" />}
      {logs.data?.next_cursor && <button className="log-load-more" onClick={() => void api.logs({ levels, query, component, eventType, jobId, requestId, entityId, from, to, cursor: logs.data.next_cursor ?? undefined }).then((next) => queryClient.setQueryData(['logs', levels, query, component, eventType, jobId, requestId, entityId, range, customFrom, customTo], { ...next, items: [...(logs.data?.items ?? []), ...next.items] }))}>加载更多</button>}
    </section>{jobId && Boolean(logs.data?.attempts?.length) && <section className="panel log-attempts"><div className="panel__heading"><h2>模型尝试</h2><span>{logs.data?.attempts.length} 次</span></div><div className="log-attempt-list">{logs.data?.attempts.map((attempt) => <div className="log-attempt" key={attempt.id}><div><strong>{attempt.route === 'fallback' ? '备用模型' : '主模型'} · {attempt.model}</strong><small>{formatDate(attempt.created_at)} · {attempt.operation}{attempt.chunk_count ? ` · 分块 ${attempt.chunk_index}/${attempt.chunk_count}` : ''}{attempt.split_path && attempt.split_path !== 'root' ? ` · ${attempt.split_path}` : ''}{attempt.timeout_seconds ? ` · 上限 ${attempt.timeout_seconds}s` : ''}</small></div><span className={attempt.status === 'COMPLETED' || attempt.status === 'RUNNING' ? 'green-text' : 'amber-text'}>{attempt.status === 'RUNNING' ? '进行中' : attempt.status === 'COMPLETED' ? '成功' : attempt.error_code || '失败'}<small>{attempt.status === 'RUNNING' ? `已运行 ${attempt.elapsed_seconds}s` : attempt.duration_ms == null ? '耗时未采集' : `${attempt.duration_ms} ms`}</small></span>{attempt.error_message && <p>{attempt.error_message}</p>}</div>)}</div></section>}{selected && <aside className="log-drawer"><header><div><span>事件详情</span><strong>{selected.event_type}</strong></div><button onClick={() => setSelectedId(undefined)} aria-label="关闭详情"><X /></button></header><dl><div><dt>时间</dt><dd>{formatDate(selected.created_at)}</dd></div><div><dt>组件</dt><dd>{selected.component}</dd></div><div><dt>Job / 实体</dt><dd>{selected.entity_id || '—'}</dd></div><div><dt>Request ID</dt><dd>{selected.request_id || '—'}</dd></div></dl><p>{selected.message}</p><pre>{JSON.stringify(selected.detail, null, 2)}</pre><footer>{selected.entity_type === 'job' && selected.entity_id && <Link to={`/tasks/${selected.entity_id}`}>打开任务</Link>}{['ERROR', 'CRITICAL'].includes(selected.level) && selected.entity_type === 'job' && selected.entity_id && ['FAILED', 'PARTIAL_SUCCESS', 'NEEDS_USER', 'CANCELLED'].includes(eventJob.data?.status ?? '') && <button disabled={rerun.isPending} onClick={() => { if (window.confirm(`重跑“${eventJob.data?.title ?? '该任务'}”会重新入队，并可能再次访问来源或调用模型。是否继续？`)) rerun.mutate() }}>{rerun.isPending ? '正在重新入队' : '重跑所属任务'}</button>}{['ERROR', 'CRITICAL'].includes(selected.level) && eventJob.data?.status === 'RUNNING' && <span className="log-rerun-state">任务正在执行</span>}{['ERROR', 'CRITICAL'].includes(selected.level) && eventJob.data?.status === 'COMPLETED' && <span className="log-rerun-state">任务已在后续尝试完成</span>}<button onClick={() => void navigator.clipboard?.writeText(selected.entity_id || selected.request_id || selected.id)}><Copy />复制标识</button><button onClick={() => { void navigator.clipboard?.writeText(JSON.stringify(selected, null, 2)); setCopiedLogId(selected.id) }}><Copy />{copiedLogId === selected.id ? '已复制日志' : '复制日志'}</button><button onClick={() => downloadEvent(selected)}><Download />导出详情</button></footer></aside>}</div>
}

function downloadEvent(event: object & { id: string }) { const blob = new Blob([JSON.stringify(event, null, 2)], { type: 'application/json' }); const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url; link.download = `zhijian-event-${event.id}.json`; link.click(); URL.revokeObjectURL(url) }

function Loading() { return <div className="loading-state"><LoaderCircle className="spin" />读取中</div> }
function formatDate(value?: string) { return formatBeijingTime(value) }
function kindLabel(kind: string) { return ({ CONTENT_REVIEW: '内容确认', JOB_FAILURE: '任务失败', JOB_REVIEW: '任务确认', PLACE_REVIEW: '地点确认' } as Record<string, string>)[kind] ?? kind }
function sourceTypeLabel(type: string) { return ({ URL: '网页链接', FILE: '本地文件', TEXT: '文本' } as Record<string, string>)[type] ?? type }
function authorityLabel(authority: string) { return ({ OFFICIAL: '官方来源', PLATFORM: '平台来源', UNKNOWN: '未判定' } as Record<string, string>)[authority] ?? authority }
