import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, ExternalLink, History, MapPin, Save, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { FilterMenu } from '../../components/ui/FilterMenu'
import { api } from '../../lib/api'
import type { PlaceVisitWindow } from '../../lib/types'
import {
  labelPlaceType,
  placeTypeLabels,
  seasonLabels,
  segmentLabels,
  stateLabels,
  timeLabels,
  visitWindowLabel,
} from './placeLabels'

type Detail = {
  name?: string
  address?: string
  place_type?: string
  user_state?: string
  coordinates?: number[]
  display?: { name?: string; place_type?: string; tags?: string[]; revision?: number }
  note?: { markdown?: string; revision?: number }
  visit_windows?: PlaceVisitWindow[]
  knowledge?: Knowledge
} & Record<string, unknown>

type KnowledgeObservation = { source_title: string; source_quote: string; segment_ids: string[]; evidence_url?: string }
type KnowledgeItem = { insight_type: string; value_text: string; state: string; source_count: number; current: boolean; observations: KnowledgeObservation[] }
type Knowledge = Record<string, KnowledgeItem[]> & { consensus?: Record<string, string>; sources?: { source_id: string; title: string }[] }

type WindowDraft = {
  season: string
  month: string
  month_segment: string
  day_time_slot: string
  source_text: string
}

const emptyWindow: WindowDraft = { season: '', month: '', month_segment: '', day_time_slot: '', source_text: '' }
const menuOptions = (labels: Record<string, string>) => [
  { value: '', label: '未设置' },
  ...Object.entries(labels).map(([value, label]) => ({ value, label })),
]
const placeTypeOptions = menuOptions(placeTypeLabels)
const monthOptions = [
  { value: '', label: '未设置' },
  ...Array.from({ length: 12 }, (_, index) => ({ value: String(index + 1), label: `${index + 1}月` })),
]
const knowledgeLabels: Record<string, string> = {
  highlights: '核心看点', dishes: '推荐菜 / 核心体验', visit_windows: '最佳时间', warnings: '注意事项', prices: '价格', queues: '排队', opinions: '作者态度', other: '其他观察',
}
const knowledgeState: Record<string, string> = { CONSENSUS: '多来源一致', SINGLE_SOURCE: '单一来源', CONFLICT: '来源存在冲突' }

function PlaceKnowledge({ knowledge }: { knowledge?: Knowledge }) {
  const sections = Object.entries(knowledgeLabels).flatMap(([key, label]) => knowledge?.[key]?.length ? [[key, label, knowledge[key]] as const] : [])
  if (!sections.length) return <section className="detail-section"><h2>地点知识</h2><p>尚无带证据的跨来源观察。</p></section>
  return <section className="detail-section"><h2>地点知识</h2><p className="knowledge-intro">每条结论保留来源引文；“一致”仅代表独立来源与证据完整度满足门禁。</p><div className="place-knowledge">{sections.map(([key, label, items]) => <section key={key} className="knowledge-group"><h3>{label}</h3>{items.map((item, index) => <article key={`${item.insight_type}-${item.value_text}-${index}`} className={`knowledge-card knowledge-card--${item.state.toLowerCase()}`}><div><strong>{item.value_text}</strong>{!item.current ? <small>较早观察</small> : null}</div><span>{knowledgeState[item.state] ?? item.state} · {item.source_count || 1} 个来源</span><ul>{item.observations.map((observation, observationIndex) => <li key={`${observation.source_title}-${observationIndex}`}><b>{observation.source_title}</b><q>{observation.source_quote || '未保存引文'}</q>{observation.evidence_url ? <Link to={observation.evidence_url}>查看证据{observation.segment_ids.length ? `（${observation.segment_ids.length} 段）` : ''}</Link> : <small>{observation.segment_ids.length ? `关联 ${observation.segment_ids.length} 个片段` : '未关联片段'}</small>}</li>)}</ul></article>)}</section>)}</div></section>
}

export function PlaceDetailPage() {
  const { placeId = '' } = useParams()
  const navigate = useNavigate()
  const client = useQueryClient()
  const place = useQuery({ queryKey: ['place', placeId], queryFn: () => api.place(placeId) })
  const history = useQuery({ queryKey: ['place-history', placeId], queryFn: () => api.placeHistory(placeId) })
  const [note, setNote] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [placeType, setPlaceType] = useState('')
  const [tags, setTags] = useState('')
  const [windowValue, setWindowValue] = useState<WindowDraft>(emptyWindow)
  const [deleteOpen, setDeleteOpen] = useState(false)

  const refresh = () => {
    void client.invalidateQueries({ queryKey: ['place', placeId] })
    void client.invalidateQueries({ queryKey: ['places'] })
    void client.invalidateQueries({ queryKey: ['map'] })
  }
  const update = useMutation({ mutationFn: (action: string) => api.updatePlace(placeId, action), onSuccess: refresh })
  const saveNote = useMutation({
    mutationFn: (detail: Detail) => api.updatePlaceNote(placeId, note, detail.note?.revision ?? 0),
    onSuccess: refresh,
  })
  const saveOverlay = useMutation({
    mutationFn: (detail: Detail) => api.updatePlaceOverlay(placeId, {
      display_name: displayName,
      override_place_type: placeType,
      custom_tags: tags.split(',').map((tag) => tag.trim()).filter(Boolean),
      expected_revision: detail.display?.revision ?? 0,
    }),
    onSuccess: refresh,
  })
  const addWindow = useMutation({
    mutationFn: () => api.createVisitWindow(placeId, {
      season: windowValue.season || null,
      month: windowValue.month ? Number(windowValue.month) : null,
      month_segment: windowValue.month_segment || null,
      day_time_slot: windowValue.day_time_slot || null,
      source_text: windowValue.source_text,
    }),
    onSuccess: () => { setWindowValue(emptyWindow); refresh() },
  })
  const removeWindow = useMutation({ mutationFn: (id: string) => api.deleteVisitWindow(placeId, id), onSuccess: refresh })
  const hardDelete = useMutation({ mutationFn: () => api.hardDeletePlace(placeId), onSuccess: () => navigate('/places') })

  useEffect(() => {
    const detail = place.data as Detail | undefined
    setNote(detail?.note?.markdown ?? '')
    setDisplayName(detail?.display?.name ?? '')
    setPlaceType(detail?.display?.place_type ?? '')
    setTags((detail?.display?.tags ?? []).join(', '))
  }, [place.data])

  if (!place.data) return <div className="detail-loading">正在读取地点…</div>
  const detail = place.data as Detail
  const name = detail.display?.name || String(detail.name)
  const coordinates = detail.coordinates ?? []
  const amapUrl = coordinates.length === 2
    ? `https://uri.amap.com/marker?position=${coordinates[0]},${coordinates[1]}&name=${encodeURIComponent(name)}&src=zhijian&coordinate=gaode&callnative=1`
    : `https://www.amap.com/search?query=${encodeURIComponent(name)}`
  const setWindowField = (field: keyof WindowDraft) => (value: string) => setWindowValue((current) => ({ ...current, [field]: value }))

  return <div className="place-detail">
    <header className="detail-topbar"><Link to="/places"><ArrowLeft />返回地点管理</Link><span>地点详情</span><span /></header>
    <article className="place-detail__body">
      <p className="detail-context">地图中的地点 · {stateLabels[String(detail.user_state)] ?? detail.user_state}</p>
      <h1>{name}</h1>
      <p className="place-location"><MapPin />{String(detail.address || '')}<a href={amapUrl} target="_blank" rel="noreferrer">在高德中打开 <ExternalLink /></a></p>
      <section className="place-facts"><div><span>类型</span><strong>{labelPlaceType(detail.display?.place_type || String(detail.place_type))}</strong></div><div><span>坐标系</span><strong>高德 GCJ-02</strong></div><div><span>状态</span><strong>{stateLabels[String(detail.user_state)] ?? String(detail.user_state)}</strong></div></section>
      <PlaceKnowledge knowledge={detail.knowledge} />
      <section className="detail-section"><h2>显示覆盖</h2><div className="place-form"><label><span>显示名称</span><input value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder="保留为空则使用地点原名" /></label><label><span>地点类型</span><FilterMenu label="选择类型" value={placeType} onChange={setPlaceType} options={placeTypeOptions} /></label><label className="place-form__wide"><span>我的标签</span><input value={tags} onChange={(event) => setTags(event.target.value)} placeholder="多个标签用逗号分隔" /></label></div><button className="button button--outline" onClick={() => saveOverlay.mutate(detail)} disabled={saveOverlay.isPending}><Save />保存显示信息</button></section>
      <section className="detail-section"><h2>适宜时间与季节限制</h2>{detail.visit_windows?.length ? <ul className="place-insights">{detail.visit_windows.map((item) => <li key={item.id}><b>{visitWindowLabel(item)}</b>{item.source_text || '用户补充'}{item.provenance !== 'SOURCE_FACT' ? <button className="text-action" onClick={() => removeWindow.mutate(item.id)}>移除</button> : null}</li>)}</ul> : <p>尚未记录适宜时间或季节限制。</p>}<div className="visit-window-editor"><FilterMenu label="季节" value={windowValue.season} onChange={setWindowField('season')} options={menuOptions(seasonLabels)} /><FilterMenu label="月份" value={windowValue.month} onChange={setWindowField('month')} options={monthOptions} /><FilterMenu label="旬段" value={windowValue.month_segment} onChange={setWindowField('month_segment')} options={menuOptions(segmentLabels)} /><FilterMenu label="时段" value={windowValue.day_time_slot} onChange={setWindowField('day_time_slot')} options={menuOptions(timeLabels)} /><label className="visit-window-editor__note"><span>说明</span><input value={windowValue.source_text} onChange={(event) => setWindowField('source_text')(event.target.value)} placeholder="例如：十月中旬秋色最好" /></label><button className="button button--outline" disabled={addWindow.isPending || !Object.values(windowValue).some(Boolean)} onClick={() => addWindow.mutate()}>添加时间窗口</button></div></section>
      <section className="detail-section"><h2>我的备注</h2><textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="记录自己的到访建议、提醒或感受" /><button className="button button--outline" onClick={() => saveNote.mutate(detail)} disabled={saveNote.isPending}><Save />保存备注</button></section>
      <section className="detail-section"><h2><History />编辑历史</h2>{history.data?.map((event) => <p className="place-history" key={event.id}><time>{new Date(event.created_at).toLocaleString('zh-CN')}</time>{event.message}</p>)}</section>
      <section className="detail-section danger-zone"><h2>危险操作</h2><p>永久删除地点会删除地点域数据和路线引用；来源、视频和 Evidence 会保留。</p><button className="button button--danger" onClick={() => setDeleteOpen(true)}><Trash2 />永久删除地点</button></section>
    </article>
    <div className="detail-actions"><button onClick={() => update.mutate('dismiss')}>不感兴趣</button><button onClick={() => update.mutate('visited')}>去过</button><button className="button--primary" onClick={() => update.mutate('save')}>想去</button></div>
    {deleteOpen ? <ConfirmDialog title="永久删除地点" description="此操作不可恢复；地点域数据和路线引用会删除，来源、视频和 Evidence 会保留。" confirmLabel="永久删除地点" danger pending={hardDelete.isPending} error={hardDelete.error instanceof Error ? hardDelete.error.message : ''} onCancel={() => setDeleteOpen(false)} onConfirm={() => hardDelete.mutate()} /> : null}
  </div>
}
