import type { VideoNoteDetail, VideoNoteSection } from '../../lib/types'

export function noteQualityGroups(quality: VideoNoteDetail['quality_summary'], sections: VideoNoteSection[]) {
  const names = new Map(sections.map((section) => [section.id, section.heading]))
  const groups = new Map<string, { label: string; sectionId?: string; count: number }>()
  for (const issue of quality?.issues ?? []) {
    const sectionId = issue.section_ids[0]
    const key = `${issue.kind}:${sectionId ?? 'unassigned'}`
    const previous = groups.get(key)
    if (previous) { previous.count++; continue }
    const reason = issue.kind === 'AUTHOR_OPINION_REVIEW' ? '作者意见或条件待核对' : issue.kind === 'POSSIBLE_SOURCE_OMISSION' ? '可能含尚未归纳的限制' : '证据尚未完整保留'
    groups.set(key, { label: `${names.get(sectionId) ?? '未归属原文'}：${reason}`, sectionId, count: 1 })
  }
  return [...groups.values()]
}
