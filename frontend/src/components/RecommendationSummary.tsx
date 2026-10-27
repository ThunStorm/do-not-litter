import { Link } from 'react-router-dom'
import type { Recommendation } from '../lib/types'

// Recommendation is implicit in the reading UI; only a negative source gets a name-side mark.
export function RecommendationSummary({ value, compact = false }: { value?: Recommendation; compact?: boolean }) {
  if (compact) {
    if (value?.status !== 'NOT_RECOMMENDED' && value?.status !== 'CONFLICT') return null
    const label = value.status === 'CONFLICT' ? '有来源不推荐' : '不推荐'
    return <span className="recommendation-summary__label" title="视频作者的地点意见">{label}</span>
  }
  const statements = value?.source_opinions?.flatMap((opinion) => opinion.statements || []) || []
  if (!statements.length) return null
  return <div className="recommendation-summary"><details><summary>作者意见与条件原文</summary><ul>{statements.map((statement, index) => <li key={`${statement.statement_id}-${index}`}>{statement.quote}{statement.speaker === 'OTHER' ? '（转述他人）' : ''}</li>)}</ul>{value?.source_opinions?.filter((opinion) => opinion.note_id).map((opinion) => <p key={opinion.mention_id}><Link to={`/video-notes/${opinion.note_id}`}>{opinion.title || '查看来源笔记'}</Link></p>)}</details></div>
}
