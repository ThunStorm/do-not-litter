import type { ButtonHTMLAttributes, ReactNode } from 'react'

type IconButtonProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'> & {
  children: ReactNode
  label: string
}

export function IconButton({ children, className = '', label, ...props }: IconButtonProps) {
  return <button className={`ui-icon-button ${className}`.trim()} aria-label={label} title={label} {...props}>{children}</button>
}
