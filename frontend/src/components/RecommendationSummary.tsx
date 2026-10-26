import { Link } from 'react-router-dom'
import type { Recommendation } from '../lib/types'

const labels: Record<string, string> = { RECOMMENDED: '作者推荐', OPTIONAL: '可顺路考虑', NOT_RECOMMENDED: '作者不推荐', CONFLICT: '作者意见有分歧', UNKNOWN: '态度未明确' }

export function RecommendationSummary({ value, compact = false }: { value?: Recommendation; compact?: boolean }) {
  const status = value?.status || 'UNKNOWN'
  const statements = value?.source_opinions?.flatMap((opinion) => opinion.statements || []) || []
  return <div className="recommendation-summary">
    <span className="recommendation-summary__label">{labels[status] || labels.UNKNOWN}{value?.review_required ? ' · 待核对' : ''}</span>
    {!compact && statements.length > 0 && <details><summary>作者意见与条件原文</summary><ul>{statements.map((statement, index) => <li key={`${statement.statement_id}-${index}`}>{statement.quote}{statement.speaker === 'OTHER' ? '（转述他人）' : ''}</li>)}</ul>{value?.source_opinions?.filter((opinion) => opinion.note_id).map((opinion) => <p key={opinion.mention_id}><Link to={`/video-notes/${opinion.note_id}`}>{opinion.title || '查看来源笔记'}</Link></p>)}</details>}
    {!compact && value?.source_opinions?.some((opinion) => opinion.assessment_status === 'LEGACY') && <small>旧提取记录，态度证据未按新规则复核。</small>}
  </div>
}
