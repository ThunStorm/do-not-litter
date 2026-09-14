import type { InputHTMLAttributes } from 'react'

type TextFieldProps = InputHTMLAttributes<HTMLInputElement> & { label: string }

export function TextField({ className = '', label, ...props }: TextFieldProps) {
  return <label className="ui-text-field"><span>{label}</span><input className={className} {...props} /></label>
}
