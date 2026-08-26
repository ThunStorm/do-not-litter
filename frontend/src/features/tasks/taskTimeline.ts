const STEP_LABELS: Record<string, string> = {
  RECEIVED: '已接收',
  NORMALIZE_CAPTURE_INPUT: '识别粘贴内容',
  RESOLVE: '解析来源',
  SEGMENT: '文本分段',
  EXTRACT: '提取信息',
  VALIDATE_LINK: '校验链接',
  FETCH_METADATA: '获取元信息',
  FETCH_SUBTITLE: '获取字幕',
  DOWNLOAD_AUDIO: '下载音频',
  ASR: '语音识别',
  NORMALIZE_TRANSCRIPT: '归一化字幕',
  CORRECT_TRANSCRIPT: 'AI 校对转写',
  GENERATE_AI_NOTE: '生成 AI 笔记',
  EXTRACT_TRAVEL_FACTS: '提取地点',
  RESOLVE_POI: '解析地点',
  BUILD_PLACE_NOTES: '生成地点笔记',
  PLAN_SCREENSHOTS: '规划关键截图',
  DOWNLOAD_VIDEO_FOR_FRAMES: '下载截图所需视频',
  EXTRACT_SCREENSHOTS: '提取关键截图',
  MATERIALIZE: '生成结果',
  CLEAN_CACHE: '清理缓存',
}

export function stepLabel(step: string) { return STEP_LABELS[step] ?? step }

export function isTimelineCurrent(jobStatus: string, currentStep: string, stepName: string, stepStatus: string) {
  return jobStatus === 'RUNNING' && stepStatus === 'RUNNING' && stepName === currentStep
}

export function replayActionState(
  jobStatus: string,
  replayFromStep: string | null,
  stepReplayAvailable: boolean,
  fullReplayAvailable: boolean,
) {
  if (stepReplayAvailable && replayFromStep) {
    return { label: `从“${stepLabel(replayFromStep)}”继续`, enabled: true }
  }
  if (jobStatus === 'CANCELLED' && !fullReplayAvailable) {
    return { label: '正在停止当前步骤', enabled: false }
  }
  return { label: '从头重新运行', enabled: fullReplayAvailable }
}

export function formatStepDuration(startedAt: string | null, finishedAt: string | null) {
  if (!startedAt) return '尚未开始'
  const milliseconds = Math.max(0, (finishedAt ? new Date(finishedAt).getTime() : Date.now()) - new Date(startedAt).getTime())
  const seconds = Math.floor(milliseconds / 1000)
  if (seconds < 1) return '用时 <1 秒'
  if (seconds < 60) return `用时 ${seconds} 秒`
  if (seconds < 3600) return `用时 ${Math.floor(seconds / 60)} 分 ${seconds % 60} 秒`
  return `用时 ${Math.floor(seconds / 3600)} 小时 ${Math.floor(seconds % 3600 / 60)} 分`
}
