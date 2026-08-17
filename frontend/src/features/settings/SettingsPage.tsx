import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, Cpu, Database, KeyRound, LoaderCircle, Server } from 'lucide-react'
import { useEffect, useState } from 'react'

import { PageHeader } from '../../components/AppShell'
import { api } from '../../lib/api'

type ProviderValues = Record<string, string>

export function SettingsPage() {
  const providers = useQuery({ queryKey: ['providers'], queryFn: api.providers })
  const status = useQuery({ queryKey: ['status'], queryFn: api.status })

  return (
    <div className="settings-page page-frame">
      <PageHeader title="设置" />
      <div className="settings-layout">
        <nav className="settings-nav">
          <button>通用</button><button>局域网访问</button><button className="is-active">AI 模型</button>
          <button>语音与 OCR</button><button>浏览器</button><button>地图与地点</button>
        </nav>
        <div className="settings-main">
          <section className="settings-title"><div><h2>AI 模型与 Provider</h2><p>本地优先，外部模型只在策略允许时使用；密钥不进入数据库。</p></div></section>
          <div className="provider-summary">
            <ProviderSummary icon={Cpu} label="默认模型" value={providers.data?.default?.provider ?? 'DeepSeek'} />
            <ProviderSummary icon={Server} label="后备模型" value={providers.data?.fallback?.provider ?? 'MiMo'} />
            <ProviderSummary icon={Database} label="本地模型" value={providers.data?.local?.provider ?? 'Ollama Metal'} />
          </div>
          {providers.data && Object.entries(providers.data).map(([role, provider]) => (
            <ProviderEditor key={role} role={role} initial={provider} />
          ))}
        </div>
      </div>
      <section className="node-footer"><strong>当前节点</strong><span>{String(status.data?.node_name ?? 'Mac mini')} · {String(status.data?.architecture ?? 'arm64')}</span></section>
    </div>
  )
}

function ProviderEditor({ role, initial }: { role: string; initial: ProviderValues }) {
  const queryClient = useQueryClient()
  const [values, setValues] = useState<ProviderValues>(initial)
  const [message, setMessage] = useState('')
  useEffect(() => setValues(initial), [initial])

  const save = useMutation({
    mutationFn: () => api.saveProvider(role, values),
    onSuccess: () => {
      setMessage('配置已保存')
      setValues((current) => ({ ...current, api_key: '' }))
      void queryClient.invalidateQueries({ queryKey: ['providers'] })
    },
    onError: (error) => setMessage(error.message),
  })
  const test = useMutation({
    mutationFn: () => api.testProvider(role, values),
    onSuccess: (result) => setMessage(result.message),
    onError: (error) => setMessage(error.message),
  })
  const update = (key: string, value: string) => setValues((current) => ({ ...current, [key]: value }))
  const busy = save.isPending || test.isPending

  return (
    <section className="provider-form">
      <div className="provider-form__title">
        <h3>{roleLabel(role)}</h3>
        <div className="provider-form__actions">
          {message && <span className="provider-message"><CheckCircle2 />{message}</span>}
          <button className="button button--outline" onClick={() => test.mutate()} disabled={busy}>测试</button>
          <button className="button button--primary" onClick={() => save.mutate()} disabled={busy}>{busy && <LoaderCircle className="spin" />}保存</button>
        </div>
      </div>
      <div className="field-grid">
        <label>Provider<input value={values.provider ?? ''} onChange={(event) => update('provider', event.target.value)} /></label>
        <label>模型名<input value={values.model ?? ''} onChange={(event) => update('model', event.target.value)} /></label>
        <label className="field-grid__wide">Base URL<input value={values.base_url ?? ''} onChange={(event) => update('base_url', event.target.value)} /></label>
        <label>API Key（留空则沿用 Keychain）<div className="masked-key"><KeyRound /><input type="password" value={values.api_key ?? ''} onChange={(event) => update('api_key', event.target.value)} placeholder="未修改" /></div></label>
      </div>
    </section>
  )
}

function ProviderSummary({ icon: Icon, label, value }: { icon: typeof Cpu; label: string; value: string }) {
  return <div><Icon /><span>{label}</span><strong>{value}</strong><small><i className="status-dot" />已配置</small></div>
}

function roleLabel(role: string) {
  return ({ default: '1. 默认推理模型', fallback: '2. 后备模型', local: '3. 本地模型' } as Record<string, string>)[role] ?? role
}
