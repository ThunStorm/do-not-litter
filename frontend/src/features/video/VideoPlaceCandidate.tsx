import { Link } from 'react-router-dom'
import { RecommendationSummary } from '../../components/RecommendationSummary'
import type { VideoPlace } from '../../lib/api'
import { videoTimestampUrl } from './videoTime'

export function VideoPlaceCandidate({ place, canonicalUrl, platform }: { place: VideoPlace; canonicalUrl: string; platform: string }) {
  const reference = place.poi_policy === 'REFERENCE_ONLY' || place.poi_policy === 'SKIP'
  const area = place.poi_policy === 'AREA_RESOLVE'
  const confirmed = place.resolution_status === 'CONFIRMED' && place.place_id && place.place
  const anchor = place.resolution_status === 'AREA_RESOLVED' && place.destination?.anchor_kind
  const statuses: Record<string, string> = { REVIEW: '待确认', UNRESOLVED: '未定位', REJECTED: '已排除' }
  const status = confirmed ? '已确认' : anchor === 'SCENIC_ENTRY' ? '已定位至游客中心' : anchor === 'GOVERNMENT_SEAT' ? '已定位至政府驻地' : reference ? '背景提及' : place.resolution_status === 'AREA_UNRESOLVED' ? '区域待定位' : area ? '内容区域' : statuses[place.resolution_status] || '待确认'
  const name = confirmed ? place.place!.name : place.name
  const seconds = Math.floor((place.start_ms ?? 0) / 1000)
  const time = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
  return <li className="video-place">
    <div className="video-place__main"><div className="place-name-line">{confirmed ? <Link className="video-place__name" to={`/places/${place.place_id}`}>{name}</Link> : anchor && place.destination ? <Link className="video-place__name" to={`/map?place=${encodeURIComponent(place.destination.id)}`}>{name}</Link> : <strong>{name}</strong>}<RecommendationSummary value={place.recommendation_summary} compact /></div><small>{status}</small></div>
    {place.start_ms != null && platform !== 'LOCAL' ? <a className="video-place__time-link" href={videoTimestampUrl(canonicalUrl, place.start_ms)} target="_blank" rel="noreferrer" aria-label={`在新窗口打开视频并跳至 ${time}`}><time>{time}</time></a> : place.start_ms != null ? <time>{time}</time> : null}
  </li>
}
