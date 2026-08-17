import { useQuery } from '@tanstack/react-query'
import { BriefcaseBusiness, ChevronRight, Filter, Luggage, Map, Search } from 'lucide-react'
import { useDeferredValue, useState } from 'react'
import { Link } from 'react-router-dom'

import { EmptyState, PageHeader } from '../../components/AppShell'
import { api } from '../../lib/api'
import type { ContentType } from '../../lib/types'

const filters: Array<{ label: string; value?: ContentType }> = [
  { label: '全部' },
  { label: '招聘', value: 'RECRUITMENT' },
  { label: '旅行', value: 'TRAVEL' },
]

export function ContentPage() {
  const [activeType, setActiveType] = useState<ContentType | undefined>()
  const [query, setQuery] = useState('')
  const deferredQuery = useDeferredValue(query)
  const contents = useQuery({
    queryKey: ['content', activeType, deferredQuery],
    queryFn: () => api.content(activeType, deferredQuery),
  })

  return (
    <div className="content-page page-frame">
      <PageHeader title="内容" actions={<Link className="icon-button" to="/map" aria-label="地图总览"><Map /></Link>} />
      <div className="search-field">
        <Search size={21} strokeWidth={1.5} />
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索标题、地点或来源" />
      </div>
      <div className="content-tabs" role="tablist" aria-label="内容分类">
        {filters.map((item) => (
          <button
            key={item.label}
            role="tab"
            aria-selected={activeType === item.value}
            className={activeType === item.value ? 'is-active' : ''}
            onClick={() => setActiveType(item.value)}
          >
            {item.label}
          </button>
        ))}
        <button className="content-tabs__filter"><Filter size={18} />筛选</button>
      </div>
      {activeType !== 'RECRUITMENT' && (
        <Link className="map-entry" to="/map">
          <div><Map size={24} strokeWidth={1.5} /><span><strong>地图总览</strong><small>查看地点分布并建立路线清单</small></span></div>
          <ChevronRight size={20} />
        </Link>
      )}
      <section className="content-list-section">
        <div className="section-title"><h2>最近更新</h2><span>{contents.data?.length ?? 0}</span></div>
        <div className="mobile-content-list">
          {contents.data?.length ? contents.data.map((item) => (
            <Link key={item.id} className="mobile-content-row" to={`/content/${item.id}`}>
              {item.content_type === 'RECRUITMENT' ? <BriefcaseBusiness /> : <Luggage />}
              <div><strong>{item.title}</strong><span>{item.content_type === 'RECRUITMENT' ? '招聘' : '旅行'} · {item.status === 'NEEDS_USER' ? '需确认' : '已完成'}</span></div>
              <ChevronRight />
            </Link>
          )) : <EmptyState title="没有符合条件的内容" detail="调整分类或投递新的链接" />}
        </div>
      </section>
    </div>
  )
}
