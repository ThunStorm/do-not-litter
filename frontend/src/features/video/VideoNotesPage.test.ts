import { describe, expect, it } from 'vitest'

import { videoTimestampUrl } from './videoTime'

describe('videoTimestampUrl', () => {
  it('preserves existing Bilibili query parameters and adds seconds', () => {
    expect(videoTimestampUrl('https://www.bilibili.com/video/BV1abc?p=2', 49_900)).toBe(
      'https://www.bilibili.com/video/BV1abc?p=2&t=49',
    )
  })
})
