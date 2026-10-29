import type { AIUsageView } from '../../lib/types'
import { stepLabel } from './taskTimeline'

const labels: Record<string, string> = {
  DIRECT_VALID: '直接解析', NORMALIZED_VALID: '格式规范化', DETERMINISTIC_REPAIRED: '规则修复',
  MODEL_REPAIRED: '模型修复', INVALID: '无效结果', INCOMPLETE: '输出不完整',
  PRIMARY_DIRECT: '主模型', PRIMARY_RETRY: '重试', FALLBACK: '备用模型', CACHE_HIT: '缓存',
  QUEUED: '等待本地资源', DISPATCHED: '模型执行中', VALIDATING: '校验结果中',
  GROUND_MAP: '证据地图', NOTE_REDUCE: '笔记归纳', TRANSCRIPT_CORRECTION: '转写校对',
  COVER_TEXT: '封面文字识别',
  GENERATE_AI_NOTE: '生成笔记', EXTRACT_TRAVEL_FACTS: '提取旅行事实',
}

export function AICallDetails({ calls }: { calls: AIUsageView['call_details'] }) {
  if (!calls?.length) return null
  return <details className="ai-call-details"><summary>调用明细（最近 {calls.length} 条）</summary>
    <ul>{calls.map((call) => <li key={call.id}>
      <strong>{labels[call.stage] ?? stepLabel(call.stage)} · {labels[call.execution_path ?? ''] ?? '历史调用'}</strong>
      <span>{call.model}</span>
      <span>{call.status === 'RUNNING' ? labels[call.attempt_state ?? ''] ?? '正在等待或调用模型' : call.error_code ? '调用失败' : labels[call.parse_quality ?? ''] ?? '解析质量未记录'} · {call.duration_ms == null ? '耗时未记录' : `${(call.duration_ms / 1000).toFixed(1)} 秒`}</span>
      <span>{call.usage_source === 'REPORTED' ? '模型上报用量' : '用量未知，估算另列'}{call.queue_ms != null ? ` · 等待 ${(call.queue_ms / 1000).toFixed(1)} 秒` : ''}{call.provider_ms != null ? ` · 模型 ${(call.provider_ms / 1000).toFixed(1)} 秒` : ''}</span>
      {Boolean(call.rejected_items) && <span>部分接受：{call.rejected_items} 项证据无效</span>}
    </li>)}</ul>
  </details>
}
