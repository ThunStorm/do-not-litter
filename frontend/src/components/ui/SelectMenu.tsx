import { Check, ChevronDown } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'

type Option = { label: string; value: string }
type SelectMenuProps = {
  disabled?: boolean
  label: string
  onChange: (value: string) => void
  options: Option[]
  searchable?: boolean
  value: string
}

export function SelectMenu({ disabled = false, label, onChange, options, searchable = false, value }: SelectMenuProps) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const trigger = useRef<HTMLButtonElement>(null)
  const listId = useId()
  const selected = options.find((option) => option.value === value) ?? options[0]
  const visibleOptions = searchable ? options.filter((option) => `${option.label} ${option.value}`.toLowerCase().includes(search.trim().toLowerCase())) : options
  useEffect(() => {
    const close = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false)
        trigger.current?.focus()
      }
    }
    window.addEventListener('keydown', close)
    return () => window.removeEventListener('keydown', close)
  }, [])
  const choose = (next: string) => {
    onChange(next)
    setOpen(false)
    trigger.current?.focus()
  }
  const move = (direction: 1 | -1) => {
    if (!options.length) return
    const index = Math.max(0, options.findIndex((option) => option.value === value))
    choose(options[(index + direction + options.length) % options.length].value)
  }

  return <div className="ui-select-menu"><span>{label}</span><button ref={trigger} type="button" disabled={disabled} aria-haspopup="listbox" aria-controls={listId} aria-expanded={open} onClick={() => { setSearch(''); setOpen((current) => !current) }} onKeyDown={(event) => { if (event.key === 'ArrowDown') { event.preventDefault(); move(1) } if (event.key === 'ArrowUp') { event.preventDefault(); move(-1) } if (event.key === 'Home' && options.length) { event.preventDefault(); choose(options[0].value) } if (event.key === 'End') { event.preventDefault(); choose(options.at(-1)?.value ?? value) } }}><span>{selected?.label ?? label}</span><ChevronDown /></button>{open && <div className="ui-select-menu__panel">{searchable && <input className="ui-select-menu__search" aria-label={`搜索${label}`} placeholder="输入关键词搜索" value={search} onChange={(event) => setSearch(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && visibleOptions[0]) { event.preventDefault(); choose(visibleOptions[0].value) } if (event.key === 'ArrowDown') { event.preventDefault(); event.currentTarget.nextElementSibling?.querySelector<HTMLButtonElement>('button')?.focus() } }} />}<div id={listId} role="listbox" aria-label={label}>{visibleOptions.map((option) => <button key={option.value} type="button" role="option" aria-selected={option.value === value} onClick={() => choose(option.value)}>{option.value === value && <Check aria-hidden="true" />}{option.label}</button>)}</div>{visibleOptions.length === 0 && <small role="status">没有匹配项</small>}</div>}</div>
}
