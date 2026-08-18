import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Clock, ExternalLink, MapPin, PlayCircle } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'

import { api } from '../../lib/api'

export function PlaceDetailPage() {
  const { placeId = '' } = useParams()
  const queryClient = useQueryClient()
  const place = useQuery({ queryKey: ['place', placeId], queryFn: () => api.place(placeId) })
  const update = useMutation({ mutationFn: (action: string) => api.updatePlace(placeId, action), onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['place', placeId] }) })
  if (!place.data) return <div className="detail-loading">正在读取地点…</div>
  const coordinates = Array.isArray(place.data.coordinates) ? place.data.coordinates as number[] : []
  const amapUrl = coordinates.length === 2 ? `https://uri.amap.com/marker?position=${coordinates[0]},${coordinates[1]}&name=${encodeURIComponent(place.data.name)}&src=zhijian&coordinate=gaode&callnative=1` : `https://www.amap.com/search?query=${encodeURIComponent(place.data.name)}`
  return <div className="place-detail"><header className="detail-topbar"><Link to="/map"><ArrowLeft />返回地图</Link><span>地点详情</span><span aria-hidden="true" /></header><article className="place-detail__body"><p className="detail-context">地图中的地点 · {stateLabel(place.data.user_state)}</p><h1>{place.data.name}</h1><p className="place-location"><MapPin />{place.data.address}<a href={amapUrl} target="_blank" rel="noreferrer">在高德中打开 <ExternalLink /></a></p><section className="place-facts"><div><span>类型</span><strong>{place.data.place_type}</strong></div><div><span>坐标系</span><strong>高德 GCJ-02</strong></div><div><span>状态</span><strong>{stateLabel(place.data.user_state)}</strong></div></section><section className="detail-section"><h2>作者观点</h2><p>{place.data.summary}</p></section><section className="detail-section ai-inference"><h2>AI 推断 <small>需确认</small></h2><p>AI 推断与来源观点分开显示；未经 Evidence 支撑的内容不会作为确定事实。</p></section><section className="detail-section"><h2><Clock />时间证据</h2>{place.data.observations.map((observation, index) => <div className="evidence-row" key={`${observation.type}-${index}`}><PlayCircle /><div><strong>视频 {observation.timestamp ?? '--:--'} · {observationLabel(observation.type)}</strong><span>{observation.value}</span></div></div>)}</section></article><div className="detail-actions"><button onClick={() => update.mutate('dismiss')}>不感兴趣</button><button onClick={() => update.mutate('visited')}>去过</button><button className="button--primary" onClick={() => update.mutate('save')}>想去</button></div></div>
}

function stateLabel(state: string) { return ({ DISCOVERED: '新发现', SAVED: '想去', PLANNED: '已计划', VISITED: '去过', DISMISSED: '不感兴趣' } as Record<string, string>)[state] ?? state }
function observationLabel(type: string) { return ({ AUTHOR_OPINION: '作者观点', LOCATION_MENTION: '地点提及', AI_INFERENCE: 'AI 推断' } as Record<string, string>)[type] ?? type }
