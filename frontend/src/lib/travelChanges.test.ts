import { QueryClient } from '@tanstack/react-query'
import { afterEach, expect, it, vi } from 'vitest'

import { notifyTravelChange, subscribeTravelChanges } from './travelChanges'

afterEach(() => vi.unstubAllGlobals())
it('invalidates a mounted map cache in another window without storing credentials or place data', async () => {
  const listeners = new Set<Channel>()
  class Channel {
    onmessage: ((event: { data: unknown }) => void) | null = null
    constructor() { listeners.add(this) }
    postMessage(data: unknown) { for (const peer of listeners) if (peer !== this) peer.onmessage?.({ data }) }
    close() { listeners.delete(this) }
  }
  vi.stubGlobal('BroadcastChannel', Channel)
  const receiving = new QueryClient()
  receiving.setQueryData(['map', 'viewport'], { visible_places: 16 })
  const stop = subscribeTravelChanges(receiving)
  const sending = new QueryClient()
  notifyTravelChange(sending)
  expect(receiving.getQueryState(['map', 'viewport'])?.isInvalidated).toBe(true)
  stop()
  expect(listeners.size).toBe(0)
  receiving.clear(); sending.clear()
})
