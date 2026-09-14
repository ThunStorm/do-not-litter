import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Check, ChevronDown, MapPin, Pencil, X } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { api, type PlaceReview } from '../../lib/api'
import { videoTimestampUrl } from '../video/videoTime'

function timecode(value: number | null) {
  if (value == null) return '—'
  const seconds = Math.floor(value / 1000)
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
}

function VideoTimeLink({ canonicalUrl, value }: { canonicalUrl: string; value: number | null }) {
  if (value == null) return <time>—</time>
  const label = timecode(value)
  if (!canonicalUrl.startsWith('https://')) return <time>{label}</time>
  return <a className="review-time-link" href={videoTimestampUrl(canonicalUrl, value)} target="_blank" rel="noreferrer" aria-label={`在新窗口打开视频并跳至 ${label}`} title="在新窗口打开视频并跳至此时间"><time>{label}</time></a>
}

function Candidate({ candidate, pending, onConfirm }: { candidate: PlaceReview['candidates'][number]; pending: boolean; onConfirm: () => void }) {
  return <article><MapPin /><div><strong>{candidate.name}</strong><span>{candidate.address || '地址暂缺'}</span><small>{[candidate.city, candidate.district, candidate.typecode].filter(Boolean).join(' · ')}</small><small>匹配 {candidate.score} · {candidate.match_reasons.join('、') || '名称候选'}</small></div><button className="button button--primary" onClick={onConfirm} disabled={pending}><Check />确认此 POI</button></article>
}

export function PlaceReviewCard({ review, onJump }: { review: PlaceReview; onJump?: (sectionId: string) => void }) {
  const client = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [query, setQuery] = useState(review.suggested_name || review.name)
  const refresh = () => void Promise.all([
    client.invalidateQueries({ queryKey: ['place-reviews'] }),
    client.invalidateQueries({ queryKey: ['place-review-count'] }),
    client.invalidateQueries({ queryKey: ['video-places'] }),
    client.invalidateQueries({ queryKey: ['video-note'] }),
    client.invalidateQueries({ queryKey: ['map'] }),
  ])
  const reject = useMutation({ mutationFn: () => api.updatePlaceMention(review.mention_id, 'reject'), onSuccess: refresh })
  const confirm = useMutation({ mutationFn: (poiId: string) => api.confirmPlaceReview(review.mention_id, poiId, review.revision), onSuccess: refresh })
  const search = useMutation({ mutationFn: () => api.searchPlaceReview(review.mention_id, query, review.revision), onSuccess: () => { setEditing(false); refresh() } })
  const source = review.source_context
  const preferred = review.candidates[0]
  const remaining = review.candidates.slice(1)
  const geo = [review.review_context.geo_city, review.review_context.anchor_count ? `同段 ${review.review_context.anchor_count} 个可信锚点` : '无可信地点锚点'].filter(Boolean).join(' · ')

  return <section id={`review-${review.mention_id}`} className="panel place-review-card"><div className="panel__heading"><div><h2>{review.name}</h2><span>{review.place_type} · {review.reason || (review.resolution_status === 'UNRESOLVED' ? '尚未找到可靠 POI，请手动搜索' : '需要人工确认')}</span></div><div className="review-card__actions"><button className="button button--outline" onClick={() => setEditing(true)}><Pencil />搜索 POI</button><button className="button button--outline" onClick={() => reject.mutate()} disabled={reject.isPending}><X />不是地点</button></div></div><div className="review-decision"><strong>系统首选</strong><span>{preferred ? `${preferred.name} · ${preferred.address || '地址暂缺'}` : '暂无候选'}</span><small>{geo}</small></div><div className="review-source"><strong>{source.video_title}</strong>{source.section && <button className="text-action" onClick={() => onJump?.(source.section!.id)}>{source.section.heading}</button>}<small><VideoTimeLink canonicalUrl={source.canonical_url} value={source.start_ms} />–<VideoTimeLink canonicalUrl={source.canonical_url} value={source.end_ms} /> · {source.quote || '原文 Evidence 不可用'}</small>{source.transcript_expired ? <small>完整转写已过期</small> : <div className="review-transcript">{source.transcript_context.map((segment) => <p className={segment.is_evidence ? 'is-evidence' : ''} key={segment.id}><VideoTimeLink canonicalUrl={source.canonical_url} value={segment.start_ms} />{segment.text}</p>)}</div>}{source.screenshot && <img src={source.screenshot.image_url} alt={source.screenshot.caption || `${review.name}相关截图`} />}{source.video_note_id && !onJump && <Link to={`/video-notes/${source.video_note_id}${source.section ? `#section-${source.section.id}` : ''}`}>查看对应章节</Link>}</div>{editing && <form className="review-search" onSubmit={(event) => { event.preventDefault(); search.mutate() }}><input value={query} onChange={(event) => setQuery(event.target.value)} aria-label="搜索 POI 名称" /><button className="button button--primary" disabled={!query || search.isPending}>重新搜索</button><button type="button" className="text-action" onClick={() => setEditing(false)}>取消</button></form>}<div className="review-candidates">{preferred ? <Candidate candidate={preferred} pending={confirm.isPending} onConfirm={() => confirm.mutate(preferred.provider_id)} /> : <p className="review-candidates__empty">暂无可选 POI，请点击“搜索 POI”重新搜索。</p>}{remaining.length > 0 && <details className="review-candidates__more"><summary><ChevronDown />查看另外 {remaining.length} 个候选</summary>{remaining.map((candidate) => <Candidate candidate={candidate} pending={confirm.isPending} onConfirm={() => confirm.mutate(candidate.provider_id)} key={candidate.provider_id} />)}</details>}</div></section>
}
