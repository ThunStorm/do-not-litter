import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, LoaderCircle, QrCode, RefreshCw, ShieldCheck } from 'lucide-react'
import { useEffect, useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'

import { api } from '../../lib/api'

type LoginStart = Awaited<ReturnType<typeof api.startBilibiliLogin>>

export function BilibiliLoginPanel({ compact = false }: { compact?: boolean }) {
  const queryClient = useQueryClient()
  const settings = useQuery({ queryKey: ['bilibili-settings'], queryFn: api.bilibiliSettings })
  const [session, setSession] = useState<LoginStart | null>(null)
  const start = useMutation({
    mutationFn: api.startBilibiliLogin,
    onSuccess: (result) => setSession(result),
  })
  const poll = useQuery({
    queryKey: ['bilibili-login', session?.session_id],
    queryFn: () => api.pollBilibiliLogin(session!.session_id),
    enabled: Boolean(session?.session_id),
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'SUCCESS' || status === 'EXPIRED' ? false : 2000
    },
  })
  useEffect(() => {
    if (poll.data?.status !== 'SUCCESS') return
    queryClient.setQueryData(['bilibili-settings'], {
      cookie_saved: true,
      account_name: poll.data.account_name ?? null,
      verified_at: poll.data.verified_at ?? null,
    })
  }, [poll.data, queryClient])

  const loginStatus = poll.data?.status
  const busy = start.isPending
  const error = start.error || poll.error
  const accountLabel = settings.data?.cookie_saved
    ? settings.data.account_name ? `已连接 · ${settings.data.account_name}` : '已保存登录凭证'
    : '尚未登录'

  return <section className={`bilibili-login-card ${compact ? 'bilibili-login-card--compact' : ''}`}>
    <div className="bilibili-login-card__header"><div><span className={`bilibili-login-dot ${settings.data?.cookie_saved ? 'is-ready' : ''}`} /><div><h3>Bilibili 登录</h3><small>{accountLabel}</small></div></div><button className="button button--outline" type="button" onClick={() => start.mutate()} disabled={busy}>{busy ? <LoaderCircle className="spin" /> : settings.data?.cookie_saved ? <RefreshCw /> : <QrCode />}{settings.data?.cookie_saved ? '重新登录' : '扫码登录'}</button></div>
    {!session && <div className="bilibili-login-intro"><ShieldCheck /><p>使用哔哩哔哩 App 扫码确认。登录凭证由本机自动接收并写入 Keychain，不需要复制 Cookie。</p></div>}
    {session && loginStatus !== 'SUCCESS' && <div className="bilibili-qr-stage"><div className={`bilibili-qr-frame ${loginStatus === 'EXPIRED' ? 'is-expired' : ''}`}><QRCodeSVG value={session.qr_url} size={176} level="M" bgColor="#fffdf9" fgColor="#27231f" title="Bilibili 登录二维码" />{loginStatus === 'EXPIRED' && <span>已过期</span>}</div><div><strong>{loginStatus === 'WAITING_CONFIRM' ? '请在手机上确认' : loginStatus === 'EXPIRED' ? '二维码已失效' : '打开哔哩哔哩 App 扫码'}</strong><p>{poll.data?.message || '二维码约 3 分钟有效，页面会自动检查登录状态。'}</p>{loginStatus === 'EXPIRED' && <button className="button button--primary" type="button" onClick={() => start.mutate()} disabled={busy}><RefreshCw />刷新二维码</button>}</div></div>}
    {loginStatus === 'SUCCESS' && <div className="bilibili-login-success"><CheckCircle2 /><div><strong>登录成功</strong><span>{poll.data?.account_name ? `已连接 ${poll.data.account_name}` : '登录凭证已安全更新'}</span></div></div>}
    {error && <p className="form-error" role="alert">{error instanceof Error ? error.message : 'Bilibili 登录暂时不可用'}</p>}
  </section>
}
