import { Check, ChevronDown } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'

type Option = { label: string; value: string }
type SelectMenuProps = {
  disabled?: boolean
  label: string
  onChange: (value: string) => void
  options: Option[]
  value: string
}

export function SelectMenu({ disabled = false, label, onChange, options, value }: SelectMenuProps) {
  const [open, setOpen] = useState(false)
  const trigger = useRef<HTMLButtonElement>(null)
  const listId = useId()
  const selected = options.find((option) => option.value === value) ?? options[0]
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
    const index = Math.max(0, options.findIndex((option) => option.value === value))
    choose(options[(index + direction + options.length) % options.length].value)
  }

  return <div className="ui-select-menu"><span>{label}</span><button ref={trigger} type="button" disabled={disabled} aria-haspopup="listbox" aria-controls={listId} aria-expanded={open} onClick={() => setOpen((current) => !current)} onKeyDown={(event) => { if (event.key === 'ArrowDown') { event.preventDefault(); move(1) } if (event.key === 'ArrowUp') { event.preventDefault(); move(-1) } if (event.key === 'Home') { event.preventDefault(); choose(options[0].value) } if (event.key === 'End') { event.preventDefault(); choose(options.at(-1)?.value ?? value) } }}><span>{selected?.label ?? label}</span><ChevronDown /></button>{open && <div id={listId} role="listbox" aria-label={label}>{options.map((option) => <button key={option.value} type="button" role="option" aria-selected={option.value === value} onClick={() => choose(option.value)}>{option.value === value && <Check aria-hidden="true" />}{option.label}</button>)}</div>}</div>
}
