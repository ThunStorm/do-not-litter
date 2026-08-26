import type { ReactNode } from 'react'

function inline(value: string): ReactNode[] {
  return value.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g).filter(Boolean).map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) return <strong key={index}>{part.slice(2, -2)}</strong>
    if (part.startsWith('*') && part.endsWith('*')) return <em key={index}>{part.slice(1, -1)}</em>
    if (part.startsWith('`') && part.endsWith('`')) return <code key={index}>{part.slice(1, -1)}</code>
    return part
  })
}

export function MarkdownContent({ value }: { value: string }) {
  const lines = value.replace(/\r\n/g, '\n').split('\n')
  const blocks: ReactNode[] = []
  let index = 0
  while (index < lines.length) {
    const line = lines[index].trim()
    if (!line) { index += 1; continue }
    const heading = line.match(/^(#{2,3})\s+(.+)$/)
    if (heading) {
      const Tag = heading[1].length === 2 ? 'h4' : 'h5'
      blocks.push(<Tag key={index}>{inline(heading[2])}</Tag>)
      index += 1
      continue
    }
    if (/^(?:[-*+]\s+|\d+\.\s+)/.test(line)) {
      const ordered = /^\d+\.\s+/.test(line)
      const items: ReactNode[] = []
      while (index < lines.length && /^(?:[-*+]\s+|\d+\.\s+)/.test(lines[index].trim())) {
        items.push(<li key={index}>{inline(lines[index].trim().replace(/^(?:[-*+]\s+|\d+\.\s+)/, ''))}</li>)
        index += 1
      }
      blocks.push(ordered ? <ol key={index}>{items}</ol> : <ul key={index}>{items}</ul>)
      continue
    }
    if (line.startsWith('> ')) {
      blocks.push(<blockquote key={index}>{inline(line.slice(2))}</blockquote>)
      index += 1
      continue
    }
    const paragraph = [line]
    index += 1
    while (index < lines.length && lines[index].trim() && !/^(?:#{2,3}\s+|[-*+]\s+|\d+\.\s+|>\s+)/.test(lines[index].trim())) {
      paragraph.push(lines[index].trim())
      index += 1
    }
    blocks.push(<p key={index}>{inline(paragraph.join(' '))}</p>)
  }
  return <>{blocks}</>
}
