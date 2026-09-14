import { Search } from 'lucide-react'
import type { InputHTMLAttributes } from 'react'

type SearchFieldProps = Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> & { label: string }

export function SearchField({ className = '', label, ...props }: SearchFieldProps) {
  return <label className={`ui-search-field ${className}`.trim()}><Search aria-hidden="true" /><span className="sr-only">{label}</span><input type="search" aria-label={label} {...props} /></label>
}
