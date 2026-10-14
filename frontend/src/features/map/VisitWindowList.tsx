import type { PlaceVisitWindow } from '../../lib/types'
import { visitWindowLabel } from './placeLabels'

export function VisitWindowList({ windows, onRemove }: { windows: PlaceVisitWindow[]; onRemove: (id: string) => void }) {
  return <ul className="place-insights">{windows.map((item) => <li key={item.id}><b>{visitWindowLabel(item)}</b>{item.source_text || '用户补充'}{item.provenance === 'TITLE_CONTEXT' ? ' · 来自视频标题' : item.provenance === 'SOURCE_FACT' ? ' · 正文原句佐证' : ''}{!['SOURCE_FACT', 'TITLE_CONTEXT'].includes(item.provenance) ? <button className="text-action" onClick={() => onRemove(item.id)}>移除</button> : null}</li>)}</ul>
}
