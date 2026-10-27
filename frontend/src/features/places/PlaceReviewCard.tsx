import { RecommendationSummary } from '../../components/RecommendationSummary'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Check, ChevronDown, MapPin, Pencil, X } from 'lucide-react'
import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { notifyTravelChange } from '../../lib/travelChanges'
import { api, type PlaceReview } from '../../lib/api'
import { videoTimestampUrl } from '../video/videoTime'
import { labelPlaceType } from '../map/placeLabels'

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
  return <article><MapPin /><div><strong>{candidate.name}</strong><span>{candidate.address || '地址暂缺'}</span><small>{[candidate.city, candidate.district, candidate.typecode].filter(Boolean).join(' · ')}</small><small>匹配 {candidate.score} · {candidate.match_reasons.join('、') || '名称候选'}</small></div><button className="button button--primary" onClick={onConfirm} disabled={pending}><Check />确认地点位置</button></article>
}

export function PlaceReviewCard({ review, onJump, onConfirmed }: { review: PlaceReview; onJump?: (sectionId: string) => void; onConfirmed?: (placeId: string) => void }) {
  const client = useQueryClient()
  const [editing, setEditing] = useState(false)
  const searchBusy = useRef(false)
  const [query, setQuery] = useState(review.suggested_name || review.name)
  const [searchResult, setSearchResult] = useState<{ revision: number; candidates: PlaceReview['candidates'] } | null>(null)
  const refresh = () => notifyTravelChange(client)
  const onConflict = (error: Error) => { if (error.message.includes('409')) refresh() }
  const reject = useMutation({ mutationFn: () => api.updatePlaceMention(review.mention_id, 'reject'), onSuccess: refresh, onError: onConflict })
  const currentRevision = Math.max(review.revision, searchResult?.revision ?? 0)
  const confirm = useMutation({ mutationFn: (poiId: string) => api.confirmPlaceReview(review.mention_id, poiId, currentRevision), onSuccess: (data) => { onConfirmed?.(data.place_id); refresh() }, onError: onConflict })
  const search = useMutation({ mutationFn: () => api.searchPlaceReview(review.mention_id, query.trim(), currentRevision), onSuccess: (data) => { setSearchResult(data); refresh() }, onError: onConflict, onSettled: () => { searchBusy.current = false } })
  const busy = search.isPending || confirm.isPending || reject.isPending
  const source = review.source_context
  const candidates = searchResult && searchResult.revision >= review.revision ? searchResult.candidates : review.candidates
  const manualCandidates = (searchResult && searchResult.revision >= review.revision) || review.candidate_source === 'MANUAL'
  const preferred = candidates[0]
  const remaining = candidates.slice(1)
  const geo = [review.review_context.geo_city, review.review_context.anchor_count ? `同段 ${review.review_context.anchor_count} 个可信锚点` : '无可信地点锚点'].filter(Boolean).join(' · ')

  if (confirm.isSuccess) return <section className="panel place-review-card" role="status"><strong>地点位置已确认</strong><RecommendationSummary value={review.recommendation_summary} compact /><RecommendationSummary value={review.recommendation_summary} /><p>全国视野会以聚合数量或独立标记显示该地点。</p><Link className="button button--primary" to={`/map?place=${encodeURIComponent(confirm.data.place_id)}`}>在地图查看</Link></section>

  return <section id={`review-${review.mention_id}`} className="panel place-review-card"><div className="panel__heading"><div><div className="place-name-line"><h2>{review.name}</h2><RecommendationSummary value={review.recommendation_summary} compact /></div><RecommendationSummary value={review.recommendation_summary} /><span>{labelPlaceType(review.place_type)} · {manualCandidates ? '自动解析记录：' : ''}{review.reason || (review.resolution_status === 'UNRESOLVED' ? '尚未找到可靠 POI，请手动搜索' : '需要人工确认')}</span></div><div className="review-card__actions"><button className="button button--outline" onClick={() => setEditing(true)} disabled={busy}><Pencil />搜索 POI</button><button className="button button--outline" onClick={() => reject.mutate()} disabled={busy}><X />不是地点</button></div></div><div className="review-decision"><strong>{review.visit_intent === 'NOT_RECOMMENDED' ? '作者不推荐 · 待人工检核' : manualCandidates ? '手动搜索结果' : review.candidate_source === 'HISTORICAL' ? '已保存候选' : '系统首选'}</strong><span>{preferred ? `${preferred.name} · ${preferred.address || '地址暂缺'}` : '暂无候选'}</span><small>{geo}</small></div><div className="review-source"><strong>{source.video_title}</strong>{source.section && <button className="text-action" onClick={() => onJump?.(source.section!.id)}>{source.section.heading}</button>}<small><VideoTimeLink canonicalUrl={source.canonical_url} value={source.start_ms} />–<VideoTimeLink canonicalUrl={source.canonical_url} value={source.end_ms} /> · {source.quote || '原文 Evidence 不可用'}</small>{source.transcript_expired ? <small>完整转写已过期</small> : <div className="review-transcript">{source.transcript_context.map((segment) => <p className={segment.is_evidence ? 'is-evidence' : ''} key={segment.id}><VideoTimeLink canonicalUrl={source.canonical_url} value={segment.start_ms} />{segment.text}</p>)}</div>}{source.screenshot && <img src={source.screenshot.image_url} alt={source.screenshot.caption || `${review.name}相关截图`} />}{source.video_note_id && !onJump && <Link to={`/video-notes/${source.video_note_id}${source.section ? `#section-${source.section.id}` : ''}`}>查看对应章节</Link>}</div>{editing && <div><form className="review-search" onSubmit={(event) => { event.preventDefault(); if (searchBusy.current || busy || !query.trim()) return; searchBusy.current = true; search.mutate() }}><input value={query} onChange={(event) => { setQuery(event.target.value); search.reset() }} aria-label="搜索 POI 名称" disabled={busy} /><button className="button button--primary" disabled={!query.trim() || busy}>{search.isPending ? '正在搜索…' : '重新搜索'}</button><button type="button" className="text-action" disabled={busy} onClick={() => setEditing(false)}>取消</button></form>{search.isSuccess && <p role="status">{search.data.candidates.length ? `搜索到 ${search.data.candidates.length} 个候选${search.data.search_status === 'PARTIAL' ? '，结果可能不完整' : ''}` : '没有找到匹配地点，请尝试其他名称。'}</p>}{search.isError && <p role="alert">{search.error.message.includes('409') ? '地点信息已更新，请检查最新候选后重试。' : `搜索失败：${search.error.message}`}</p>}</div>}{confirm.isError && <p role="alert">确认失败：{confirm.error.message}</p>}{reject.isError && <p role="alert">操作失败：{reject.error.message}</p>}<div className="review-candidates">{preferred ? <Candidate candidate={preferred} pending={busy} onConfirm={() => confirm.mutate(preferred.provider_id)} /> : <p className="review-candidates__empty">暂无可选 POI，请点击“搜索 POI”重新搜索。</p>}{remaining.length > 0 && <details className="review-candidates__more"><summary><ChevronDown />查看另外 {remaining.length} 个候选</summary>{remaining.map((candidate) => <Candidate candidate={candidate} pending={busy} onConfirm={() => confirm.mutate(candidate.provider_id)} key={candidate.provider_id} />)}</details>}</div></section>
}
