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
      <header className="detail-topbar"><Link to="/content"><ArrowLeft />返回内容</Link><span>{contentTypeLabel(item.content_type)}</span><Link aria-label="查看来源" to="/sources"><RotateCcw /></Link></header>
      <article className="detail-body">
        <p className="detail-context">结构化结果 · {item.status === 'NEEDS_USER' ? '需要确认' : '来源已保存'}</p>
        <h1>{item.title}</h1>
        <p className="detail-summary">{item.summary}</p>
        {item.content_type === 'RECRUITMENT' ? (
          <>
            <section className="deadline-block"><span>报名截止</span><strong>{String(structured.deadline ?? '待确认')}</strong><Link className="button" to="/todos">查看待办</Link></section>
            <section className="detail-section"><h2>我的条件核验</h2>{eligibility.length ? eligibility.map((rule) => <EligibilityRow key={rule.label} rule={rule} />) : <p>个人档案信息不足，暂不自动给出通过结论。</p>}</section>
          </>
        ) : item.content_type === 'VIDEO_NOTE' ? (
          <section className="detail-section"><h2><FileText />视频 AI 笔记</h2><p>已生成可回溯时间码的笔记、地点候选与 POI 确认状态。</p>{structured.note_id ? <Link className="text-action" to={`/video-notes/${String(structured.note_id)}`}>打开视频笔记</Link> : <p>笔记入口正在生成，请从视频笔记列表打开或稍后刷新。</p>}</section>
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
  return <div className="eligibility-row">{safe ? <CheckCircle2 /> : <CircleHelp />}<strong>{rule.label}</strong><span>{rule.value}</span><em className={`eligibility-${rule.status?.toLowerCase()}`}>{eligibilityLabel(rule.status)}</em></div>
}

function contentTypeLabel(type: string) { return ({ RECRUITMENT: '招聘详情', TRAVEL: '旅行详情', VIDEO_NOTE: '视频笔记', UNSUPPORTED: '来源详情' } as Record<string, string>)[type] ?? '内容详情' }
function eligibilityLabel(status: string) { return ({ PASS: '符合', UNKNOWN: '待确认', FAIL: '不符合' } as Record<string, string>)[status] ?? status }
