import { useEffect, useRef, type ReactNode } from 'react'

export function ConfirmDialog({ title, description, confirmLabel, danger = false, pending = false, error, children, onCancel, onConfirm }: { title: string; description: string; confirmLabel: string; danger?: boolean; pending?: boolean; error?: string; children?: ReactNode; onCancel: () => void; onConfirm: () => void }) {
  const cancel = useRef<HTMLButtonElement>(null)
  useEffect(() => { cancel.current?.focus() }, [])
  return <div className="dialog-scrim" role="presentation" onMouseDown={onCancel}><section className="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="confirm-dialog-title" onMouseDown={(event) => event.stopPropagation()}><h2 id="confirm-dialog-title">{title}</h2><p>{description}</p>{children}{error && <p className="form-error" role="alert">{error}</p>}<footer><button ref={cancel} className="button button--outline" onClick={onCancel} disabled={pending}>取消</button><button className={`button ${danger ? 'button--danger' : 'button--primary'}`} onClick={onConfirm} disabled={pending}>{pending ? '处理中…' : confirmLabel}</button></footer></section></div>
}
