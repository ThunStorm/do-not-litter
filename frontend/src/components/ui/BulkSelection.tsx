import { Trash2, X } from 'lucide-react'

export function BulkSelectionToolbar({ label, visibleCount, selectedCount, allSelected, pending = false, onToggleAll, onClear, onDelete }: {
  label: string
  visibleCount: number
  selectedCount: number
  allSelected: boolean
  pending?: boolean
  onToggleAll: () => void
  onClear: () => void
  onDelete: () => void
}) {
  return <div className="bulk-selection-toolbar">
    <label title={`全选当前 ${visibleCount} 条${label}`}><input type="checkbox" checked={allSelected} onChange={onToggleAll} aria-label={`全选当前${label}`} /><span>{selectedCount > 0 ? `已选 ${selectedCount}/${visibleCount}` : '全选'}</span></label>
    {selectedCount > 0 && <><button className="button button--outline bulk-selection-clear" onClick={onClear} disabled={pending} aria-label={`清除已选${label}`}><X /></button><button className="button button--danger" onClick={onDelete} disabled={pending}><Trash2 />删除 {selectedCount}</button></>}
  </div>
}
