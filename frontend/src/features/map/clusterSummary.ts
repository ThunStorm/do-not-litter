import type { MapMarker } from '../../lib/types'

export function clusterSummary(markers: MapMarker[]) {
  if (markers.some((m) => ['NOT_RECOMMENDED', 'CONFLICT'].includes(m.recommendation_summary?.status || '') || m.recommendation_summary?.review_required)) return null
  if (markers.length < 2 || markers.some((m) => m.source_notes?.length !== 1)) return null
  const note = markers[0].source_notes![0]
  if (!markers.every((m) => m.source_notes![0].note_id === note.note_id && m.source_notes![0].version_id === note.version_id)) return null
  const highlights = [...new Set(markers.flatMap((m) => m.travel_brief?.highlights ?? []))].slice(0, 3)
  return highlights.length ? { note, highlights } : null
}

export function matchingCluster(groups: MapMarker[][], current: MapMarker[]) {
  const ids = new Set(current.map((m) => m.id))
  return groups.find((g) => g.length === ids.size && g.every((m) => ids.has(m.id))) ?? null
}
