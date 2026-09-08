import { Check, ChevronDown } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

export function FilterMenu({ label, value, options, onChange }: { label: string; value: string; options: Array<{ value: string; label: string }>; onChange: (value: string) => void }) {
  const [open, setOpen] = useState(false)
  const trigger = useRef<HTMLButtonElement>(null)
  useEffect(() => { const close = (event: KeyboardEvent) => { if (event.key === 'Escape') { setOpen(false); trigger.current?.focus() } }; window.addEventListener('keydown', close); return () => window.removeEventListener('keydown', close) }, [])
  const current = options.find((option) => option.value === value)?.label
  return <div className="filter-menu"><button ref={trigger} className={`filter-chip${value ? ' is-active' : ''}`} aria-haspopup="listbox" aria-expanded={open} onClick={() => setOpen((item) => !item)}>{value ? `${label} · ${current}` : label}<ChevronDown /></button>{open && <div className="filter-menu__list" role="listbox">{options.map((option) => <button key={option.value} role="option" aria-selected={option.value === value} onClick={() => { onChange(option.value); setOpen(false); trigger.current?.focus() }}>{option.value === value && <Check />}{option.label}</button>)}</div>}</div>
}
