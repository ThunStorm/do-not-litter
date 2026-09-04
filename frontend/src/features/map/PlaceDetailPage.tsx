import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Clock, ExternalLink, History, MapPin, PlayCircle, Save } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { api } from '../../lib/api'

type Insight = { id: string; insight_type: string; value_text: string; provenance?: string }
type Detail = { coordinates?: number[]; display?: { name?: string; place_type?: string; tags?: string[]; revision?: number }; note?: { markdown?: string; revision?: number }; insights?: Insight[] } & Record<string, unknown>

export function PlaceDetailPage() {
  const { placeId = '' } = useParams()
  const queryClient = useQueryClient()
  const place = useQuery({ queryKey: ['place', placeId], queryFn: () => api.place(placeId) })
  const history = useQuery({ queryKey: ['place-history', placeId], queryFn: () => api.placeHistory(placeId) })
  const [note, setNote] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [placeType, setPlaceType] = useState('')
  const [tags, setTags] = useState('')
  const [insightType, setInsightType] = useState('HIGHLIGHT')
  const [insightText, setInsightText] = useState('')
  const update = useMutation({ mutationFn: (action: string) => api.updatePlace(placeId, action), onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['place', placeId] }) })
  const saveNote = useMutation({ mutationFn: (detail: Detail) => api.updatePlaceNote(placeId, note, detail.note?.revision ?? 0), onSuccess: () => { void queryClient.invalidateQueries({ queryKey: ['place', placeId] }); void queryClient.invalidateQueries({ queryKey: ['place-history', placeId] }) } })
  const saveOverlay = useMutation({ mutationFn: (detail: Detail) => api.updatePlaceOverlay(placeId, { display_name: displayName, override_place_type: placeType, custom_tags: tags.split(',').map((tag) => tag.trim()).filter(Boolean), expected_revision: detail.display?.revision ?? 0 }), onSuccess: () => { void queryClient.invalidateQueries({ queryKey: ['place', placeId] }); void queryClient.invalidateQueries({ queryKey: ['place-history', placeId] }) } })
  const addInsight = useMutation({ mutationFn: () => api.createPlaceInsight(placeId, { insight_type: insightType, value_key: '', value_text: insightText }), onSuccess: () => { setInsightText(''); void queryClient.invalidateQueries({ queryKey: ['place', placeId] }) } })
  const removeInsight = useMutation({ mutationFn: (insightId: string) => api.deletePlaceInsight(placeId, insightId), onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['place', placeId] }) })
  useEffect(() => { const detail = place.data as Detail | undefined; setNote(detail?.note?.markdown ?? ''); setDisplayName(detail?.display?.name ?? ''); setPlaceType(detail?.display?.place_type ?? ''); setTags((detail?.display?.tags ?? []).join(', ')) }, [place.data])
  if (!place.data) return <div className="detail-loading">正在读取地点…</div>
  const detail = place.data as Detail
  const coordinates = Array.isArray(detail.coordinates) ? detail.coordinates : []
  const name = detail.display?.name || String(detail.name)
  const amapUrl = coordinates.length === 2 ? `https://uri.amap.com/marker?position=${coordinates[0]},${coordinates[1]}&name=${encodeURIComponent(name)}&src=zhijian&coordinate=gaode&callnative=1` : `https://www.amap.com/search?query=${encodeURIComponent(name)}`
  const insights = detail.insights ?? []
  return <div className="place-detail"><header className="detail-topbar"><Link to="/map"><ArrowLeft />返回地图</Link><span>地点详情</span><span aria-hidden="true" /></header><article className="place-detail__body"><p className="detail-context">地图中的地点 · {stateLabel(String(detail.user_state))}</p><h1>{name}</h1><p className="place-location"><MapPin />{String(detail.address || '')}<a href={amapUrl} target="_blank" rel="noreferrer">在高德中打开 <ExternalLink /></a></p><section className="place-facts"><div><span>类型</span><strong>{detail.display?.place_type || String(detail.place_type)}</strong></div><div><span>坐标系</span><strong>高德 GCJ-02</strong></div><div><span>状态</span><strong>{stateLabel(String(detail.user_state))}</strong></div></section><section className="detail-section"><h2>编辑地点显示信息</h2><input value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder="显示名称" /><input value={placeType} onChange={(event) => setPlaceType(event.target.value)} placeholder="地点类型" /><input value={tags} onChange={(event) => setTags(event.target.value)} placeholder="标签，用逗号分隔" /><button className="button button--outline" onClick={() => saveOverlay.mutate(detail)} disabled={saveOverlay.isPending}><Save />保存显示信息</button><p>POI 名称、坐标和来源证据保持只读；此处只保存你的覆盖信息。</p></section><section className="detail-section"><h2>地点洞察</h2>{insights.length ? <ul className="place-insights">{insights.map((item) => <li key={item.id}><b>{insightLabel(item.insight_type)}</b>{item.value_text}</li>)}</ul> : <p>还没有带来源证据的地点洞察。</p>}<div className="place-insight-editor"><select value={insightType} onChange={(event) => setInsightType(event.target.value)} aria-label="补充洞察类型"><option value="HIGHLIGHT">亮点</option><option value="BEST_MONTH">最佳月份</option><option value="BEST_TIME_SLOT">最佳时段</option><option value="WARNING">注意</option></select><input value={insightText} onChange={(event) => setInsightText(event.target.value)} placeholder="补充自己的旅行事实" /><button className="button button--outline" disabled={!insightText || addInsight.isPending} onClick={() => addInsight.mutate()}>添加</button></div>{insights.filter((item) => item.provenance !== 'SOURCE_FACT').map((item) => <button className="text-action" key={`remove-${item.id}`} onClick={() => removeInsight.mutate(item.id)}>撤销我的“{item.value_text}”</button>)}</section><section className="detail-section"><h2>我的备注</h2><textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="记录自己的到访建议、提醒或感受" /><button className="button button--outline" onClick={() => saveNote.mutate(detail)} disabled={saveNote.isPending}><Save />保存备注</button></section><section className="detail-section"><h2><History />编辑历史</h2>{history.data?.length ? history.data.map((event) => <p className="place-history" key={event.id}><time>{new Date(event.created_at).toLocaleString('zh-CN')}</time>{event.message}</p>) : <p>还没有人工编辑记录。</p>}</section><section className="detail-section"><h2><Clock />时间证据</h2>{Array.isArray(detail.observations) ? detail.observations.map((observation, index) => <div className="evidence-row" key={`${String(observation.type)}-${index}`}><PlayCircle /><div><strong>视频 {String(observation.timestamp ?? '--:--')} · {observationLabel(String(observation.type))}</strong><span>{String(observation.value ?? '')}</span></div></div>) : null}</section></article><div className="detail-actions"><button onClick={() => update.mutate('dismiss')}>不感兴趣</button><button onClick={() => update.mutate('visited')}>去过</button><button className="button--primary" onClick={() => update.mutate('save')}>想去</button></div></div>
}

function stateLabel(state: string) { return ({ DISCOVERED: '新发现', SAVED: '想去', PLANNED: '已计划', VISITED: '去过', DISMISSED: '不感兴趣' } as Record<string, string>)[state] ?? state }
function insightLabel(type: string) { return ({ HIGHLIGHT: '亮点', RECOMMENDED_ITEM: '推荐', BEST_MONTH: '最佳月份', BEST_TIME_SLOT: '最佳时段', WARNING: '注意' } as Record<string, string>)[type] ?? type }
function observationLabel(type: string) { return ({ AUTHOR_OPINION: '作者观点', LOCATION_MENTION: '地点提及', AI_INFERENCE: 'AI 推断' } as Record<string, string>)[type] ?? type }
