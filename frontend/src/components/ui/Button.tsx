import type { ButtonHTMLAttributes, ReactNode } from 'react'

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode
  loading?: boolean
  variant?: 'primary' | 'outline' | 'danger'
}

export function Button({ children, className = '', loading = false, variant = 'primary', disabled, ...props }: ButtonProps) {
  return <button className={`ui-button ui-button--${variant} ${className}`.trim()} disabled={disabled || loading} {...props}>{loading ? '处理中…' : children}</button>
}
