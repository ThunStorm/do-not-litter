import { ArrowRight, LockKeyhole } from 'lucide-react'
import { FormEvent, type ReactNode, useEffect, useState } from 'react'

import { api } from '../lib/api'
import { Brand } from './Brand'

type GateState = 'checking' | 'login' | 'ready' | 'unavailable'
const STATUS_TIMEOUT_MS = 8_000

export function SessionGate({ children }: { children: ReactNode }) {
  const [state, setState] = useState<GateState>('checking')
  const [token, setToken] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function checkSession() {
    setState('checking')
    const controller = new AbortController()
    const timeout = window.setTimeout(() => controller.abort(), STATUS_TIMEOUT_MS)
    try {
      const response = await fetch('/api/status', { credentials: 'include', cache: 'no-store', signal: controller.signal })
      setState(response.ok ? 'ready' : response.status === 401 || response.status === 403 ? 'login' : 'unavailable')
    } catch {
      setState('unavailable')
    } finally {
      window.clearTimeout(timeout)
    }
  }

  useEffect(() => {
    void checkSession()
  }, [])

  async function submit(event: FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      await api.createSession(token.trim())
      setToken('')
      setState('ready')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : '配对失败')
    } finally {
      setSubmitting(false)
    }
  }

  if (state === 'ready') return children
  if (state === 'checking') return <div className="session-checking"><Brand /><span>正在连接 Mac mini…</span></div>
  if (state === 'unavailable') return <main className="session-page"><section className="session-card"><Brand /><div className="session-card__icon"><LockKeyhole /></div><p className="detail-context">Mac mini 暂时无法响应</p><h1>正在保留本次配对</h1><p>已配对设备不需要重新输入 4 位码。请确认 Mac mini 服务仍在运行，随后重试连接。</p><button className="button button--primary" onClick={() => void checkSession()}>重新连接</button><small>只有服务明确返回“会话已失效”时，才需要重新配对。</small></section></main>
  return (
    <main className="session-page">
      <section className="session-card">
        <Brand />
        <div className="session-card__icon"><LockKeyhole /></div>
        <p className="detail-context">可信局域网配对</p>
        <h1>连接你的 Mac mini</h1>
        <p>输入后端初始化时生成的访问 Token。配对完成后仅保存 HttpOnly 会话，不在浏览器中留存原始 Token。</p>
        <form onSubmit={submit}>
          <label htmlFor="lan-token">输入 Mac mini 上显示的 4 位配对码</label>
          <div><input id="lan-token" type="text" inputMode="numeric" autoComplete="one-time-code" value={token} onChange={(event) => setToken(event.target.value.replace(/\D/g, '').slice(0, 4))} placeholder="0000" minLength={4} maxLength={4} pattern="\d{4}" required /><button aria-label="连接" disabled={submitting || token.length !== 4}><ArrowRight /></button></div>
        </form>
        {error && <span className="form-error">{error}</span>}
        <small>只应在可信家庭或办公局域网使用，不要将端口暴露到公网。</small>
      </section>
    </main>
  )
}
