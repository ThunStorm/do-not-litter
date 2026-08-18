import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowDown, ArrowLeft, ArrowUp, MapPin, Plus } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../../lib/api'

export function RoutesPage() {
  const queryClient = useQueryClient()
  const routes = useQuery({ queryKey: ['routes'], queryFn: api.routes })
  const [creating, setCreating] = useState(false)
  const [name, setName] = useState('新的路线清单')
  const create = useMutation({ mutationFn: () => api.createRoute(name, '厦门市'), onSuccess: () => { setCreating(false); void queryClient.invalidateQueries({ queryKey: ['routes'] }) } })
  const reorder = useMutation({ mutationFn: ({ routeId, ids }: { routeId: string; ids: string[] }) => api.updateRoute(routeId, ids), onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['routes'] }) })
  const move = (routeId: string, ids: string[], index: number, offset: number) => { const next = index + offset; if (next < 0 || next >= ids.length) return; const reordered = [...ids]; [reordered[index], reordered[next]] = [reordered[next], reordered[index]]; reorder.mutate({ routeId, ids: reordered }) }
  return <div className="page-frame route-page"><header className="detail-topbar"><Link to="/map"><ArrowLeft />返回地图</Link><span>路线清单</span><button className="icon-button" onClick={() => setCreating((value) => !value)} aria-label="新建路线"><Plus /></button></header>{creating && <form className="route-create" onSubmit={(event) => { event.preventDefault(); create.mutate() }}><input value={name} onChange={(event) => setName(event.target.value)} autoFocus /><button className="button button--primary">建立清单</button></form>}{routes.data?.map((route) => <section key={route.id} className="panel"><div className="panel__heading"><div><h2>{route.name}</h2><span>{route.city} · {route.places.length} 个地点 · 手动排序</span></div></div>{route.places.map((place, index) => <div className="route-row" key={place.id}><span className="route-order">{index + 1}</span><MapPin /><div><strong>{place.name}</strong><span>{place.address}</span></div><span className="route-row__actions"><button onClick={() => move(route.id, route.places.map((item) => item.id), index, -1)} disabled={index === 0 || reorder.isPending} aria-label="上移"><ArrowUp /></button><button onClick={() => move(route.id, route.places.map((item) => item.id), index, 1)} disabled={index === route.places.length - 1 || reorder.isPending} aria-label="下移"><ArrowDown /></button></span></div>)}<p className="route-note">只保存地点和人工顺序，不生成未经路线服务验证的距离与交通时间。</p></section>)}</div>
}
