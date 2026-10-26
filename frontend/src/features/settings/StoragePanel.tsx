import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Button } from '../../components/ui/Button'
import { TextField } from '../../components/ui/TextField'
import { api } from '../../lib/api'
import type { LogPolicy, LogPreview, StorageStatus } from '../../lib/types'

const fields: Array<{ key: keyof LogPolicy; label: string; min: number }> = [
  { key: 'retention_days', label: '运行日志总保留天数', min: 1 },
  { key: 'compression_delay_hours', label: '封卷后压缩延迟（小时）', min: 1 },
  { key: 'volume_bytes', label: '单卷上限（字节）', min: 65536 },
  { key: 'capacity_bytes', label: '运行日志归档容量上限（字节）', min: 1048576 },
  { key: 'bootstrap_retention_days', label: '启动与标准输出总保留天数', min: 1 },
  { key: 'bootstrap_capacity_bytes', label: '启动与标准输出归档上限（字节）', min: 1048576 },
  { key: 'low_space_bytes', label: '可用磁盘空间告警阈值（字节）', min: 0 },
]
const bytes = (n: number) => `${(n / 1024 / 1024).toFixed(1)} MiB`

export function StoragePanel() {
  const client = useQueryClient()
  const status = useQuery({ queryKey: ['storage'], queryFn: api.storageStatus, refetchInterval: 5000 })
  const [path, setPath] = useState('')
  const [draft, setDraft] = useState<LogPolicy | null>(null)
  const [impact, setImpact] = useState<LogPreview | null>(null)
  const plan = useMutation({ mutationFn: () => api.storagePlan(path), onSuccess: (result) => { client.setQueryData<StorageStatus>(['storage'], (old) => old ? { ...old, plan: { stage: result.stage } } : old); return client.invalidateQueries({ queryKey: ['storage'] }) } })
  const policy = draft || status.data?.policy
  const preview = useMutation({ mutationFn: () => api.logPolicyPreview(policy!), onSuccess: setImpact })
  const apply = useMutation({ mutationFn: () => api.logPolicyApply(policy!, impact!.token), onSuccess: () => { setImpact(null); setDraft(null); client.invalidateQueries({ queryKey: ['storage'] }) } })
  if (status.error) return <p role="alert">{status.error.message}</p>
  if (!status.data || !policy) return <p>正在读取存储配置…</p>
  const data = status.data
  return <div className="storage-settings">
    <section className="panel"><div className="panel__heading"><h2>存储与日志</h2></div>
      <p>目录位于运行服务的 Mac。保存方案不会切换运行中的数据库；原目录及备份不会自动删除。</p>
      <dl className="storage-settings__facts"><dt>当前生效目录</dt><dd>{data.root}</dd><dt>配置代次 / 当前加载</dt><dd>{data.configured_generation} / {data.generation}</dd><dt>最近维护</dt><dd>{data.state.stage || '无搬迁操作'}</dd></dl>
      <form onSubmit={(event) => { event.preventDefault(); plan.mutate() }}><TextField label="拟切换的服务器目录" value={path} onChange={(event) => setPath(event.target.value)} placeholder="例如 /Volumes/数据盘/至简资料" required /><Button variant="outline" loading={plan.isPending} disabled={!path || !data.registered || data.plan.stage === 'SCANNING'}>预检并保存待应用方案</Button></form>
      {!data.registered && <p role="status">当前为旧安装，需在本机登记现有实例后才能保存搬迁方案。</p>}
      {plan.error && <p role="alert">{plan.error.message}</p>}
      {data.plan.stage && <div role="status"><p>方案：{({ SCANNING: '后台清点中', PLANNED: '预检完成，待本机维护窗口应用', FAILED: '预检失败' } as Record<string, string>)[data.plan.stage] || data.plan.stage}</p>{data.plan.error && <p>{data.plan.error}</p>}{data.plan.required_bytes != null && <p>预计需要 {bytes(data.plan.required_bytes)}；可用 {bytes(data.plan.free_bytes || 0)}。</p>}{data.plan.categories && <ul>{Object.entries(data.plan.categories).map(([name, size]) => <li key={name}>{name}：{bytes(size)}</li>)}</ul>}<p>应用时会等待任务结束、短时停止服务并核验副本。请在 Mac 本机使用部署管理器的 storage-apply；本页不执行搬迁。</p></div>}
      <details><summary>不随目录自动搬迁的项目</summary><ul>{data.exceptions.map((item) => <li key={item}>{item}</li>)}</ul></details>
    </section>
    <section className="panel"><div className="panel__heading"><h2>文件日志策略</h2></div><p>只管理运行日志和启动输出。系统事件与调用审计在通用设置单独配置；转录保留180天，笔记、图片和密钥不随日志清理。</p><p>未压缩查阅窗口由压缩延迟决定，总保留期包含压缩阶段。空间上限优先，可能缩短实际窗口；扩大保留期无法找回已删日志。</p>
      <div className="settings-grid">{fields.map((field) => <TextField key={field.key} label={field.label} type="number" min={field.min} value={Number(policy[field.key])} onChange={(event) => { setDraft({ ...policy, [field.key]: Number(event.target.value) }); setImpact(null) }} />)}</div>
      <label><input type="checkbox" checked={policy.compress} onChange={(event) => { setDraft({ ...policy, compress: event.target.checked }); setImpact(null) }} /> 压缩已关闭的分卷</label>
      <p>策略版本 {data.policy.version}；当前写入器加载版本 {data.handler_versions.join('、') || '尚未采样'}。压缩延迟须小于两类日志总保留期。</p>
      <Button variant="outline" loading={preview.isPending} onClick={() => preview.mutate()}>预览清理影响</Button>
      {impact && <div role="status"><p>将清理 {impact.delete_count} 个封卷，合计 {bytes(impact.delete_bytes)}；活跃文件不参与清理。</p><Button loading={apply.isPending} disabled={data.plan.stage === 'SCANNING'} onClick={() => apply.mutate()}>应用此日志策略</Button></div>}
      {(preview.error || apply.error) && <p role="alert">{(preview.error || apply.error)?.message}</p>}{apply.data && <p role="status">{apply.data.message}</p>}
      <p>归档占用 {bytes(data.log_summary.archived_bytes)}；最早可用封卷 {data.log_summary.oldest_closed_at ? new Date(data.log_summary.oldest_closed_at * 1000).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }) : '暂无'}。</p>
      {data.maintenance.at && <p>最近文件维护：{new Date(data.maintenance.at * 1000).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })}；压缩 {data.maintenance.compressed || 0} 卷，删除 {data.maintenance.deleted || 0} 卷{data.maintenance.errors?.length ? '；存在维护错误，原文件保留' : ''}。</p>}
    </section>
  </div>
}
