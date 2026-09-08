import { describe, expect, it } from 'vitest'

import { visitWindowLabel } from './placeLabels'

describe('visitWindowLabel', () => {
  it('shows recommended viewing time with calendar detail', () => {
    expect(visitWindowLabel({ period_type: 'BEST_VIEWING', suitability: 'RECOMMENDED', month: 10, month_segment: 'MID' })).toBe('推荐 · 最佳观赏期 · 10月中旬')
  })

  it('distinguishes restrictive seasonal periods', () => {
    expect(visitWindowLabel({ period_type: 'FISHING_CLOSURE', suitability: 'RESTRICTED' })).toBe('限制 · 渔业时段')
  })
})
