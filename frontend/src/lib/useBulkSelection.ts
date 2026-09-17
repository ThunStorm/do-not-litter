import { useEffect, useMemo, useState } from 'react'

export function useBulkSelection(ids: string[]) {
  const idsKey = ids.join('|')
  const itemIds = useMemo(() => idsKey ? idsKey.split('|') : [], [idsKey])
  const [selected, setSelected] = useState<Set<string>>(() => new Set())
  useEffect(() => {
    setSelected((current) => {
      const allowed = new Set(itemIds)
      const next = new Set([...current].filter((id) => allowed.has(id)))
      return next.size === current.size ? current : next
    })
  }, [itemIds])
  const selectedIds = useMemo(() => itemIds.filter((id) => selected.has(id)), [itemIds, selected])
  const allSelected = itemIds.length > 0 && selectedIds.length === itemIds.length
  return {
    selectedIds,
    allSelected,
    isSelected: (id: string) => selected.has(id),
    toggle: (id: string) => setSelected((current) => {
      const next = new Set(current)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    }),
    toggleAll: () => setSelected(allSelected ? new Set() : new Set(itemIds)),
    clear: () => setSelected(new Set()),
  }
}
