import type { PlaceReview, ReviewContract } from '../../lib/api'

const labels: Record<string, string> = {
  SEARCH_ERROR: '搜索失败，请重新搜索', NO_RESULTS: '未找到候选，可调整原词搜索',
  NAME_UNCERTAIN: '名称依据不足，请对照原文', AMBIGUOUS: '存在多个相近候选，请核对地址',
  OBJECT_CATEGORY: '对象类别不一致，请区分景区、入口与子景点', INCOMPLETE_CANDIDATES: '候选不完整，请核对后搜索',
  DETAIL_MISMATCH: '详情核验未通过，请核对名称和地址', INSUFFICIENT_EVIDENCE: '证据不足，请核对原句与时间码',
  MANUAL_RESULTS: '手动搜索结果，请核对位置', AREA_ONLY: '仅能定位区域',
  PLACE_JOB_ACTIVE: '所属任务运行中，暂不能编辑', MENTION_SUPERSEDED: '此地点版本已失效',
  PLACE_DELETED: '地点已删除，不能再次确认', DUPLICATE_PROVIDER_ID: '地点身份冲突，暂不能确认',
  INVALID_POI: '候选位置无效', MENTION_NOT_POI_ELIGIBLE: '此条目不允许确认地点',
}
export function reviewReason(code: string) { return labels[code] ?? '当前条件不允许此操作，请刷新权威数据后检查' }
export function reviewAction(contract: ReviewContract | undefined, action: string, poiId?: string) {
  if (!contract || contract.version !== 'poi-review-v1') return false
  return (poiId ? contract.candidate_actions.find((c) => c.provider_id === poiId)?.allowed_actions : contract.allowed_actions)?.includes(action) ?? false
}
export function reviewNoteLink(review: PlaceReview) {
  const source = review.source_context
  const version = source.ai_note_version_id
  return source.video_note_id && version && source.section ? `/video-notes/${encodeURIComponent(source.video_note_id)}?version=${encodeURIComponent(version)}#section-${source.section.id}` : null
}
