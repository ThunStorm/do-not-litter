export const providerPresets = [
  { id: 'DEEPSEEK', label: 'DeepSeek', provider: 'DeepSeek', baseUrl: 'https://api.deepseek.com/v1', models: ['deepseek-chat', 'deepseek-reasoner'] },
  { id: 'MIMO', label: 'MiMo', provider: 'MiMo', baseUrl: 'https://api.xiaomimimo.com/v1', models: ['mimo-v2-flash', 'mimo-v2-pro'] },
  { id: 'MOONSHOT', label: 'Moonshot / Kimi', provider: 'Moonshot', baseUrl: 'https://api.moonshot.cn/v1', models: ['kimi-k2.6', 'kimi-k2.5'] },
  { id: 'ZHIPU', label: '智谱 GLM', provider: 'Zhipu', baseUrl: 'https://open.bigmodel.cn/api/paas/v4', models: ['glm-5-turbo', 'glm-5', 'glm-4.7'] },
  { id: 'QWEN', label: '通义千问', provider: 'Qwen', baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1', models: ['qwen-plus', 'qwen-max'] },
  { id: 'OPENAI', label: 'OpenAI 兼容', provider: 'OpenAI Compatible', baseUrl: '', models: ['gpt-4.1-mini', 'gpt-4.1'] },
  { id: 'OLLAMA', label: 'Ollama（本地）', provider: 'Ollama', baseUrl: 'http://127.0.0.1:11434', models: ['qwen2.5:7b'] },
] as const

export type ModelFormValues = {
  name: string; provider: string; base_url: string; model: string; timeout_seconds: number; request_interval_seconds: number | null; api_key: string
  location?: 'LOCAL' | 'REMOTE'; modalities?: string[]; capabilities?: string[]; supports_json_mode?: boolean; supports_thinking?: boolean; quality_tier?: 'FAST' | 'MAIN' | 'STRONG' | 'SPECIALIST'
}
export type ManualModelFields = { model: boolean; baseUrl: boolean }

export function providerPreset(provider: string) { return providerPresets.find((item) => item.provider.toLowerCase() === provider.trim().toLowerCase()) }

export function applyProviderPreset(values: ModelFormValues, presetId: string, manual: ManualModelFields): ModelFormValues {
  const preset = providerPresets.find((item) => item.id === presetId)
  if (!preset) return values
  return { ...values, provider: preset.provider, base_url: manual.baseUrl ? values.base_url : preset.baseUrl, model: manual.model ? values.model : preset.models[0] }
}
