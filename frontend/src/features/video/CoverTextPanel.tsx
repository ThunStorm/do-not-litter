import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Button } from '../../components/ui/Button'
import { api } from '../../lib/api'

export function CoverTextPanel({ noteId, available }: { noteId: string; available: boolean }) {
  const [allowVisual, setAllowVisual] = useState(false)
  const [showLatest, setShowLatest] = useState(false)
  const [selected, setSelected] = useState<number | null>(null)
  const evidence = useQuery({ queryKey: ['cover-text', noteId], queryFn: () => api.videoCoverText(noteId), enabled: available })
  const queue = useMutation({ mutationFn: () => api.queueCoverText(noteId, allowVisual) })
  if (!available) return null
  const value = showLatest ? evidence.data?.latest_extraction : evidence.data?.evidence ?? evidence.data?.latest_extraction
  const rows = value?.regions ?? []
  const box = selected === null ? null : rows[selected]?.bbox
  const imageUrl = value?.cover_id && value?.cover_hash ? `/api/video-covers/${value.cover_id}/evidence-image?content_hash=${value.cover_hash}` : undefined
  return <details className="video-section-sources"><summary>封面文字</summary>
    <p>{evidence.data?.applied_to_current_note && !showLatest ? '当前笔记使用的封面依据。' : value ? '独立提取结果，尚未用于当前笔记。' : '尚未提取封面文字。'}封面与正文分别保留来源。</p>
    {evidence.data?.evidence && evidence.data?.latest_extraction ? <Button variant="outline" onClick={() => { setShowLatest(!showLatest); setSelected(null) }}>{showLatest ? '查看当前笔记依据' : '查看新提取（未应用）'}</Button> : null}
    {!showLatest && evidence.data?.applicable_places?.length ? <ul>{evidence.data.applicable_places.map((place, i) => <li key={i}>{place.name}：{place.time_text}{place.relation === 'OPTIONAL' ? '可选主题' : '推荐主题'}（封面文字）</li>)}</ul> : null}
    {value?.status === 'NEEDS_REVIEW' ? <p>文字或时间关系需要核对，尚未作为推荐依据。</p> : null}
    {value?.vision_error_code ? <p>视觉识别暂不可用，已保留本地文字识别结果。</p> : null}
    {imageUrl ? <div style={{ position: 'relative', maxWidth: 672 }}><img src={imageUrl} alt="封面文字原始证据" style={{ width: '100%', display: 'block' }} />{box ? <span aria-hidden="true" style={{ position: 'absolute', left: `${box[0] * 100}%`, bottom: `${box[1] * 100}%`, width: `${box[2] * 100}%`, height: `${box[3] * 100}%`, border: '2px solid var(--color-accent)', pointerEvents: 'none' }} /> : null}</div> : null}
    {rows.length ? <ul>{rows.map((row, i) => <li key={i}><Button variant={selected === i ? 'primary' : 'outline'} onClick={() => setSelected(i)} aria-pressed={selected === i} style={{ overflowWrap: 'anywhere', whiteSpace: 'normal', height: 'auto', maxWidth: '100%' }}>{row.text}</Button></li>)}</ul> : null}
    <label className="toggle-field"><input type="checkbox" checked={allowVisual} onChange={e => setAllowVisual(e.target.checked)} />识别困难时使用已配置的视觉模型</label>
    <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 12, marginTop: 12 }}><Button variant="outline" disabled={queue.isPending} onClick={() => queue.mutate()}>{queue.isPending ? '正在排队…' : '提取封面文字'}</Button>{queue.data ? <Link to={`/tasks/${queue.data.job_id}`}>查看提取任务</Link> : null}</div>
    {queue.isError || evidence.isError ? <p role="alert">封面信息暂不可用，请稍后重试；正文不受影响。</p> : null}
  </details>
}
