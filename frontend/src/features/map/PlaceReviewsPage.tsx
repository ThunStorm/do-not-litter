import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, MapPinCheck } from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'

import { api } from '../../lib/api'
import { PlaceReviewCard } from '../places/PlaceReviewCard'

export function PlaceReviewsPage() {
  const [params, setParams] = useSearchParams()
  const selected = params.get('mention')
  const [confirmedId, setConfirmedId] = useState('')
  const reviews = useQuery({ queryKey: ['place-reviews'], queryFn: () => api.placeReviews() })
  useEffect(() => {
    if (!selected || !reviews.data) return
    const target = document.getElementById(`review-${selected}`)
    target?.scrollIntoView({ block: 'start' })
    target?.focus({ preventScroll: true })
  }, [selected, reviews.data])
  if (reviews.isPending) return <p role="status">正在读取待核地点…</p>
  if (reviews.isError) return <p role="alert">待核地点读取失败：{reviews.error.message}<button className="text-action" onClick={() => void reviews.refetch()}>重试</button></p>
  return <div className="page-frame place-reviews"><header className="detail-topbar"><Link to="/map"><ArrowLeft />返回地图</Link><span>待确认地点</span><span /></header><p role="status">{reviews.data?.length ?? 0} 个地点问题{selected ? ' · 已定位目标' : ''}</p>{selected && !reviews.data?.some((r) => r.mention_id === selected) && <p role="status">目标已处理或版本已失效，未跳转到其他版本。</p>}{selected && <button className="button button--outline" onClick={() => setParams({})}>显示全部待核地点</button>}{confirmedId ? <p role="status">地点已确认 <Link to={`/map?place=${encodeURIComponent(confirmedId)}`}>在地图查看</Link></p> : null}{reviews.data?.length ? reviews.data.map((review) => <PlaceReviewCard onConfirmed={setConfirmedId} review={review} key={review.mention_id} />) : <section className="panel review-empty-state"><MapPinCheck /><h2>没有待确认地点</h2><p>出现无法自动确认的地点时，会在这里等待你选择。</p></section>}</div>
}
