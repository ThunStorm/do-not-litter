import type { QueryClient } from '@tanstack/react-query'

const channelName = 'zhijian-travel-changes'
const keys = ['map', 'places', 'place-reviews', 'place-review-count', 'video-places', 'video-note', 'video-notes', 'travel-dashboard']
export function invalidateTravel(client: QueryClient) {
  return Promise.all(keys.map((key) => client.invalidateQueries({ queryKey: [key] })))
}
export function notifyTravelChange(client: QueryClient) {
  void invalidateTravel(client)
  if (typeof BroadcastChannel !== 'undefined') {
    const channel = new BroadcastChannel(channelName)
    channel.postMessage('changed')
    channel.close()
  }
}
export function subscribeTravelChanges(client: QueryClient) {
  if (typeof BroadcastChannel === 'undefined') return () => {}
  const channel = new BroadcastChannel(channelName)
  channel.onmessage = (event) => { if (event.data === 'changed') void invalidateTravel(client) }
  return () => channel.close()
}
