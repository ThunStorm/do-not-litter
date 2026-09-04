import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Check, MapPin, Pencil, RotateCcw, X } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../../lib/api'

type Candidate = { provider_id: string; name: string; address: string; score: number; match_reasons: string[] }
type Review = { mention_id: string; name: string; place_type: string; reason: string; revision: number; candidates: Candidate[] }

export function PlaceReviewsPage() {
  const client = useQueryClient()
  const reviews = useQuery({ queryKey: ['place-reviews'], queryFn: api.placeReviews })
  const [editing, setEditing] = useState<string>()
  const [query, setQuery] = useState('')
  const [undo, setUndo] = useState<string>()
  const refresh = () => void client.invalidateQueries({ queryKey: ['place-reviews'] })
  const reject = useMutation({ mutationFn: (mentionId: string) => api.updatePlaceMention(mentionId, 'reject'), onSuccess: (_value, mentionId) => { setUndo(mentionId); refresh() } })
  const restore = useMutation({ mutationFn: (mentionId: string) => api.updatePlaceMention(mentionId, 'restore'), onSuccess: () => { setUndo(undefined); refresh() } })
  const confirm = useMutation({ mutationFn: ({ mentionId, poiId, revision }: { mentionId: string; poiId: string; revision: number }) => api.confirmPlaceReview(mentionId, poiId, revision), onSuccess: refresh })
  const search = useMutation({ mutationFn: ({ mentionId, value, revision }: { mentionId: string; value: string; revision: number }) => api.searchPlaceReview(mentionId, value, revision), onSuccess: () => { setEditing(undefined); refresh() } })
  const active = reviews.data as Review[] | undefined
  return <div className="page-frame place-reviews"><header className="detail-topbar"><Link to="/map"><ArrowLeft />返回地图</Link><span>待确认地点</span><span /></header>{undo && <div className="review-toast" role="status">已移出审核队列 <button onClick={() => restore.mutate(undo)} disabled={restore.isPending}><RotateCcw />撤销</button></div>}{active?.length ? active.map((review) => <section className="panel" key={review.mention_id}><div className="panel__heading"><div><h2>{review.name}</h2><span>{review.place_type} · {review.reason || '需要人工确认'}</span></div><div className="review-card__actions"><button className="button button--outline" onClick={() => { setEditing(review.mention_id); setQuery(review.name) }}><Pencil />修正名称</button><button className="button button--outline" onClick={() => reject.mutate(review.mention_id)} disabled={reject.isPending && reject.variables === review.mention_id}><X />{reject.isPending && reject.variables === review.mention_id ? '处理中' : '不是地点'}</button></div></div>{editing === review.mention_id && <form className="review-search" onSubmit={(event) => { event.preventDefault(); search.mutate({ mentionId: review.mention_id, value: query, revision: review.revision }) }}><input value={query} onChange={(event) => setQuery(event.target.value)} aria-label="修正后的地点名称" /><button className="button button--primary" disabled={!query || search.isPending}>重新搜索</button><button type="button" className="text-action" onClick={() => setEditing(undefined)}>取消</button></form>}<div className="review-candidates">{review.candidates.map((candidate) => <article key={candidate.provider_id}><MapPin /><div><strong>{candidate.name}</strong><span>{candidate.address}</span><small>匹配 {candidate.score} · {candidate.match_reasons.join('、') || '名称候选'}</small></div><button className="button button--primary" onClick={() => confirm.mutate({ mentionId: review.mention_id, poiId: candidate.provider_id, revision: review.revision })} disabled={confirm.isPending && confirm.variables?.mentionId === review.mention_id}><Check />选择</button></article>)}</div></section>) : <section className="panel"><h2>没有待确认地点</h2><p>歧义 POI 会在这里等待你的选择。</p></section>}</div>
}
