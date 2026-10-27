import { RecommendationSummary } from '../../components/RecommendationSummary'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, ExternalLink, MapPin, Save, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'

import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { FilterMenu } from '../../components/ui/FilterMenu'
import { api } from '../../lib/api'
import type { PlaceVisitWindow, TravelBriefData } from '../../lib/types'
import {
  labelPlaceType,
  placeTypeLabels,
  seasonLabels,
  segmentLabels,
  stateLabels,
  timeLabels,
} from './placeLabels'
import { placeText } from './placePresentation'
import { TravelBrief } from './TravelBrief'
import { VisitWindowList } from './VisitWindowList'

type Detail = {
  recommendation_summary?: import('../../lib/types').Recommendation
  source_notes?: Array<{ note_id: string; version_id: string; title: string }>
  travel_brief?: TravelBriefData
  name?: string
  address?: string
  place_type?: string
  user_state?: string
  coordinates?: number[]
  display?: { name?: string; place_type?: string; tags?: string[]; revision?: number }
  note?: { markdown?: string; revision?: number }
  visit_windows?: PlaceVisitWindow[]
  knowledge?: Knowledge
  recommendation?: { label?: string; reasons?: Array<{ kind: string; text: string }> }
  visual_facts?: Array<{ id: string; fact_type: string; value: string; evidence_url: string }>
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
  highlights: '特色与体验', dishes: '美食与游玩', visit_windows: '观赏时机', warnings: '出行提醒', prices: '费用与消费', queues: '排队与等候', opinions: '体验评价', other: '相关观察',
}
function PlaceKnowledge({ knowledge, brief }: { knowledge?: Knowledge; brief?: TravelBriefData }) {
  const shown = new Set([brief?.timing, ...(brief?.highlights ?? []), ...(brief?.warnings ?? []), ...(brief?.conditions ?? [])].map((text) => placeText(text)))
  const sections = Object.entries(knowledgeLabels).flatMap(([key, label]) => {
    const items = knowledge?.[key]?.filter((item) => !shown.has(placeText(item.value_text))) ?? []
    return items.length ? [[key, label, items] as const] : []
  })
  if (!sections.length) return null
  return <section className="detail-section place-business"><h2>更多地点信息</h2><div className="place-business__grid">{sections.map(([key, label, items]) => <section key={key}><h3>{label}</h3><ul>{items.map((item, i) => <li key={`${key}-${i}`}><p>{placeText(item.value_text)}</p>{item.state === 'CONFLICT' && <small className="place-data-conflict">资料存在差异，可在下方原句与来源中核对依据。</small>}{!item.current && <small>较早记录</small>}</li>)}</ul></section>)}</div></section>
}
function KnowledgeSources({ knowledge }: { knowledge?: Knowledge }) {
  const items = Object.entries(knowledgeLabels).flatMap(([key, label]) => (knowledge?.[key] ?? []).map((item) => ({ ...item, label })))
  if (!items.length) return null
  return <section className="detail-section place-source-records"><h2>原句与来源</h2>{items.map((item, i) => <article key={i}><strong>{item.label} · {item.value_text}</strong>{item.observations.map((o, j) => <blockquote key={j}><small>{o.source_title}</small><p>{o.source_quote || '未保存引文'}</p>{o.evidence_url && <Link to={o.evidence_url}>查看原笔记</Link>}</blockquote>)}</article>)}</section>
}

export function PlaceDetailPage() {
  const { placeId = '' } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const client = useQueryClient()
  const place = useQuery({ queryKey: ['place', placeId], queryFn: () => api.place(placeId) })
  const destinations = useQuery({ queryKey: ['place-destinations', placeId], queryFn: () => api.placeDestinations(placeId) })
  const history = useQuery({ queryKey: ['place-history', placeId], queryFn: () => api.placeHistory(placeId), enabled: place.isSuccess })
  const [note, setNote] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [placeType, setPlaceType] = useState('')
  const [tags, setTags] = useState('')
  const [windowValue, setWindowValue] = useState<WindowDraft>(emptyWindow)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [editing, setEditing] = useState(false)
  const [saved, setSaved] = useState(false)

  const refresh = () => {
    void client.invalidateQueries({ queryKey: ['place', placeId] })
    void client.invalidateQueries({ queryKey: ['place-history', placeId] })
    void client.invalidateQueries({ queryKey: ['places'] })
    void client.invalidateQueries({ queryKey: ['map'] })
  }
  const update = useMutation({ mutationFn: (action: string) => api.updatePlace(placeId, action), onSuccess: refresh })
  const saveEdits = useMutation({
    mutationFn: async (detail: Detail) => {
      await api.updatePlaceOverlay(placeId, { display_name: displayName, override_place_type: placeType, custom_tags: tags.split(',').map((tag) => tag.trim()).filter(Boolean), expected_revision: detail.display?.revision ?? 0 })
      await api.updatePlaceNote(placeId, note, detail.note?.revision ?? 0)
    },
    onSuccess: () => { setEditing(false); setSaved(true); refresh() },
  })
  const markerVisibility = useMutation({ mutationFn: (hidden: boolean) => hidden ? api.restorePlaceMarker(placeId) : api.hidePlaceMarker(placeId), onSuccess: refresh })
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
  const preference = useMutation({ mutationFn: (eventType: 'LIKE' | 'DISLIKE') => api.createPlacePreference(placeId, eventType), onSuccess: refresh })

  useEffect(() => {
    if (editing) return
    const detail = place.data as Detail | undefined
    setNote(detail?.note?.markdown ?? '')
    setDisplayName(detail?.display?.name ?? '')
    setPlaceType(detail?.display?.place_type ?? '')
    setTags((detail?.display?.tags ?? []).join(', '))
  }, [place.data, editing])

  useEffect(() => {
    if (place.isSuccess && location.hash === '#time-evidence') document.getElementById('time-evidence')?.scrollIntoView({ block: 'start' })
  }, [location.hash, place.isSuccess, placeId])

  if (place.isError) return <p role="alert">地点读取失败，请刷新重试。</p>
  if (!place.data) return <div className="detail-loading">正在读取地点…</div>
  const detail = place.data as Detail
  const name = detail.display?.name || String(detail.name)
  const coordinates = detail.coordinates ?? []
  const amapUrl = coordinates.length === 2
    ? `https://uri.amap.com/marker?position=${coordinates[0]},${coordinates[1]}&name=${encodeURIComponent(name)}&src=zhijian&coordinate=gaode&callnative=1`
    : `https://www.amap.com/search?query=${encodeURIComponent(name)}`
  const setWindowField = (field: keyof WindowDraft) => (value: string) => setWindowValue((current) => ({ ...current, [field]: value }))

  return <div className="place-detail place-detail--reading">
    <header className="detail-topbar"><Link to={location.state?.fromMap ? '/map' : '/places'}><ArrowLeft />{location.state?.fromMap ? '返回地图' : '返回地点管理'}</Link><span>地点详情</span><button onClick={() => { setEditing(!editing); setSaved(false) }}>{editing ? '收起编辑' : '编辑地点'}</button></header>
    <article className="place-detail__body">
      <header className="place-reading-hero"><div className="place-reading-tags"><span>{labelPlaceType(detail.display?.place_type || String(detail.place_type))}</span><span>{stateLabels[String(detail.user_state)] ?? '未标记'}</span>{[...new Set(detail.display?.tags ?? [])].map((tag) => <span key={tag}>{tag}</span>)}</div><div className="place-name-line"><h1>{name}</h1><RecommendationSummary value={detail.recommendation_summary} compact /></div><RecommendationSummary value={detail.recommendation_summary} /><div className="place-reading-location"><p><MapPin />{String(detail.address || '地址待补充')}</p><a className="ui-button ui-button--outline" href={amapUrl} target="_blank" rel="noreferrer">在高德中打开 <ExternalLink /></a></div></header>
      {saved && <p className="place-save-status" role="status">已保存</p>}
      <section className="place-reading-overview" aria-label="地点要点"><TravelBrief brief={detail.travel_brief} layout="detail" /></section>
      <PlaceKnowledge knowledge={detail.knowledge} brief={detail.travel_brief} />
      {destinations.data?.length ? <section className="detail-section place-related"><h2>周边与目的地</h2><div className="place-reading-tags">{destinations.data.map((d) => <span key={d.id}>{d.name}</span>)}</div></section> : null}
      {!!detail.visual_facts?.length && <section className="detail-section"><h2>图片补充</h2><div className="place-photo-grid">{detail.visual_facts.map((item) => <a key={item.id} href={item.evidence_url} target="_blank" rel="noreferrer"><img loading="lazy" src={item.evidence_url} alt={item.value} /><span>{placeText(item.value)}</span><small>图片观察，待核对</small></a>)}</div></section>}
      {!editing && detail.note?.markdown && <section className="detail-section"><h2>我的备注</h2><p className="place-personal-note">{detail.note.markdown}</p></section>}
      {editing && <section className="detail-section place-editor" aria-label="编辑地点记录"><h2>编辑地点记录</h2><div className="place-form"><label><span>显示名称</span><input autoFocus value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="保留为空则使用地点原名" /></label><label><span>地点类型</span><FilterMenu label="选择类型" value={placeType} onChange={setPlaceType} options={placeTypeOptions} /></label><label className="place-form__wide"><span>我的标签</span><input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="多个标签用逗号分隔" /></label></div><label className="place-editor__note"><span>我的备注</span><textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="记录自己的到访建议、提醒或感受" /></label><button className="button button--primary" onClick={() => saveEdits.mutate(detail)} disabled={saveEdits.isPending}><Save />{saveEdits.isPending ? '保存中…' : '保存修改'}</button>{saveEdits.isError && <p role="alert">保存失败，请重试；已保存字段会保留。</p>}
      <h3>时间补充</h3>{!!detail.visit_windows?.length && <VisitWindowList windows={detail.visit_windows} onRemove={(id) => removeWindow.mutate(id)} />}<div className="visit-window-editor"><FilterMenu label="季节" value={windowValue.season} onChange={setWindowField('season')} options={menuOptions(seasonLabels)} /><FilterMenu label="月份" value={windowValue.month} onChange={setWindowField('month')} options={monthOptions} /><FilterMenu label="旬段" value={windowValue.month_segment} onChange={setWindowField('month_segment')} options={menuOptions(segmentLabels)} /><FilterMenu label="时段" value={windowValue.day_time_slot} onChange={setWindowField('day_time_slot')} options={menuOptions(timeLabels)} /><label className="visit-window-editor__note"><span>说明</span><input value={windowValue.source_text} onChange={(e) => setWindowField('source_text')(e.target.value)} placeholder="例如：十月中旬秋色最好" /></label><button className="button button--outline" disabled={addWindow.isPending || !Object.values(windowValue).some(Boolean)} onClick={() => addWindow.mutate()}>保存时间补充</button>{addWindow.isError && <p role="alert">时间补充保存失败，请重试。</p>}</div></section>}
      <section className="detail-section place-reading-sources"><h2>关联笔记</h2>{detail.source_notes?.length ? <ul className="place-source-links">{detail.source_notes.map((source) => <li key={`${source.note_id}-${source.version_id}`}><Link to={`/video-notes/${source.note_id}`}>{source.title}</Link></li>)}</ul> : <p>暂无关联笔记。</p>}</section>
      <section className="detail-section place-reading-evidence"><h2 id="time-evidence">时间依据</h2>{detail.travel_brief?.inherited && <p className="place-evidence-context">时节取自关联地点的共同景观背景，不代表继承具体日期、天气和时刻。</p>}{detail.visit_windows?.length ? <VisitWindowList windows={detail.visit_windows} /> : <p>暂无原始时间记录。</p>}</section>
      <KnowledgeSources knowledge={detail.knowledge} />
      <div className="place-support-grid">
        <section className="place-support-card"><h3>地点资料</h3><dl className="place-metadata" tabIndex={0} aria-label="地点资料内容"><div><dt>坐标</dt><dd>{coordinates.length === 2 ? coordinates.join(', ') : '未记录'}</dd></div><div><dt>坐标系</dt><dd>{String(detail.coordinate_system || 'GCJ-02')}</dd></div><div><dt>地图标识</dt><dd>{String(detail.external_poi_id || '未记录')}</dd></div></dl></section>
        <section className="place-support-card"><h3>编辑历史</h3><div className="place-history-list" role="region" aria-label="编辑历史记录" tabIndex={0}>{history.isPending ? <p>正在读取…</p> : history.isError ? <p role="alert">历史读取失败，请重试。</p> : history.data?.length ? history.data.map((event) => <p className="place-history" key={event.id}><time>{new Date(event.created_at).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })}</time>{event.message}</p>) : <p>暂无编辑记录。</p>}</div></section>
      </div>
      <section className="place-management place-support-card"><h3>地图显示</h3><div className="place-management__body"><div className="place-management__actions"><button className="ui-button ui-button--outline" disabled={markerVisibility.isPending} onClick={() => markerVisibility.mutate((detail.marker as { visibility?: string } | undefined)?.visibility === 'HIDDEN')}>{(detail.marker as { visibility?: string } | undefined)?.visibility === 'HIDDEN' ? '恢复地图显示' : '在地图中隐藏'}</button></div>{markerVisibility.isError && <p role="alert">操作失败，请重试。</p>}<button className="text-action place-delete-action" onClick={() => setDeleteOpen(true)}><Trash2 />永久删除地点</button></div></section>
    </article>
    <div className="detail-actions" role="group" aria-label="地点操作"><button onClick={() => update.mutate('dismiss')} disabled={update.isPending}>不感兴趣</button><button onClick={() => preference.mutate('DISLIKE')} disabled={preference.isPending}>不喜欢</button><button onClick={() => preference.mutate('LIKE')} disabled={preference.isPending}>喜欢</button><button onClick={() => update.mutate('visited')} disabled={update.isPending}>去过</button><button className="button--primary" onClick={() => update.mutate('save')} disabled={update.isPending}>想去</button></div>
    {deleteOpen ? <ConfirmDialog title="永久删除地点" description="此操作不可恢复；地点域数据和路线引用会删除，来源、视频和 Evidence 会保留。" confirmLabel="永久删除地点" danger pending={hardDelete.isPending} error={hardDelete.error instanceof Error ? hardDelete.error.message : ''} onCancel={() => setDeleteOpen(false)} onConfirm={() => hardDelete.mutate()} /> : null}
  </div>
}
