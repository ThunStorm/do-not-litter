import { expect, it } from 'vitest'
import type { AIStagePolicy } from '../../lib/types'
import { editablePolicy } from './stagePolicyForm'

it('preserves inherited model settings when saving an unrelated stage field', () => {
  const policy = { temperature: 0.1, retry_count: 0, json_retry_count: 0, sources: {
    temperature: 'system_default', retry_count: 'system_default', json_retry_count: 'system_default',
  } } as unknown as AIStagePolicy
  expect(editablePolicy(policy)).toEqual({ temperature: null, retry_count: null, json_retry_count: null })
  expect(policy.retry_count).toBe(0)
})

it('keeps explicit zero retries and explicit temperature', () => {
  const policy = { temperature: 0.1, retry_count: 0, json_retry_count: 0, sources: {
    temperature: 'saved_stage_policy', retry_count: 'saved_stage_policy', json_retry_count: 'saved_stage_policy',
  } } as unknown as AIStagePolicy
  expect(editablePolicy(policy)).toEqual({ temperature: 0.1, retry_count: 0, json_retry_count: 0 })
})
