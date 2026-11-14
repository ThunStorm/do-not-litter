import { describe, expect, it } from 'vitest'
import { reviewAction, reviewNoteLink } from './reviewContract'
import type { PlaceReview, ReviewContract } from '../../lib/api'
describe('authority review links and actions', () => {
  it('requires an exact version and section without guessing identities', () => {
    const source = { video_note_id: 'note_a', ai_note_version_id: 'ntv_old', section: { id: 'old' } }
    expect(reviewNoteLink({ source_context: source } as PlaceReview)).toBe('/video-notes/note_a?version=ntv_old#section-old')
    expect(reviewNoteLink({ source_context: { ...source, ai_note_version_id: null } } as PlaceReview)).toBeNull()
  })
  it('fails closed for missing and incompatible contracts and candidate blockers', () => {
    expect(reviewAction(undefined, 'SEARCH')).toBe(false)
    const contract = { version: 'poi-review-v1', allowed_actions: ['SEARCH'], candidate_actions: [{ provider_id: 'p', allowed_actions: [], blocked_by: ['PLACE_DELETED'] }] } as unknown as ReviewContract
    expect(reviewAction(contract, 'SEARCH')).toBe(true)
    expect(reviewAction(contract, 'CONFIRM', 'p')).toBe(false)
    expect(reviewAction({ ...contract, version: 'future' }, 'SEARCH')).toBe(false)
  })
})
