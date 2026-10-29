import { Link } from 'react-router-dom'
import type { PlaceVisitWindow } from '../../lib/types'
import { visitWindowLabel } from './placeLabels'

const derived = new Set(['SOURCE_FACT', 'TITLE_CONTEXT', 'SEMANTIC_CONTEXT', 'THEME_CONTEXT'])
export function VisitWindowList({ windows, onRemove }: { windows: PlaceVisitWindow[]; onRemove?: (id: string) => void }) {
  const seen = new Set<string>()
  const items = windows.filter((item) => {
    if (!derived.has(item.provenance)) return true
    const key = `${item.provenance}:${item.source_id}:${item.source_text}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
  return <ul className="place-insights">{items.map((item) => <li key={item.id}>
    <b>{item.valid_as_time === false ? '原有时间记录，尚待核对' : item.source_kind === 'COVER_TEXT' ? '封面文字推荐主题' : item.provenance === 'THEME_CONTEXT' ? '视频推荐主题' : item.provenance === 'SEMANTIC_CONTEXT' ? '同篇笔记中的季节背景' : item.provenance === 'TITLE_CONTEXT' ? '视频标题中的时间线索' : item.provenance === 'SOURCE_FACT' ? '视频原句' : visitWindowLabel(item)}</b>
    <q>{item.source_text || '用户补充'}</q>
    {item.source_kind === 'COVER_TEXT' && item.theme_context?.context?.cover_id && item.theme_context?.context?.cover_hash ? <a href={`/api/video-covers/${item.theme_context.context.cover_id}/evidence-image?content_hash=${item.theme_context.context.cover_hash}`} target="_blank" rel="noreferrer">查看封面原图</a> : null}
    {item.note_id ? <Link to={`/video-notes/${item.note_id}`}>查看主题来源</Link> : null}
    {onRemove && !derived.has(item.provenance) ? <button className="text-action" onClick={() => onRemove(item.id)}>移除</button> : null}
  </li>)}</ul>
}
