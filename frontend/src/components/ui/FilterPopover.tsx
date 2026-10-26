import { ChevronDown, X } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { createPortal } from 'react-dom'

export function FilterPopover({ label, active = false, children, listbox = false }: { label: string; active?: boolean; children: ReactNode | ((close: () => void) => ReactNode); listbox?: boolean }) {
  const [open, setOpen] = useState(false)
  const [position, setPosition] = useState({ top: 0, left: 0 })
  const trigger = useRef<HTMLButtonElement>(null)
  const panel = useRef<HTMLDivElement>(null)
  const id = useId()
  const close = () => { setOpen(false); trigger.current?.focus() }
  useEffect(() => {
    if (!open) return
    const dismiss = (event: PointerEvent) => { if (!panel.current?.contains(event.target as Node) && !trigger.current?.contains(event.target as Node)) setOpen(false) }
    const other = (event: Event) => { if ((event as CustomEvent<string>).detail !== id) setOpen(false) }
    const positionPanel = () => {
      const rect = trigger.current?.getBoundingClientRect()
      if (!rect) return
      const height = Math.min(panel.current?.offsetHeight || 320, window.innerHeight - 32)
      setPosition({ left: Math.max(12, Math.min(rect.left, window.innerWidth - (panel.current?.offsetWidth || 300) - 12)), top: rect.bottom + height + 8 > window.innerHeight ? Math.max(12, rect.top - height - 6) : rect.bottom + 6 })
    }
    positionPanel()
    panel.current?.querySelector<HTMLElement>('[aria-selected="true"], button, input')?.focus()
    document.addEventListener('pointerdown', dismiss)
    window.addEventListener('filter-popover-open', other)
    window.addEventListener('resize', positionPanel)
    window.addEventListener('scroll', positionPanel, true)
    return () => {
      document.removeEventListener('pointerdown', dismiss)
      window.removeEventListener('filter-popover-open', other)
      window.removeEventListener('resize', positionPanel)
      window.removeEventListener('scroll', positionPanel, true)
    }
  }, [id, open])
  return <div className="filter-menu"><button ref={trigger} type="button" className={`filter-chip${active ? ' is-active' : ''}`} aria-haspopup={listbox ? 'listbox' : 'dialog'} aria-controls={id} aria-expanded={open} onClick={() => { if (!open) window.dispatchEvent(new CustomEvent('filter-popover-open', { detail: id })); setOpen(!open) }} onKeyDown={(event) => { if (event.key === 'ArrowDown' || event.key === 'ArrowUp') { event.preventDefault(); window.dispatchEvent(new CustomEvent('filter-popover-open', { detail: id })); setOpen(true) } }}><span>{label}</span><ChevronDown /></button>{open && createPortal(<><div className="filter-popover__scrim" onClick={close} /><div ref={panel} className={`filter-popover${listbox ? ' filter-popover--options' : ''}`} role="dialog" aria-label={label} style={position} onKeyDown={(event) => {
    if (event.key === 'Escape') { event.stopPropagation(); close() }
    if (event.key === 'Tab') {
      const controls = Array.from(panel.current?.querySelectorAll<HTMLElement>('button:not(:disabled), input, a[href]') ?? [])
      if (event.shiftKey && document.activeElement === controls[0]) { event.preventDefault(); controls.at(-1)?.focus() }
      if (!event.shiftKey && document.activeElement === controls.at(-1)) { event.preventDefault(); controls[0]?.focus() }
    }
  }}><header><strong>{label}</strong><button type="button" className="icon-button" aria-label={`关闭${label}`} onClick={close}><X /></button></header><div id={id}>{typeof children === 'function' ? children(close) : children}</div></div></>, document.body)}</div>
}
