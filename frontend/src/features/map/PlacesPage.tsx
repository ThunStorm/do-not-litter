import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Eye, EyeOff, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { api } from '../../lib/api'
import type { MapMarker } from '../../lib/types'
import { labelPlaceType, stateLabels } from './placeLabels'

export function PlacesPage() {
  const client = useQueryClient()
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState<string[]>([])
  const [deleting, setDeleting] = useState<MapMarker>()
  const places = useQuery({ queryKey: ['places', query], queryFn: () => api.places(query ? `query=${encodeURIComponent(query)}` : '') })
  const invalidate = () => { void client.invalidateQueries({ queryKey: ['places'] }); void client.invalidateQueries({ queryKey: ['map'] }); void client.invalidateQueries({ queryKey: ['routes'] }) }
  const bulk = useMutation({ mutationFn: (action: 'hide' | 'restore') => api.bulkPlaces({ place_ids: selected, action }), onSuccess: () => { setSelected([]); invalidate() } })
  const hardDelete = useMutation({ mutationFn: () => api.hardDeletePlace(deleting!.id), onSuccess: () => { setDeleting(undefined); invalidate() } })
  const toggle = (id: string) => setSelected((items) => items.includes(id) ? items.filter((item) => item !== id) : [...items, id])
  const all = places.data?.items ?? []
  const allSelected = all.length > 0 && all.every((place) => selected.includes(place.id))
  return <div className="page-frame places-page"><header className="detail-topbar"><Link to="/map"><ArrowLeft />返回地图</Link><span>地点管理</span><small>{places.data?.total ?? 0} 个地点</small></header><div className="places-toolbar"><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索名称或地址" /><button className="button button--outline" onClick={() => bulk.mutate('hide')} disabled={!selected.length || bulk.isPending}><EyeOff />隐藏 {selected.length || ''}</button><button className="button button--outline" onClick={() => bulk.mutate('restore')} disabled={!selected.length || bulk.isPending}><Eye />恢复显示</button></div><div className="places-table"><div className="places-row places-row--head"><input aria-label="全选地点" type="checkbox" checked={allSelected} onChange={() => setSelected(allSelected ? [] : all.map((place) => place.id))} /><span>地点</span><span>类型</span><span>状态</span><span>可见性</span><span>操作</span></div>{all.map((place) => <div className="places-row" key={place.id}><input aria-label={`选择 ${place.name}`} type="checkbox" checked={selected.includes(place.id)} onChange={() => toggle(place.id)} /><Link to={`/places/${place.id}`}><strong>{place.name}</strong><small>{place.address || '未填写地址'}</small></Link><span>{labelPlaceType(place.place_type)}</span><span>{stateLabels[place.user_state] ?? place.user_state}</span><span>{place.visibility === 'HIDDEN' ? '已隐藏' : '显示中'}</span><span><Link className="text-action" to={`/places/${place.id}`}>详情</Link><button className="icon-button" aria-label={`永久删除 ${place.name}`} onClick={() => setDeleting(place)}><Trash2 /></button></span></div>)}</div>{!all.length && <p className="empty-state">没有符合条件的地点。</p>}{deleting && <ConfirmDialog title="永久删除地点" description="地点域数据与路线引用会删除；来源、视频和 Evidence 会保留。" confirmLabel="永久删除地点" danger pending={hardDelete.isPending} error={hardDelete.error instanceof Error ? hardDelete.error.message : ''} onCancel={() => setDeleting(undefined)} onConfirm={() => hardDelete.mutate()} />}</div>
}
