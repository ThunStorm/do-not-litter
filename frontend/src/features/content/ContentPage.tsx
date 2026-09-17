import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BriefcaseBusiness, ChevronRight, FileQuestion, Filter, Luggage, Map, Search } from 'lucide-react'
import { useDeferredValue, useState } from 'react'
import { Link } from 'react-router-dom'

import { EmptyState, PageHeader } from '../../components/AppShell'
import { BulkSelectionToolbar } from '../../components/ui/BulkSelection'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { api } from '../../lib/api'
import { useBulkSelection } from '../../lib/useBulkSelection'
import type { ContentType } from '../../lib/types'

const filters: Array<{ label: string; value?: ContentType }> = [
  { label: '全部' },
  { label: '招聘', value: 'RECRUITMENT' },
  { label: '旅行', value: 'TRAVEL' },
]

export function ContentPage() {
  const [activeType, setActiveType] = useState<ContentType | undefined>()
  const [query, setQuery] = useState('')
  const [needsReviewOnly, setNeedsReviewOnly] = useState(false)
  const deferredQuery = useDeferredValue(query)
  const contents = useQuery({
    queryKey: ['content', activeType, deferredQuery],
    queryFn: () => api.content(activeType, deferredQuery),
  })
  const visibleContents = needsReviewOnly ? contents.data?.filter((item) => item.status === 'NEEDS_USER') : contents.data
  const queryClient = useQueryClient()
  const [deleteOpen, setDeleteOpen] = useState(false)
  const selection = useBulkSelection((visibleContents ?? []).map((item) => item.id))
  const remove = useMutation({ mutationFn: () => api.deleteContents(selection.selectedIds), onSuccess: () => { selection.clear(); setDeleteOpen(false); void queryClient.invalidateQueries({ queryKey: ['content'] }); void queryClient.invalidateQueries({ queryKey: ['dashboard'] }); void queryClient.invalidateQueries({ queryKey: ['todos'] }); void queryClient.invalidateQueries({ queryKey: ['sources'] }) } })

  const typeMeta = (contentType: ContentType) => {
    if (contentType === 'RECRUITMENT') return { icon: <BriefcaseBusiness />, label: '招聘' }
    if (contentType === 'TRAVEL') return { icon: <Luggage />, label: '旅行' }
    return { icon: <FileQuestion />, label: '未支持' }
  }

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
        <button className={`content-tabs__filter ${needsReviewOnly ? 'is-active' : ''}`} aria-pressed={needsReviewOnly} onClick={() => setNeedsReviewOnly((value) => !value)}><Filter size={18} />{needsReviewOnly ? '只看待确认' : '筛选'}</button>
      </div>
      {activeType !== 'RECRUITMENT' && (
        <Link className="map-entry" to="/map">
          <div><Map size={24} strokeWidth={1.5} /><span><strong>地图总览</strong><small>查看地点分布并建立路线清单</small></span></div>
          <ChevronRight size={20} />
        </Link>
      )}
      <section className="content-list-section">
        <div className="section-title"><div className="bulk-heading-title"><h2>{needsReviewOnly ? '需要确认' : '最近更新'}</h2><span>{visibleContents?.length ?? 0}</span></div><BulkSelectionToolbar label="内容" visibleCount={visibleContents?.length ?? 0} selectedCount={selection.selectedIds.length} allSelected={selection.allSelected} pending={remove.isPending} onToggleAll={selection.toggleAll} onClear={selection.clear} onDelete={() => setDeleteOpen(true)} /></div>
        <div className="mobile-content-list">
          {visibleContents?.length ? visibleContents.map((item) => (
            <div key={item.id} className="mobile-content-item selectable-row"><label className="bulk-row-checkbox"><input type="checkbox" checked={selection.isSelected(item.id)} onChange={() => selection.toggle(item.id)} aria-label={`选择内容 ${item.title}`} /></label><Link className="mobile-content-row mobile-content-row--selectable" to={`/content/${item.id}`}>
              {typeMeta(item.content_type).icon}
              <div><strong>{item.title}</strong><span>{typeMeta(item.content_type).label} · {item.status === 'NEEDS_USER' ? '需确认' : '已完成'}</span></div>
              <ChevronRight />
            </Link></div>
          )) : <EmptyState title="没有符合条件的内容" detail="调整分类或投递新的链接" />}
        </div>
      </section>
      {deleteOpen && <ConfirmDialog title="删除内容" description={`将删除 ${selection.selectedIds.length} 条内容及其专属事实/证据；孤立来源会一并清理，地点和路线保留。`} confirmLabel={`删除 ${selection.selectedIds.length} 条内容`} danger pending={remove.isPending} error={remove.error instanceof Error ? remove.error.message : ''} onCancel={() => setDeleteOpen(false)} onConfirm={() => remove.mutate()} />}
    </div>
  )
}
