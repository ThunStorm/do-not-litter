import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Clapperboard, Download, ExternalLink, MapPin, MoreHorizontal, Play, RotateCcw, Search, TextQuote, Trash2, X } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { EmptyState, PageHeader } from '../../components/AppShell'
import { MarkdownContent } from '../../components/MarkdownContent'
import { api, type PlaceReview, type VideoPlace } from '../../lib/api'
import { PlaceReviewCard } from '../places/PlaceReviewCard'

function duration(value: number | null) {
  if (!value) return '时长待读取'
  const seconds = Math.floor(value / 1000)
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
}

function timecode(value: number | null) {
  if (value == null) return '—'
  const seconds = Math.floor(value / 1000)
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
}

function VideoCover({ url, alt, fallback = true }: { url: string | null; alt: string; fallback?: boolean }) {
  const [failed, setFailed] = useState(false)
  if (url && !failed) return <img src={url} alt={alt} onError={() => setFailed(true)} />
  return fallback ? <Clapperboard size={30} aria-label="视频封面不可用" /> : null
}

function DeleteMenu({ label, disabled, onDelete }: { label: string; disabled: boolean; onDelete: () => void }) {
  return <details className="overflow-menu"><summary aria-label={`${label}更多操作`}><MoreHorizontal /></summary><div><button disabled={disabled} onClick={onDelete}><Trash2 />删除笔记</button></div></details>
}

function InsightChips({ insights, jump }: { insights: Array<{ insight_type: string; value_text: string; source_quote: string; target_section_id: string | null }>; jump: (sectionId?: string | null) => void }) {
  return insights.length ? <ul className="video-place__insights">{insights.slice(0, 4).map((item) => <li key={`${item.insight_type}-${item.value_text}`}><button title={item.source_quote || '回到对应证据'} onClick={() => jump(item.target_section_id)}>{item.value_text}</button></li>)}</ul> : null
}

function VideoPlaceCandidate({ place, review, jump, jumpToReview }: { place: VideoPlace; review?: PlaceReview; jump: (sectionId?: string | null) => void; jumpToReview: (mentionId: string) => void }) {
  if (place.resolution_status === 'CONFIRMED' && place.place_id && place.place) return <div className="video-place video-place--confirmed"><Link to={`/places/${place.place_id}`}><strong>{place.place.name}</strong><small>{place.place.address || '已确认 POI'}</small></Link></div>
  return <div className="video-place"><button onClick={() => jump(place.target_section_id)}><strong>{place.name}</strong><small>待确认</small></button><time>{timecode(place.start_ms)}</time><InsightChips insights={place.insights} jump={jump} />{review ? <button className="text-action" onClick={() => jumpToReview(place.id)}>确认 POI</button> : null}</div>
}

export function VideoNotesPage() {
  const notes = useQuery({ queryKey: ['video-notes'], queryFn: () => api.videoNotes() })
  const client = useQueryClient()
  const remove = useMutation({ mutationFn: (id: string) => api.deleteVideoNote(id), onSuccess: () => { void client.invalidateQueries({ queryKey: ['video-notes'] }); void client.invalidateQueries({ queryKey: ['content'] }); void client.invalidateQueries({ queryKey: ['dashboard'] }); void client.invalidateQueries({ queryKey: ['sources'] }) } })
  function requestDelete(note: { id: string; title: string }) {
    if (window.confirm(`删除《${note.title}》及其内容投影？若来源已无其他内容或活跃任务，来源视频、完整转写和审计记录会一并清理；地点与路线保留。此操作无法撤销。`)) remove.mutate(note.id)
  }
  return <div className="page-frame video-notes-page"><PageHeader title="视频笔记" />
    <section className="video-notes-intro"><Clapperboard /><div><strong>把视频整理成可回看、可落点的笔记</strong><span>读取字幕或语音识别，AI 校对后生成主旨、地点与关键截图。</span></div><Link className="button button--primary" to="/capture">添加视频链接</Link></section>
    <div className="search-field"><Search size={19} /><input aria-label="搜索视频笔记" placeholder="搜索视频标题" /></div>
    <section className="video-note-list">{notes.data?.length ? notes.data.map((note) => <div key={note.id} className="video-note-row-wrap"><Link to={`/video-notes/${note.id}`} className="video-note-row"><div className="video-note-row__cover"><VideoCover url={note.cover_image_url ?? null} alt={note.title} /><span><Play size={14} />{duration(note.duration_ms)}</span></div><div><p>{note.status === 'COMPLETED' ? '笔记已完成' : note.status === 'PARTIAL_SUCCESS' ? '笔记已完成 · 地点待补全' : '处理中'}</p><h2>{note.title}</h2><small>{note.uploader || 'Bilibili'} · 已确认 {note.place_summary.confirmed}/{note.place_summary.total} 个地点</small><p className="video-note-row__overview">{note.overview || '正在生成结构化视频笔记…'}</p></div></Link><DeleteMenu label={note.title} disabled={remove.isPending} onDelete={() => requestDelete(note)} /></div>) : <EmptyState title="还没有视频笔记" detail="在投递页粘贴 Bilibili 视频链接，即可开始处理。" />}</section>
  </div>
}

export function VideoNoteDetailPage() {
  const { noteId = '' } = useParams()
  const client = useQueryClient()
  const [lightbox, setLightbox] = useState<{ src: string; alt: string } | null>(null)
  const note = useQuery({ queryKey: ['video-note', noteId], queryFn: () => api.videoNote(noteId) })
  const canonicalNoteId = note.data?.id ?? noteId
  const transcript = useQuery({ queryKey: ['video-transcript', canonicalNoteId], queryFn: () => api.videoTranscript(canonicalNoteId), enabled: Boolean(note.data) })
  const places = useQuery({ queryKey: ['video-places', canonicalNoteId], queryFn: () => api.videoPlaces(canonicalNoteId), enabled: Boolean(note.data) })
  const screenshots = useQuery({ queryKey: ['video-screenshots', canonicalNoteId], queryFn: () => api.videoScreenshots(canonicalNoteId), enabled: Boolean(note.data) })
  const reviews = useQuery({ queryKey: ['place-reviews', canonicalNoteId], queryFn: () => api.placeReviews(canonicalNoteId), enabled: Boolean(note.data) })
  const regenerate = useMutation({ mutationFn: () => api.regenerateVideoNote(canonicalNoteId), onSuccess: () => void client.invalidateQueries({ queryKey: ['jobs'] }) })
  const remove = useMutation({ mutationFn: () => api.deleteVideoNote(canonicalNoteId), onSuccess: () => { void client.invalidateQueries({ queryKey: ['video-notes'] }); void client.invalidateQueries({ queryKey: ['sources'] }); window.location.assign('/video-notes') } })
  useEffect(() => {
    if (!lightbox) return
    const close = (event: KeyboardEvent) => { if (event.key === 'Escape') setLightbox(null) }
    window.addEventListener('keydown', close)
    return () => window.removeEventListener('keydown', close)
  }, [lightbox])
  const sectionForSegment = useMemo(() => {
    const result = new Map<string, string>()
    note.data?.sections.forEach((section) => section.segment_ids.forEach((id) => result.set(id, section.id)))
    return result
  }, [note.data?.sections])
  const jump = (sectionId?: string | null) => {
    if (!sectionId) return
    const target = document.getElementById(`section-${sectionId}`)
    target?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    target?.focus({ preventScroll: true })
  }
  const jumpToReview = (mentionId: string) => document.getElementById(`review-${mentionId}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  if (note.isPending) return <div className="detail-loading">正在读取视频笔记…</div>
  if (note.isError) return <div className="detail-loading"><p>无法读取视频笔记：{note.error instanceof Error ? note.error.message : '请求失败'}</p><div><Link className="button button--outline" to="/video-notes"><ArrowLeft />返回视频笔记</Link><button className="button button--primary" onClick={() => void note.refetch()}>重试读取</button></div></div>
  if (!note.data) return <div className="detail-loading">视频笔记不存在。</div>
  const legacyNeedsRegeneration = note.data.needs_regeneration
  const requestDelete = () => { if (window.confirm(`删除《${note.data.title}》及其内容投影？若来源已无其他内容或活跃任务，来源视频、完整转写和审计记录会一并清理；地点与路线保留。此操作无法撤销。`)) remove.mutate() }
  return <div className="video-detail"><header className="detail-topbar"><Link to="/video-notes"><ArrowLeft />返回笔记</Link><span>视频 AI 笔记</span><div><DeleteMenu label={note.data.title} disabled={remove.isPending} onDelete={requestDelete} /><button onClick={() => regenerate.mutate()}><RotateCcw />重新生成</button></div></header><article className="video-detail__body">
    <section className={`video-hero ${note.data.cover_image_url ? '' : 'video-hero--no-cover'}`}>{note.data.cover_image_url && <div className="video-hero__cover"><VideoCover url={note.data.cover_image_url} alt={`${note.data.title} 封面`} fallback={false} /><span>{duration(note.data.duration_ms)}</span></div>}<div><h1>{note.data.title}</h1><a href={note.data.canonical_url} target="_blank" rel="noreferrer">在 Bilibili 打开 <ExternalLink size={15} /></a></div></section>
    {legacyNeedsRegeneration && <section className="video-quality-notice"><div><strong>旧版正文已隐藏</strong><span>这份笔记生成于 AI 转写校对工序上线前。为避免口音误读继续影响摘要、目录和地点，请重新生成。</span></div><button className="button button--primary" onClick={() => regenerate.mutate()} disabled={regenerate.isPending}><RotateCcw />应用新版校对流程</button></section>}
    <section className="video-note-prose video-summary"><h2><TextQuote />AI 摘要</h2><div className="video-markdown"><MarkdownContent value={legacyNeedsRegeneration ? '等待按新版 AI 校对流程重新生成，未经校对的旧摘要不再展示。' : note.data.overview || '笔记正在生成，请稍后刷新。'} /></div></section>
    <nav className="video-toc" aria-label="主旨目录"><h2><TextQuote />主旨目录</h2><div>{note.data.sections.map((section, index) => <button key={section.id} onClick={() => jump(section.id)}><time>{timecode(section.start_ms)}</time><span>{legacyNeedsRegeneration ? `章节 ${index + 1} · 待重新归纳` : section.heading}</span></button>)}</div></nav>
    <section className="video-note-prose video-timeline"><h2>按时间线详述</h2>{note.data.sections.length ? note.data.sections.map((section) => {
      const shots = screenshots.data?.filter((shot) => shot.section_id === section.id && shot.status === 'READY') ?? []
      const concise = legacyNeedsRegeneration ? '本章节旧版转写未经 AI 校对，已暂时隐藏。重新生成后将显示主旨与要点。' : section.bullets?.length ? section.bullets.map((value) => `- ${value}`).join('\n') : section.summary || section.body_markdown
      const heading = legacyNeedsRegeneration ? '章节内容待重新归纳' : section.heading
      return <section id={`section-${section.id}`} tabIndex={-1} key={section.id}><div className="video-note-prose__heading"><time>{timecode(section.start_ms)}</time><h3>{heading}</h3></div><div className={`video-section-layout ${shots.length ? 'video-section-layout--with-shot' : ''}`}><div className="video-markdown"><MarkdownContent value={concise} /></div>{shots.slice(0, 1).map((shot) => <button className="video-section-shot" key={shot.id} onClick={() => shot.image_url && setLightbox({ src: shot.image_url, alt: shot.caption || `${heading}关键截图` })}><img src={shot.image_url ?? ''} alt={shot.caption || `${heading}关键截图`} /><span><b>{shot.caption || shot.selection_reason}</b><time>{timecode(shot.actual_timestamp_ms)}</time><em>点击放大</em></span></button>)}</div></section>
    }) : <p>时间线章节正在生成。</p>}</section>
    <section className="video-evidence-grid"><div><h2><MapPin />地点候选</h2>{legacyNeedsRegeneration ? <p>旧版地点候选可能受口音误读影响，已隐藏；重新生成后再由地图搜索校对。</p> : places.data?.length ? places.data.map((place) => <VideoPlaceCandidate place={place} review={reviews.data?.find((item) => item.mention_id === place.id)} key={place.id} jump={jump} jumpToReview={jumpToReview} />) : <p>模型尚未输出带证据的地点候选。</p>}</div><div><div className="transcript-card-heading"><h2><TextQuote />完整转写</h2>{note.data.transcript_status !== 'EXPIRED' && !legacyNeedsRegeneration && <a className="transcript-export" href={api.videoTranscriptExportUrl(canonicalNoteId, 'corrected')}><Download />导出 TXT</a>}</div>{note.data.transcript_status === 'EXPIRED' ? <p>完整转写已按 180 天策略删除。</p> : legacyNeedsRegeneration ? <p>旧版原始识别稿已保留，但不会冒充 AI 校对稿展示或导出。重新生成后可查看校对版本。</p> : <><p className="transcript-retention">共 {note.data.transcript_segment_count} 段 · AI 校对稿 · 保留至 {note.data.transcript_retention_until ? new Date(note.data.transcript_retention_until).toLocaleDateString('zh-CN', { timeZone: 'Asia/Shanghai' }) : '待生成'}</p><div className="transcript-preview">{transcript.data?.segments.slice(0, 8).map((segment) => <button key={segment.id} onClick={() => jump(sectionForSegment.get(segment.id))}><time>{timecode(segment.start_ms)}</time><span>{segment.text}</span></button>) || <p>正在读取转写…</p>}</div></>}</div></section>{!legacyNeedsRegeneration && reviews.data?.length ? <section className="video-note-reviews"><h2><MapPin />待确认地点</h2>{reviews.data.map((review) => <PlaceReviewCard review={review} key={review.mention_id} onJump={jump} />)}</section> : null}
  </article>{lightbox && <div className="video-lightbox" role="dialog" aria-modal="true" aria-label={lightbox.alt} onClick={() => setLightbox(null)}><button aria-label="关闭图片"><X /></button><img src={lightbox.src} alt={lightbox.alt} onClick={(event) => event.stopPropagation()} /></div>}</div>
}
