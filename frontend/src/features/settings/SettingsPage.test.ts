import { describe, expect, it } from 'vitest'

import { applyProviderPreset } from './providerPresets'

const moonshot = {
  name: '草稿',
  provider: 'Moonshot',
  base_url: 'https://api.moonshot.cn/v1',
  model: 'kimi-k2.6',
  timeout_seconds: 300,
  request_interval_seconds: null,
  api_key: '',
}

describe('applyProviderPreset', () => {
  it('replaces the previous Provider defaults', () => {
    expect(applyProviderPreset(moonshot, 'ZHIPU', { model: false, baseUrl: false })).toMatchObject({
      provider: 'Zhipu',
      base_url: 'https://open.bigmodel.cn/api/paas/v4',
      model: 'glm-5-turbo',
    })
  })

  it('keeps only fields explicitly edited by the user', () => {
    expect(applyProviderPreset({ ...moonshot, model: '我的模型' }, 'ZHIPU', { model: true, baseUrl: false })).toMatchObject({
      provider: 'Zhipu',
      base_url: 'https://open.bigmodel.cn/api/paas/v4',
      model: '我的模型',
    })
  })
})
