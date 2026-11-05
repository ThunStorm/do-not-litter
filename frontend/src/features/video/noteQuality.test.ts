import { describe, expect, it } from 'vitest'

import type { VideoNoteDetail, VideoNoteSection } from '../../lib/types'
import { noteQualityGroups } from './noteQuality'

describe('note quality reading groups', () => {
  it('names a chapter once per issue category and retains the full issue count', () => {
    const quality = { issues: [
      { kind: 'AUTHOR_OPINION_REVIEW', section_ids: ['river'] },
      { kind: 'AUTHOR_OPINION_REVIEW', section_ids: ['river'] },
      { kind: 'POSSIBLE_SOURCE_OMISSION', section_ids: ['river'] },
      { kind: 'POSSIBLE_SOURCE_OMISSION', section_ids: [] },
    ] } as VideoNoteDetail['quality_summary']
    const result = noteQualityGroups(quality, [{ id: 'river', heading: '河池' }] as VideoNoteSection[])
    expect(result).toHaveLength(3)
    expect(result[0]).toEqual({ label: '河池：作者意见或条件待核对', sectionId: 'river', count: 2 })
    expect(result[1].label).toContain('河池：')
    expect(result[2].label).toContain('未归属原文：')
    expect(result[2].sectionId).toBeUndefined()
  })

  it('supports historical versions without quality information', () => {
    expect(noteQualityGroups(undefined, [])).toEqual([])
  })
})
