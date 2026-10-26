import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, MapPinCheck } from 'lucide-react'
import { Link } from 'react-router-dom'

import { api } from '../../lib/api'
import { PlaceReviewCard } from '../places/PlaceReviewCard'

export function PlaceReviewsPage() {
  const [confirmedId, setConfirmedId] = useState('')
  const reviews = useQuery({ queryKey: ['place-reviews'], queryFn: () => api.placeReviews() })
  return <div className="page-frame place-reviews"><header className="detail-topbar"><Link to="/map"><ArrowLeft />返回地图</Link><span>待确认地点</span><span /></header>{confirmedId ? <p role="status">地点已确认 <Link to={`/map?place=${encodeURIComponent(confirmedId)}`}>在地图查看</Link></p> : null}{reviews.data?.length ? reviews.data.map((review) => <PlaceReviewCard onConfirmed={setConfirmedId} review={review} key={review.mention_id} />) : <section className="panel review-empty-state"><MapPinCheck /><h2>没有待确认地点</h2><p>出现无法自动确认的地点时，会在这里等待你选择。</p></section>}</div>
}
