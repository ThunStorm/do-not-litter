import { expect, it } from 'vitest'
import { placeText } from './placePresentation'

it('removes source narration while preserving dates, negation and uncertainty', () => {
  expect(placeText('视频提到，从12月下旬开始几乎天天有雾凇。')).toBe('从12月下旬开始几乎天天有雾凇。')
  expect(placeText('视频不推荐正在下雪时前往，更推荐晴天。')).toBe('不推荐正在下雪时前往，更推荐晴天。')
  expect(placeText('转写称去年可能较早下雪。')).toBe('待核实：去年可能较早下雪。')
  expect(placeText('这组雾凇在视频中按冬季介绍。')).toBe('冬季观赏雾凇。')
  expect(placeText('视频未明确说明适合的时节。')).toBe('适合时节待补充。')
})
