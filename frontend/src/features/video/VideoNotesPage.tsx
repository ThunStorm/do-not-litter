import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Clapperboard, ExternalLink, MapPin, Play, RotateCcw, Search, TextQuote } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'

import { EmptyState, PageHeader } from '../../components/AppShell'
import { api } from '../../lib/api'

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

export function VideoNotesPage() {
  const notes = useQuery({ queryKey: ['video-notes'], queryFn: () => api.videoNotes() })
  return <div className="page-frame video-notes-page"><PageHeader title="视频笔记" />
    <section className="video-notes-intro"><Clapperboard /><div><strong>把一段视频整理成可回看、可落点的笔记</strong><span>优先读取平台字幕；无字幕时由本机 Whisper 生成时间码转写。</span></div><Link className="button button--primary" to="/capture">投递视频链接</Link></section>
    <div className="search-field"><Search size={19} /><input aria-label="搜索视频笔记" placeholder="搜索视频标题" /></div>
    <section className="video-note-list">{notes.data?.length ? notes.data.map((note) => <Link key={note.id} to={`/video-notes/${note.id}`} className="video-note-row"><div className="video-note-row__cover">{note.cover_url ? <img src={note.cover_url} alt="" /> : <Clapperboard />}<span><Play size={14} />{duration(note.duration_ms)}</span></div><div><p>{note.status === 'COMPLETED' ? '笔记已完成' : note.status === 'PARTIAL_SUCCESS' ? '笔记已完成 · 地点待补全' : '处理中'}</p><h2>{note.title}</h2><small>{note.uploader || 'Bilibili'} · 已确认 {note.place_summary.confirmed}/{note.place_summary.total} 个地点</small><p className="video-note-row__overview">{note.overview || '正在生成结构化视频笔记…'}</p></div></Link>) : <EmptyState title="还没有视频笔记" detail="在投递页粘贴 Bilibili 视频链接，即可开始处理。" />}</section>
  </div>
}

export function VideoNoteDetailPage() {
  const { noteId = '' } = useParams()
  const client = useQueryClient()
  const note = useQuery({ queryKey: ['video-note', noteId], queryFn: () => api.videoNote(noteId) })
  const transcript = useQuery({ queryKey: ['video-transcript', noteId], queryFn: () => api.videoTranscript(noteId), enabled: Boolean(note.data) })
  const places = useQuery({ queryKey: ['video-places', noteId], queryFn: () => api.videoPlaces(noteId), enabled: Boolean(note.data) })
  const regenerate = useMutation({ mutationFn: () => api.regenerateVideoNote(noteId), onSuccess: () => void client.invalidateQueries({ queryKey: ['jobs'] }) })
  if (!note.data) return <div className="detail-loading">正在读取视频笔记…</div>
  return <div className="video-detail"><header className="detail-topbar"><Link to="/video-notes"><ArrowLeft />返回笔记</Link><span>视频 AI 笔记</span><button onClick={() => regenerate.mutate()}><RotateCcw />重新生成</button></header><article className="video-detail__body">
    <section className="video-hero"><div className="video-hero__cover">{note.data.cover_url ? <img src={note.data.cover_url} alt="" /> : <Clapperboard size={44} />}</div><div><p>来源视频 · {duration(note.data.duration_ms)}</p><h1>{note.data.title}</h1><a href={note.data.canonical_url} target="_blank" rel="noreferrer">在 Bilibili 打开 <ExternalLink size={15} /></a></div></section>
    <section className="video-note-prose"><h2>摘要</h2><p>{note.data.overview || '笔记正在生成，请稍后刷新。'}</p>{note.data.sections.map((section) => <section key={section.id}><div className="video-note-prose__heading"><h3>{section.heading}</h3><span>{timecode(section.start_ms)} — {timecode(section.end_ms)}</span></div><p>{section.body_markdown}</p></section>)}</section>
    <section className="video-evidence-grid"><div><h2><MapPin />地点候选</h2>{places.data?.length ? places.data.map((place) => <div className="video-place" key={place.id}><div><strong>{place.name}</strong><small>{place.resolution_status === 'CONFIRMED' ? place.place?.address || '已由高德确认' : '等待高德 POI 确认'}</small></div>{place.place_id ? <Link to={`/places/${place.place_id}`}>查看</Link> : <span>待确认</span>}</div>) : <p>模型尚未输出带证据的地点候选。</p>}</div><div><h2><TextQuote />时间码转写</h2><div className="transcript-preview">{transcript.data?.segments.slice(0, 8).map((segment) => <p key={segment.id}><time>{timecode(segment.start_ms)}</time>{segment.text}</p>) || <p>正在读取转写…</p>}</div></div></section>
  </article></div>
}
