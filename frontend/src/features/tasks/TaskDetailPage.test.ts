import { describe, expect, it } from 'vitest'

import { formatStepDuration, isTimelineCurrent, replayActionState, stepLabel } from './taskTimeline'

describe('task timeline presentation', () => {
  it('uses Chinese labels for screenshot steps', () => {
    expect(stepLabel('CORRECT_TRANSCRIPT')).toBe('AI 校对转写')
    expect(stepLabel('PLAN_SCREENSHOTS')).toBe('规划关键截图')
    expect(stepLabel('DOWNLOAD_VIDEO_FOR_FRAMES')).toBe('下载截图所需视频')
    expect(stepLabel('EXTRACT_SCREENSHOTS')).toBe('提取关键截图')
  })

  it('only highlights the running current step', () => {
    expect(isTimelineCurrent('RUNNING', 'CLEAN_CACHE', 'CLEAN_CACHE', 'RUNNING')).toBe(true)
    expect(isTimelineCurrent('COMPLETED', 'CLEAN_CACHE', 'CLEAN_CACHE', 'COMPLETED')).toBe(false)
  })

  it('formats completed step duration', () => {
    expect(formatStepDuration('2026-08-24T08:00:00Z', '2026-08-24T08:02:35Z')).toBe('用时 2 分 35 秒')
  })

  it('enables full replay after a cancelled task releases its lease', () => {
    expect(replayActionState('CANCELLED', null, false, false)).toEqual({ label: '正在停止当前步骤', enabled: false })
    expect(replayActionState('CANCELLED', null, false, true)).toEqual({ label: '从头重新运行', enabled: true })
  })
})
