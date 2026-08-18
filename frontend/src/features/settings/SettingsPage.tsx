import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, Copy, Cpu, Database, ExternalLink, FileSearch, KeyRound, LoaderCircle, RefreshCw, Server } from 'lucide-react'
import { FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { PageHeader } from '../../components/AppShell'
import { api } from '../../lib/api'

type ProviderValues = Record<string, string>
type Tab = 'general' | 'lan' | 'models' | 'runtime' | 'browser' | 'map'
const tabs: Array<{ id: Tab; label: string }> = [{ id: 'general', label: '通用' }, { id: 'lan', label: '局域网访问' }, { id: 'models', label: 'AI 模型' }, { id: 'runtime', label: '语音与 OCR' }, { id: 'browser', label: '网页解析' }, { id: 'map', label: '地图与地点' }]

export function SettingsPage() {
  const [tab, setTab] = useState<Tab>('general')
  const status = useQuery({ queryKey: ['status'], queryFn: api.status, refetchInterval: 15000 })
  return <div className="settings-page page-frame"><PageHeader title="设置" /><div className="settings-layout"><nav className="settings-nav" aria-label="设置分类">{tabs.map((item) => <button key={item.id} className={tab === item.id ? 'is-active' : ''} onClick={() => setTab(item.id)}>{item.label}</button>)}</nav><div className="settings-main">
    {tab === 'general' && <GeneralPanel />}{tab === 'lan' && <LanPanel />}{tab === 'models' && <ModelsPanel />}{tab === 'runtime' && <RuntimePanel />}{tab === 'browser' && <BrowserPanel />}{tab === 'map' && <MapPanel />}
  </div></div><section className="node-footer"><strong>当前节点</strong><span>{status.data ? `${status.data.hardware.machine_name} · ${status.data.hardware.chip} · ${status.data.hardware.memory}` : '正在读取真实设备信息'}</span></section></div>
}

function GeneralPanel() {
  const general = useQuery({ queryKey: ['general-settings'], queryFn: api.generalSettings })
  const [values, setValues] = useState<Record<string, string | number>>({ app_name: '至简', default_city: '厦门市', data_retention_days: 90 })
  const [message, setMessage] = useState('')
  useEffect(() => { if (general.data) setValues(general.data) }, [general.data])
  const save = useMutation({ mutationFn: () => api.saveGeneralSettings(values), onSuccess: () => setMessage('设置已保存'), onError: (error) => setMessage(error.message) })
  return <><PanelTitle title="通用设置" detail="管理产品名称、默认城市和本地数据保留周期。" /><form className="provider-form" onSubmit={(event: FormEvent) => { event.preventDefault(); save.mutate() }}><div className="field-grid"><label>产品名称<input value={String(values.app_name)} onChange={(event) => setValues((item) => ({ ...item, app_name: event.target.value }))} /></label><label>地图默认城市<input value={String(values.default_city)} onChange={(event) => setValues((item) => ({ ...item, default_city: event.target.value }))} /></label><label>日志保留天数<input type="number" min="7" max="3650" value={Number(values.data_retention_days)} onChange={(event) => setValues((item) => ({ ...item, data_retention_days: Number(event.target.value) }))} /></label></div><FormActions message={message} pending={save.isPending} /></form></>
}

function LanPanel() {
  const client = useQueryClient()
  const token = useQuery({ queryKey: ['lan-token'], queryFn: api.lanToken })
  const status = useQuery({ queryKey: ['status'], queryFn: api.status })
  const [copied, setCopied] = useState('')
  const rotate = useMutation({ mutationFn: api.rotateLanToken, onSuccess: () => void client.invalidateQueries({ queryKey: ['lan-token'] }) })
  const copy = async (value: string, label: string) => { await navigator.clipboard.writeText(value); setCopied(label); window.setTimeout(() => setCopied(''), 1400) }
  return <><PanelTitle title="局域网访问" detail="手机与 Mac mini 连接同一 Wi-Fi 后，用 4 位码建立可信会话。" /><section className="lan-settings-card"><span>当前配对码</span><output>{token.data?.display ?? '••••'}</output><p>4 位码只用于可信局域网首次配对，连续失败会被限流锁定。</p><div><button className="button button--outline" onClick={() => token.data && void copy(token.data.token, 'token')}><Copy />{copied === 'token' ? '已复制' : '复制配对码'}</button><button className="button button--primary" onClick={() => rotate.mutate()} disabled={rotate.isPending}><RefreshCw className={rotate.isPending ? 'spin' : ''} />轮换并撤销会话</button></div></section><section className="settings-facts"><div><span>手机访问地址</span><strong>{status.data?.lan_url ?? '检测中'}</strong><button onClick={() => status.data && void copy(status.data.lan_url, 'url')}>{copied === 'url' ? '已复制' : '复制'}</button></div><div><span>会话有效期</span><strong>7 天</strong><small>轮换配对码会立即撤销已有会话</small></div><div><span>网络边界</span><strong>仅局域网</strong><small>未配置公网端口与自动转发</small></div></section></>
}

function ModelsPanel() {
  const providers = useQuery({ queryKey: ['providers'], queryFn: api.providers })
  return <><PanelTitle title="AI 模型与 Provider" detail="本地优先；DeepSeek、MiMo 等 OpenAI 兼容接口使用 Keychain 保存密钥。" /><div className="provider-summary"><ProviderSummary icon={Cpu} label="默认模型" value={providers.data?.default?.provider ?? '读取中'} /><ProviderSummary icon={Server} label="后备模型" value={providers.data?.fallback?.provider ?? '读取中'} /><ProviderSummary icon={Database} label="本地模型" value={providers.data?.local?.provider ?? '读取中'} /></div>{providers.data && Object.entries(providers.data).map(([role, provider]) => <ProviderEditor key={role} role={role} initial={provider} />)}</>
}

function RuntimePanel() {
  const status = useQuery({ queryKey: ['status'], queryFn: api.status, refetchInterval: 10000 })
  return <><PanelTitle title="语音、视频与 OCR" detail="以下状态来自当前 Mac mini 的真实二进制、模型文件和服务连通检测。" /><section className="runtime-list">{status.data?.runtime_checks.map((check) => <div className="runtime-row" key={check.name}><span className={`runtime-dot runtime-dot--${check.status.toLowerCase()}`} /><div><strong>{check.name}</strong><small>{check.detail}</small>{check.path && <code>{check.path}</code>}</div><em>{runtimeLabel(check.status)}</em></div>)}</section><p className="settings-note">音视频上传会先由 FFmpeg 提取 16 kHz 单声道音频，再交给本机 Whisper.cpp；图片由 macOS Vision OCR 处理。</p></>
}

function BrowserPanel() { return <><PanelTitle title="网页解析" detail="链接解析器保留原始来源，无法可靠读取时会明确进入需确认状态。" /><section className="settings-facts"><div><span>普通网页</span><strong>HTTP 抓取</strong><small>保留 URL、响应内容与哈希</small></div><div><span>微信文章</span><strong>按页面可访问性处理</strong><small>支持正文与文内链接继续投递</small></div><div><span>Bilibili</span><strong>媒体转写链路</strong><small>上传媒体可直接经 Whisper.cpp 转写</small></div></section><Link className="settings-link" to="/sources"><FileSearch />查看真实来源与快照 <ExternalLink /></Link></> }
function MapPanel() { return <><PanelTitle title="地图与地点" detail="中国范围默认使用 GCJ-02 坐标与高德 POI；地图标记先总览分布，再逐点打开介绍。" /><section className="settings-facts"><div><span>坐标体系</span><strong>GCJ-02</strong><small>中国大陆地图展示标准</small></div><div><span>POI Provider</span><strong>高德地图</strong><small>API Key 通过服务环境配置</small></div><div><span>路线策略</span><strong>人工排序</strong><small>不伪造距离与交通时间</small></div></section><Link className="button button--primary settings-map-link" to="/map">打开地图总览</Link></> }

function PanelTitle({ title, detail }: { title: string; detail: string }) { return <section className="settings-title"><div><h2>{title}</h2><p>{detail}</p></div></section> }
function FormActions({ message, pending }: { message: string; pending: boolean }) { return <div className="settings-form-actions">{message && <span><CheckCircle2 />{message}</span>}<button className="button button--primary" disabled={pending}>{pending && <LoaderCircle className="spin" />}保存</button></div> }

function ProviderEditor({ role, initial }: { role: string; initial: ProviderValues }) {
  const queryClient = useQueryClient(); const [values, setValues] = useState<ProviderValues>(initial); const [message, setMessage] = useState(''); useEffect(() => setValues(initial), [initial])
  const save = useMutation({ mutationFn: () => api.saveProvider(role, values), onSuccess: () => { setMessage('配置已保存'); setValues((current) => ({ ...current, api_key: '' })); void queryClient.invalidateQueries({ queryKey: ['providers'] }) }, onError: (error) => setMessage(error.message) })
  const test = useMutation({ mutationFn: () => api.testProvider(role, values), onSuccess: (result) => setMessage(result.message), onError: (error) => setMessage(error.message) })
  const update = (key: string, value: string) => setValues((current) => ({ ...current, [key]: value })); const busy = save.isPending || test.isPending
  return <section className="provider-form"><div className="provider-form__title"><h3>{roleLabel(role)}</h3><div className="provider-form__actions">{message && <span className="provider-message"><CheckCircle2 />{message}</span>}<button className="button button--outline" onClick={() => test.mutate()} disabled={busy}>真实测试</button><button className="button button--primary" onClick={() => save.mutate()} disabled={busy}>{busy && <LoaderCircle className="spin" />}保存</button></div></div><div className="field-grid"><label>Provider<input value={values.provider ?? ''} onChange={(event) => update('provider', event.target.value)} /></label><label>模型名<input value={values.model ?? ''} onChange={(event) => update('model', event.target.value)} /></label><label className="field-grid__wide">Base URL<input value={values.base_url ?? ''} onChange={(event) => update('base_url', event.target.value)} /></label><label>API Key（留空沿用 Keychain）<div className="masked-key"><KeyRound /><input type="password" value={values.api_key ?? ''} onChange={(event) => update('api_key', event.target.value)} placeholder="未修改" /></div></label></div></section>
}
function ProviderSummary({ icon: Icon, label, value }: { icon: typeof Cpu; label: string; value: string }) { return <div><Icon /><span>{label}</span><strong>{value}</strong><small>按真实接口测试</small></div> }
function roleLabel(role: string) { return ({ default: '1. 默认推理模型', fallback: '2. 后备模型', local: '3. 本地模型' } as Record<string, string>)[role] ?? role }
function runtimeLabel(status: string) { return ({ READY: '已就绪', MISSING: '未安装', DEGRADED: '缺少组件', UNAVAILABLE: '服务离线' } as Record<string, string>)[status] ?? status }
