import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Clock, MapPin, PlayCircle } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'

import { api } from '../../lib/api'

export function PlaceDetailPage() {
  const { placeId = '' } = useParams()
  const queryClient = useQueryClient()
  const place = useQuery({ queryKey: ['place', placeId], queryFn: () => api.place(placeId) })
  const update = useMutation({ mutationFn: (action: string) => api.updatePlace(placeId, action), onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['place', placeId] }) })
  if (!place.data) return <div className="detail-loading">正在读取地点…</div>
  return <div className="place-detail"><header className="detail-topbar"><Link to="/map"><ArrowLeft />返回地图</Link><span>地点详情</span><button aria-label="更多">•••</button></header><article className="place-detail__body"><p className="detail-context">地图中的地点 · {place.data.user_state}</p><h1>{place.data.name}</h1><p className="place-location"><MapPin />{place.data.address}<button>在高德中打开</button></p><section className="place-facts"><div><span>类型</span><strong>{place.data.place_type}</strong></div><div><span>坐标系</span><strong>{String(place.data.coordinate_system)}</strong></div><div><span>状态</span><strong>{place.data.user_state}</strong></div></section><section className="detail-section"><h2>作者观点</h2><p>{place.data.summary}</p></section><section className="detail-section ai-inference"><h2>AI 推断 <small>需确认</small></h2><p>AI 推断与来源观点分开显示；未经 Evidence 支撑的内容不会作为确定事实。</p></section><section className="detail-section"><h2><Clock />时间证据</h2>{place.data.observations.map((observation, index) => <div className="evidence-row" key={`${observation.type}-${index}`}><PlayCircle /><div><strong>视频 {observation.timestamp ?? '--:--'} · {observation.type}</strong><span>{observation.value}</span></div></div>)}</section></article><div className="detail-actions"><button onClick={() => update.mutate('dismiss')}>不感兴趣</button><button onClick={() => update.mutate('visited')}>去过</button><button className="button--primary" onClick={() => update.mutate('save')}>想去</button></div></div>
}
