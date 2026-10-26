import type { AIStagePolicy } from '../../lib/types'

export function editablePolicy(policy: AIStagePolicy): AIStagePolicy {
  const values = { ...policy }
  for (const field of ['temperature', 'retry_count', 'json_retry_count'] as const) {
    if (policy.sources?.[field] === 'system_default') values[field] = null
  }
  delete values.sources
  return values
}
