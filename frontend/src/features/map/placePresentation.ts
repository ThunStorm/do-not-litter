/** Presentation only: keep qualifiers, negation, numbers and the underlying source records. */
export function placeText(value: string | undefined) {
  const text = (value ?? '').trim()
  if (!text) return ''
  const shared = text.match(/^这组(.+?)在视频中按(.+?)介绍[。.]?$/)
  if (shared) return shared[1] === '景观' ? `${shared[2]}。` : `${shared[2]}观赏${shared[1]}。`
  if (/^视频未明确说明适合的时节/.test(text)) return '适合时节待补充。'
  if (/^视频未提及季节限制/.test(text)) return '暂未记录季节限制。'
  return text
    .replace(/^视频介绍的是/, '')
    .replace(/^视频介绍(?=春|夏|秋|冬)/, '')
    .replace(/^视频推荐/, '推荐')
    .replace(/^视频(?:提到|指出|强调|提醒)[，,:：\s]*/, '')
    .replace(/^视频(?=不推荐|不建议)/, '')
    .replace(/^转写称[，,:：\s]*/, '待核实：')
}
