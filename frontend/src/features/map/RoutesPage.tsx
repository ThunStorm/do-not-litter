import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, GripVertical, MapPin } from 'lucide-react'
import { Link } from 'react-router-dom'

import { api } from '../../lib/api'

export function RoutesPage() {
  const routes = useQuery({ queryKey: ['routes'], queryFn: api.routes })
  return <div className="page-frame route-page"><header className="detail-topbar"><Link to="/map"><ArrowLeft />返回地图</Link><span>路线清单</span><span /></header>{routes.data?.map((route) => <section key={route.id} className="panel"><div className="panel__heading"><div><h2>{route.name}</h2><span>{route.city} · 手动排序</span></div></div>{route.places.map((place, index) => <div className="route-row" key={place.id}><span className="route-order">{index + 1}</span><MapPin /><div><strong>{place.name}</strong><span>{place.address}</span></div><GripVertical /></div>)}<p className="route-note">第一版只保存地点和手动顺序，不生成未经路线服务验证的距离与交通时间。</p></section>)}</div>
}
