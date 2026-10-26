import { expect, it } from 'vitest'
import type { MapMarker } from '../../lib/types'
import { clusterSummary, matchingCluster } from './clusterSummary'

const points = ['1', '2'].map((id) => ({ id, source_notes: [{ note_id: 'n', version_id: 'v', title: '雪景' }], travel_brief: { highlights: [`${id}有雾凇`] } } as MapMarker))
it('shows only a common exact note version and omits mixed sources', () => {
  expect(clusterSummary(points)?.highlights).toEqual(['1有雾凇', '2有雾凇'])
  expect(clusterSummary([points[0], { ...points[1], source_notes: [{ note_id: 'other', version_id: 'other', title: '' }] }])).toBeNull()
  expect(clusterSummary([points[0], { ...points[1], source_notes: [] }])).toBeNull()
})
it('closes when a cluster splits or loses a member, retains intact groups', () => {
  expect(matchingCluster([points], points)).toEqual(points)
  expect(matchingCluster([[points[0]], [points[1]]], points)).toBeNull()
  expect(matchingCluster([[points[0]]], points)).toBeNull()
})

it('does not generalize shared highlights across negative source opinions', () => {
  const note = { note_id: 'n', version_id: 'v', title: '同一视频' }
  const group = [
    { id: 'a', source_notes: [note], travel_brief: { highlights: ['山景很好'] }, recommendation_summary: { status: 'RECOMMENDED' } },
    { id: 'b', source_notes: [note], travel_brief: { highlights: ['船上景观'] }, recommendation_summary: { status: 'NOT_RECOMMENDED' } },
  ] as MapMarker[]
  expect(clusterSummary(group)).toBeNull()
})
