import { Check } from 'lucide-react'

import { FilterPopover } from './FilterPopover'

export function FilterMenu({ label, value, options, onChange }: { label: string; value: string; options: Array<{ value: string; label: string }>; onChange: (value: string) => void }) {
  const current = options.find((option) => option.value === value)?.label
  return <FilterPopover label={value ? `${label} · ${current}` : label} active={!!value} listbox>{(close) => <div className="filter-menu__options" role="listbox" aria-label={label} onKeyDown={(event) => {
    const items = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>('[role="option"]'))
    const index = items.indexOf(document.activeElement as HTMLButtonElement)
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? items.length - 1 : event.key === 'ArrowDown' ? (index + 1) % items.length : event.key === 'ArrowUp' ? (index - 1 + items.length) % items.length : -1
    if (next >= 0) { event.preventDefault(); items[next]?.focus() }
  }}>{options.map((option) => <button key={option.value} type="button" role="option" aria-selected={option.value === value} onClick={() => { onChange(option.value); close() }}>{option.value === value && <Check aria-hidden="true" />}{option.label}</button>)}</div>}</FilterPopover>
}
