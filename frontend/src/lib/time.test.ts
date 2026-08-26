import { describe, expect, it } from 'vitest'

import { formatBeijingTime } from './time'

describe('formatBeijingTime', () => {
  it('does not follow the browser timezone', () => {
    expect(formatBeijingTime('2026-08-22T07:00:20Z')).toContain('15:00:20')
  })
})
