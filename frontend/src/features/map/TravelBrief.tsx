import type { TravelBriefData } from '../../lib/types'
import { placeText } from './placePresentation'

export function TravelBrief({ brief, layout = 'preview' }: { brief?: TravelBriefData; layout?: 'preview' | 'detail' }) {
  return <div className={`travel-brief${layout === 'detail' ? ' travel-brief--detail' : ''}`}>
    <section><h3>何时去</h3><p>{placeText(brief?.timing) || '适合时节待补充。'}</p>{brief?.conditions?.map((text) => <p key={text}>{placeText(text)}</p>)}</section>
    {!!brief?.access?.length && <section><h3>怎么去</h3><ul>{brief.access.map((text) => <li key={text}>{placeText(text)}</li>)}</ul><small>{brief.source_label || '视频作者观点'}</small></section>}
    {!!brief?.warnings?.length && <section className="travel-brief__warnings"><h3>注意事项</h3><ul>{brief.warnings.map((text) => <li key={text}>{placeText(text)}</li>)}</ul></section>}
    {!!brief?.highlights?.length && <section><h3>看什么</h3><ul>{brief.highlights.map((text) => <li key={text}>{placeText(text)}</li>)}</ul></section>}
  </div>
}
