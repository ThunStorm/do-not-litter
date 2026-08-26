import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, ChevronDown, Copy, Cpu, Database, ExternalLink, FileSearch, KeyRound, LoaderCircle, LockKeyhole, Plus, RefreshCw, Server, Trash2 } from 'lucide-react'
import { FormEvent, type ReactNode, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { PageHeader } from '../../components/AppShell'
import { api } from '../../lib/api'
import type { ModelProfileView, ModelRoutingView, PromptSupplementsView, TranscriptProcessingView } from '../../lib/types'
import { applyProviderPreset, providerPreset, providerPresets, type ManualModelFields, type ModelFormValues } from './providerPresets'

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
  const [values, setValues] = useState<Record<string, string | number>>({ app_name: '至简', default_city: '', data_retention_days: 90, ai_retry_count: 1, ai_retry_wait_seconds: 5, ai_request_interval_seconds: 3 })
  const [message, setMessage] = useState('')
  useEffect(() => { if (general.data) setValues(general.data) }, [general.data])
  const save = useMutation({ mutationFn: () => api.saveGeneralSettings(values), onSuccess: () => setMessage('设置已保存'), onError: (error) => setMessage(error.message) })
  return <><PanelTitle title="通用设置" detail="管理基础偏好、数据保留和 AI 接口访问节奏。偏好城市不影响全国地图初始视野。" /><form className="provider-form" onSubmit={(event: FormEvent) => { event.preventDefault(); save.mutate() }}><div className="field-grid"><label>产品名称<input value={String(values.app_name)} onChange={(event) => setValues((item) => ({ ...item, app_name: event.target.value }))} /></label><label>旅行偏好城市（可选）<input value={String(values.default_city)} onChange={(event) => setValues((item) => ({ ...item, default_city: event.target.value }))} /></label><label>日志保留天数<input type="number" min="7" max="3650" value={Number(values.data_retention_days)} onChange={(event) => setValues((item) => ({ ...item, data_retention_days: Number(event.target.value) }))} /></label><label>AI 异常重试次数<input type="number" min="0" max="3" value={Number(values.ai_retry_count ?? 1)} onChange={(event) => setValues((item) => ({ ...item, ai_retry_count: Number(event.target.value) }))} /></label><label>重试等待时间（秒）<input type="number" min="0" max="300" step="0.5" value={Number(values.ai_retry_wait_seconds ?? 5)} onChange={(event) => setValues((item) => ({ ...item, ai_retry_wait_seconds: Number(event.target.value) }))} /></label><label>每次 AI 调用前间隔（秒）<input type="number" min="0" max="60" step="0.1" value={Number(values.ai_request_interval_seconds ?? 3)} onChange={(event) => setValues((item) => ({ ...item, ai_request_interval_seconds: Number(event.target.value) }))} /></label></div><p className="settings-note settings-note--inset">默认在每次 AI 请求前等待 3 秒；超时、连接失败和服务端错误最多重试 1 次。遇到 429 时优先按 Retry-After 暂停该服务，避免后续分块继续消耗额度；同一服务地址的备用模型不会重复调用。</p><FormActions message={message} pending={save.isPending} /></form></>
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
  const queryClient = useQueryClient()
  const profiles = useQuery({ queryKey: ['model-profiles'], queryFn: api.modelProfiles })
  const routing = useQuery({ queryKey: ['model-routing'], queryFn: api.modelRouting })
  const [route, setRoute] = useState<Record<keyof ModelRoutingView, string>>({ primary_id: '', fallback_id: '', transcript_primary_id: '', transcript_fallback_id: '' })
  const [adding, setAdding] = useState(false)
  useEffect(() => { if (routing.data) setRoute({ primary_id: routing.data.primary_id ?? '', fallback_id: routing.data.fallback_id ?? '', transcript_primary_id: routing.data.transcript_primary_id ?? '', transcript_fallback_id: routing.data.transcript_fallback_id ?? '' }) }, [routing.data])
  const saveRoute = useMutation({ mutationFn: () => api.saveModelRouting({ primary_id: route.primary_id || null, fallback_id: route.fallback_id || null, transcript_primary_id: route.transcript_primary_id || null, transcript_fallback_id: route.transcript_fallback_id || null }), onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['model-routing'] }) })
  const selectedName = (id: string | null | undefined) => profiles.data?.find((item) => item.id === id)?.name ?? '未选择'
  const assignedIds = new Set(Object.values(routing.data ?? {}).filter(Boolean))
  const transcriptPrimary = routing.data?.transcript_primary_id || routing.data?.primary_id
  return <><PanelTitle title="AI 模型与 Provider" detail="推理路由负责通用 AI 步骤；转写校对可单独选择模型，留空时自动继承推理路由。" /><div className="provider-summary"><ProviderSummary icon={Cpu} label="推理主模型" value={selectedName(routing.data?.primary_id)} /><ProviderSummary icon={Server} label="转写校对" value={selectedName(transcriptPrimary)} /><ProviderSummary icon={Database} label="已保存模型" value={`${profiles.data?.length ?? 0} 个`} /></div><section className="provider-form"><div className="provider-form__title"><h3>模型路由</h3><button className="button button--primary" onClick={() => saveRoute.mutate()} disabled={saveRoute.isPending}>保存全部路由</button></div><div className="provider-form__body"><p className="settings-note settings-note--inset">主模型耗尽有限重试后才调用备用模型；转写专属选项优先于推理路由，未选择的项分别继承对应的推理主/备用模型。</p><div className="field-grid route-field-grid"><SelectField label="推理主模型" value={route.primary_id} onChange={(value) => setRoute((current) => ({ ...current, primary_id: value, fallback_id: value === current.fallback_id ? '' : current.fallback_id }))}><option value="">请选择已保存模型</option>{profiles.data?.map((item) => <option value={item.id} key={item.id}>{item.name} · {item.model}</option>)}</SelectField><SelectField label="推理备用模型（可选）" value={route.fallback_id} onChange={(value) => setRoute((current) => ({ ...current, fallback_id: value }))}><option value="">不使用备用模型</option>{profiles.data?.filter((item) => item.id !== route.primary_id).map((item) => <option value={item.id} key={item.id}>{item.name} · {item.model}</option>)}</SelectField><SelectField label="转写校对主模型" value={route.transcript_primary_id} onChange={(value) => setRoute((current) => ({ ...current, transcript_primary_id: value, transcript_fallback_id: value === current.transcript_fallback_id ? '' : current.transcript_fallback_id }))}><option value="">跟随推理主模型</option>{profiles.data?.map((item) => <option value={item.id} key={item.id}>{item.name} · {item.model}</option>)}</SelectField><SelectField label="转写校对备用模型" value={route.transcript_fallback_id} onChange={(value) => setRoute((current) => ({ ...current, transcript_fallback_id: value }))}><option value="">跟随推理备用模型</option>{profiles.data?.filter((item) => item.id !== route.transcript_primary_id).map((item) => <option value={item.id} key={item.id}>{item.name} · {item.model}</option>)}</SelectField></div></div></section><TranscriptProcessingPanel /><PromptSupplementsPanel /><div className="provider-form__title model-library-title"><h3>已保存模型</h3><button className="button button--outline" onClick={() => setAdding(true)}><Plus />新增自定义模型</button></div>{adding && <ModelProfileEditor onClose={() => setAdding(false)} />}{profiles.data?.map((profile) => <ModelProfileEditor key={profile.id} profile={profile} assigned={assignedIds.has(profile.id)} />)}{profiles.data?.length === 0 && !adding && <p className="settings-note">尚未保存模型。新增后才能选择主模型或备用模型。</p>}</>
}

function TranscriptProcessingPanel() {
  const processing = useQuery({ queryKey: ['transcript-processing'], queryFn: api.transcriptProcessing })
  const [values, setValues] = useState<TranscriptProcessingView>({ chunk_chars: 12_000, batch_size: 128, timeout_seconds: 180 })
  const [message, setMessage] = useState('')
  useEffect(() => { if (processing.data) setValues(processing.data) }, [processing.data])
  const save = useMutation({ mutationFn: () => api.saveTranscriptProcessing(values), onSuccess: (data) => { setValues(data); setMessage('转写参数已保存') }, onError: (error) => setMessage(error.message) })
  const update = (key: keyof TranscriptProcessingView, value: number) => setValues((current) => ({ ...current, [key]: value }))
  return <form className="provider-form transcript-processing" onSubmit={(event: FormEvent) => { event.preventDefault(); save.mutate() }}><div className="provider-form__title"><div><h3>转写分段参数</h3><small>缺省值已经过当前样本的稳定性与额度平衡验证</small></div></div><div className="field-grid field-grid--three"><label>每批字符预算<input type="number" min="2000" max="24000" step="500" value={values.chunk_chars} onChange={(event) => update('chunk_chars', Number(event.target.value))} /><small>2,000–24,000，默认 12,000</small></label><label>每批最多 Segment<input type="number" min="16" max="256" step="8" value={values.batch_size} onChange={(event) => update('batch_size', Number(event.target.value))} /><small>16–256，默认 128</small></label><label>单次超时（秒）<input type="number" min="30" max="300" step="10" value={values.timeout_seconds} onChange={(event) => update('timeout_seconds', Number(event.target.value))} /><small>30–300，默认 180</small></label></div><p className="settings-note settings-note--inset">增大批次可减少固定 Prompt 与 Schema 的重复开销；过大可能增加响应截断风险。建议优先保留默认值。</p><FormActions message={message} pending={save.isPending} /></form>
}

const promptRoles: Array<{ key: keyof Pick<PromptSupplementsView, 'transcript_correction' | 'video_note_summary' | 'travel_place_extraction'>; label: string; placeholder: string }> = [
  { key: 'transcript_correction', label: '转写校对', placeholder: '例如：优先使用自然、简洁的中文；保留作者口语风格。' },
  { key: 'video_note_summary', label: '视频笔记', placeholder: '例如：面向首次到访者；摘要更精炼，突出行程建议与风险。' },
  { key: 'travel_place_extraction', label: '地点提取', placeholder: '例如：优先关注餐馆、街区和可实际导航的细粒度地点。' },
]

function PromptSupplementsPanel() {
  const queryClient = useQueryClient()
  const supplements = useQuery({ queryKey: ['prompt-supplements'], queryFn: api.promptSupplements })
  const [values, setValues] = useState({ transcript_correction: '', video_note_summary: '', travel_place_extraction: '' })
  const [message, setMessage] = useState('')
  useEffect(() => { if (supplements.data) setValues({ transcript_correction: supplements.data.transcript_correction, video_note_summary: supplements.data.video_note_summary, travel_place_extraction: supplements.data.travel_place_extraction }) }, [supplements.data])
  const save = useMutation({ mutationFn: () => api.savePromptSupplements(values), onSuccess: () => { setMessage('补充提示词已保存'); void queryClient.invalidateQueries({ queryKey: ['prompt-supplements'] }) }, onError: (error) => setMessage(error.message) })
  const maxLength = supplements.data?.max_length ?? 1000
  return <section className="provider-form prompt-supplements"><div className="provider-form__title"><div><h3>提示词补充</h3><small>仅影响后续新的 AI 调用</small></div><div className="provider-form__actions">{message && <span className="provider-message"><CheckCircle2 />{message}</span>}<button className="button button--primary" onClick={() => save.mutate()} disabled={save.isPending}>{save.isPending && <LoaderCircle className="spin" />}保存补充提示词</button></div></div><div className="provider-form__body"><p className="settings-note settings-note--inset">核心 JSON、字段、ID、顺序与 Schema 契约由系统锁定；这里只补充语气、篇幅、受众和关注重点。越权内容会被服务端拒绝。</p><div className="prompt-supplement-list">{promptRoles.map((role) => <section className="prompt-supplement-card" key={role.key}><div className="prompt-supplement-card__meta"><div><h4>{role.label}</h4><span><LockKeyhole />核心契约已锁定</span></div><ol>{(supplements.data?.core_contracts[role.key] ?? ['核心输出契约由系统维护，不可编辑。']).map((item) => <li key={item}>{item}</li>)}</ol></div><label>可编辑补充提示词<textarea maxLength={maxLength} value={values[role.key]} onChange={(event) => setValues((current) => ({ ...current, [role.key]: event.target.value }))} placeholder={role.placeholder} /><span className="prompt-character-count">{values[role.key].length} / {maxLength}</span></label><button className="button button--outline prompt-clear" type="button" onClick={() => setValues((current) => ({ ...current, [role.key]: '' }))}>清空补充</button></section>)}</div></div></section>
}

function RuntimePanel() {
  const status = useQuery({ queryKey: ['status'], queryFn: api.status, refetchInterval: 10000 })
  return <><PanelTitle title="语音、视频与 OCR" detail="以下状态来自当前 Mac mini 的真实二进制、模型文件和服务连通检测。" /><section className="runtime-list">{status.data?.runtime_checks.map((check) => <div className="runtime-row" key={check.name}><span className={`runtime-dot runtime-dot--${check.status.toLowerCase()}`} /><div><strong>{check.name}</strong><small>{check.detail}</small>{check.path && <code>{check.path}</code>}</div><em>{runtimeLabel(check.status)}</em></div>)}</section><p className="settings-note">音视频上传会先由 FFmpeg 提取 16 kHz 单声道音频，再交给本机 Whisper.cpp；图片由 macOS Vision OCR 处理。</p></>
}

function BrowserPanel() { return <><PanelTitle title="网页解析" detail="链接解析器保留原始来源，无法可靠读取时会明确进入需确认状态。" /><section className="settings-facts"><div><span>普通网页</span><strong>HTTP 抓取</strong><small>保留 URL、响应内容与哈希</small></div><div><span>微信文章</span><strong>按页面可访问性处理</strong><small>支持正文与文内链接继续投递</small></div><div><span>Bilibili</span><strong>媒体转写链路</strong><small>上传媒体可直接经 Whisper.cpp 转写</small></div></section><Link className="settings-link" to="/sources"><FileSearch />查看真实来源与快照 <ExternalLink /></Link></> }
function MapPanel() {
  const client = useQueryClient()
  const settings = useQuery({ queryKey: ['amap-settings'], queryFn: api.amapSettings })
  const [values, setValues] = useState({ js_key: '', security_code: '', web_service_key: '' })
  const [message, setMessage] = useState('')
  useEffect(() => { if (settings.data) setValues((current) => ({ ...current, js_key: settings.data.js_key })) }, [settings.data])
  const save = useMutation({ mutationFn: () => api.saveAmapSettings(values), onSuccess: () => { setMessage('高德配置已保存'); setValues((current) => ({ ...current, security_code: '', web_service_key: '' })); void client.invalidateQueries({ queryKey: ['amap-settings'] }) }, onError: (error) => setMessage(error.message) })
  const test = useMutation({ mutationFn: api.testAmapSettings, onSuccess: (result) => setMessage(result.message), onError: (error) => setMessage(error.message) })
  return <><PanelTitle title="地图与地点" detail="首次显示中国大陆全境；随后恢复你的上次视野。高德 Web 服务用于地点校名，坐标统一 GCJ-02。" /><section className="provider-form"><div className="provider-form__title"><h3>高德地图运行配置</h3><div className="provider-form__actions">{message && <span className="provider-message"><CheckCircle2 />{message}</span>}<button className="button button--outline" onClick={() => test.mutate()} disabled={test.isPending}>真实测试</button><button className="button button--primary" onClick={() => save.mutate()} disabled={save.isPending}>保存</button></div></div><div className="field-grid"><label className="field-grid__wide">JS API Key<input value={values.js_key} onChange={(event) => setValues((current) => ({ ...current, js_key: event.target.value }))} placeholder="浏览器地图加载使用" /></label><label>Security Code<div className="masked-key"><KeyRound /><input type="password" value={values.security_code} onChange={(event) => setValues((current) => ({ ...current, security_code: event.target.value }))} placeholder={settings.data?.security_code_saved ? '已保存，留空不修改' : '保存至 Keychain'} /></div></label><label>Web 服务 Key<div className="masked-key"><KeyRound /><input type="password" value={values.web_service_key} onChange={(event) => setValues((current) => ({ ...current, web_service_key: event.target.value }))} placeholder={settings.data?.web_service_key_saved ? '已保存，留空不修改' : '用于 POI 搜索与校名'} /></div></label></div><p className="settings-note settings-note--inset">请在高德控制台为局域网访问配置域名/IP 白名单。JS Key 可提供给已认证地图页；Security Code 与 Web 服务 Key 不会返回前端。</p></section><Link className="button button--primary settings-map-link" to="/map">打开中国大陆地图</Link></> }

function PanelTitle({ title, detail }: { title: string; detail: string }) { return <section className="settings-title"><div><h2>{title}</h2><p>{detail}</p></div></section> }
function FormActions({ message, pending }: { message: string; pending: boolean }) { return <div className="settings-form-actions">{message && <span><CheckCircle2 />{message}</span>}<button className="button button--primary" disabled={pending}>{pending && <LoaderCircle className="spin" />}保存</button></div> }

function ModelProfileEditor({ profile, assigned = false, onClose }: { profile?: ModelProfileView; assigned?: boolean; onClose?: () => void }) {
  const queryClient = useQueryClient()
  const [values, setValues] = useState<ModelFormValues>({ name: profile?.name ?? '', provider: profile?.provider ?? '', base_url: profile?.base_url ?? '', model: profile?.model ?? '', timeout_seconds: profile?.timeout_seconds ?? 300, api_key: '' })
  const [presetId, setPresetId] = useState(providerPreset(profile?.provider ?? '')?.id ?? 'CUSTOM')
  const [message, setMessage] = useState('')
  const [manual, setManual] = useState<ManualModelFields>(() => ({ model: Boolean(profile && !providerPreset(profile.provider)?.models.some((model) => model === profile.model)), baseUrl: Boolean(profile && providerPreset(profile.provider)?.baseUrl !== profile.base_url) }))
  useEffect(() => { if (profile) { const preset = providerPreset(profile.provider); setValues({ name: profile.name, provider: profile.provider, base_url: profile.base_url, model: profile.model, timeout_seconds: profile.timeout_seconds, api_key: '' }); setPresetId(preset?.id ?? 'CUSTOM'); setManual({ model: !preset?.models.some((model) => model === profile.model), baseUrl: preset?.baseUrl !== profile.base_url }) } }, [profile])
  const saved = () => { void queryClient.invalidateQueries({ queryKey: ['model-profiles'] }); void queryClient.invalidateQueries({ queryKey: ['model-routing'] }); setMessage('配置已保存'); setValues((value) => ({ ...value, api_key: '' })); onClose?.() }
  const save = useMutation({ mutationFn: () => profile ? api.updateModelProfile(profile.id, values) : api.createModelProfile(values), onSuccess: saved, onError: (error) => setMessage(error.message) })
  const test = useMutation({ mutationFn: () => profile ? api.testModelProfile(profile.id) : api.testModelProfileDraft(values), onSuccess: (result) => setMessage(result.message), onError: (error) => setMessage(error.message) })
  const remove = useMutation({ mutationFn: () => api.deleteModelProfile(profile!.id), onSuccess: () => { void queryClient.invalidateQueries({ queryKey: ['model-profiles'] }); setMessage('已删除') }, onError: (error) => setMessage(error.message) })
  const update = (key: keyof typeof values, value: string | number) => setValues((current) => ({ ...current, [key]: value }))
  const choosePreset = (id: string) => {
    setPresetId(id)
    setValues((current) => applyProviderPreset(current, id, manual))
  }
  const activePreset = providerPreset(values.provider)
  const isLocal = activePreset?.id === 'OLLAMA'
  const busy = save.isPending || test.isPending || remove.isPending
  const modelOptionsId = `model-options-${profile?.id ?? 'draft'}`
  return <section className="provider-form"><div className="provider-form__title"><h3>{profile ? profile.name : '新增自定义模型'}{assigned && <small>当前路由使用中</small>}</h3><div className="provider-form__actions">{message && <span className="provider-message"><CheckCircle2 />{message}</span>}<button className="button button--outline" onClick={() => test.mutate()} disabled={busy}>真实测试</button>{profile && <button className="button button--outline" onClick={() => { if (window.confirm(`删除“${profile.name}”吗？该操作不会删除 Keychain 之外的其他模型。`)) remove.mutate() }} disabled={busy || assigned}><Trash2 />删除</button>}<button className="button button--primary" onClick={() => save.mutate()} disabled={busy}>{busy && <LoaderCircle className="spin" />}保存</button></div></div><div className="field-grid"><label>显示名称<input value={values.name} onChange={(event) => update('name', event.target.value)} placeholder="例如：我的 DeepSeek" /></label><SelectField label="Provider" value={presetId} onChange={choosePreset}>{providerPresets.map((item) => <option value={item.id} key={item.id}>{item.label}</option>)}<option value="CUSTOM">自定义</option></SelectField>{presetId === 'CUSTOM' && <label>自定义 Provider<input value={values.provider} onChange={(event) => update('provider', event.target.value)} placeholder="例如：任意 OpenAI 兼容服务" /></label>}<label>模型名<input list={modelOptionsId} value={values.model} onChange={(event) => { setManual((current) => ({ ...current, model: true })); update('model', event.target.value) }} placeholder="可输入或选择模型名" /><datalist id={modelOptionsId}>{activePreset?.models.map((model) => <option key={model} value={model} />)}</datalist></label><label>超时（秒）<input type="number" min="5" max="900" value={values.timeout_seconds} onChange={(event) => update('timeout_seconds', Number(event.target.value))} /></label>{!isLocal && <label className="field-grid__wide">Base URL<input value={values.base_url} onChange={(event) => { setManual((current) => ({ ...current, baseUrl: true })); update('base_url', event.target.value) }} placeholder="https://api.example.com/v1" /></label>}{isLocal ? <p className="provider-local-note">本机运行，不需要 API Key；默认连接本机 Ollama。</p> : <label className="field-grid__wide">API Key（留空沿用 Keychain）<div className="masked-key"><KeyRound /><input type="password" value={values.api_key} onChange={(event) => update('api_key', event.target.value)} placeholder={profile?.api_key_saved ? '已保存，留空不修改' : '真实测试前需要填写'} /></div></label>}</div></section>
}

function SelectField({ label, value, onChange, children }: { label: string; value: string; onChange: (value: string) => void; children: ReactNode }) { return <label>{label}<span className="select-control"><select value={value} onChange={(event) => onChange(event.target.value)}>{children}</select><ChevronDown /></span></label> }
function ProviderSummary({ icon: Icon, label, value }: { icon: typeof Cpu; label: string; value: string }) { return <div><Icon /><span>{label}</span><strong>{value}</strong><small>按真实接口测试</small></div> }
function runtimeLabel(status: string) { return ({ READY: '已就绪', MISSING: '未安装', DEGRADED: '缺少组件', UNAVAILABLE: '服务离线' } as Record<string, string>)[status] ?? status }
