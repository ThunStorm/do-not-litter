import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, CheckCircle2, CircleHelp, FileText, MapPin, RotateCcw } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'

import { api } from '../../lib/api'

export function ContentDetailPage() {
  const { contentId = '' } = useParams()
  const detail = useQuery({ queryKey: ['content-detail', contentId], queryFn: () => api.contentDetail(contentId) })
  const item = detail.data
  if (!item) return <div className="detail-loading">正在读取结构化内容…</div>
  const structured = item.structured as Record<string, unknown>
  const eligibility = Array.isArray(structured.eligibility) ? structured.eligibility as Array<Record<string, string>> : []
  return (
    <div className="detail-page">
      <header className="detail-topbar"><Link to="/content"><ArrowLeft />返回内容</Link><span>{item.content_type === 'RECRUITMENT' ? '招聘详情' : '旅行详情'}</span><button aria-label="重新处理"><RotateCcw /></button></header>
      <article className="detail-body">
        <p className="detail-context">结构化结果 · {item.status === 'NEEDS_USER' ? '需要确认' : '来源已保存'}</p>
        <h1>{item.title}</h1>
        <p className="detail-summary">{item.summary}</p>
        {item.content_type === 'RECRUITMENT' ? (
          <>
            <section className="deadline-block"><span>报名截止</span><strong>{String(structured.deadline ?? '待确认')}</strong><button>添加提醒</button></section>
            <section className="detail-section"><h2>我的条件核验</h2>{eligibility.length ? eligibility.map((rule) => <EligibilityRow key={rule.label} rule={rule} />) : <p>个人档案信息不足，暂不自动给出通过结论。</p>}</section>
          </>
        ) : (
          <section className="detail-section"><h2><MapPin />地点与观察</h2><p>地点信息将在高德 POI 确认后进入独立地图总览。</p><Link className="text-action" to="/map">前往地图总览</Link></section>
        )}
        <section className="detail-section"><h2><FileText />依据</h2><p>每条结构化结论均绑定 Segment 与原始定位；未绑定 Evidence 的事实不会自动发布。</p></section>
      </article>
    </div>
  )
}

function EligibilityRow({ rule }: { rule: Record<string, string> }) {
  const safe = rule.status === 'PASS'
  return <div className="eligibility-row">{safe ? <CheckCircle2 /> : <CircleHelp />}<strong>{rule.label}</strong><span>{rule.value}</span><em className={`eligibility-${rule.status?.toLowerCase()}`}>{rule.status}</em></div>
}
