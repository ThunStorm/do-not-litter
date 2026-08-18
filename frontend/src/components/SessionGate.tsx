import { ArrowRight, LockKeyhole } from 'lucide-react'
import { FormEvent, type ReactNode, useEffect, useState } from 'react'

import { api } from '../lib/api'
import { Brand } from './Brand'

type GateState = 'checking' | 'login' | 'ready'

export function SessionGate({ children }: { children: ReactNode }) {
  const [state, setState] = useState<GateState>('checking')
  const [token, setToken] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    const controller = new AbortController()
    fetch('/api/status', { credentials: 'include', signal: controller.signal })
      .then((response) => setState(response.ok ? 'ready' : 'login'))
      .catch(() => setState('login'))
    return () => controller.abort()
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
