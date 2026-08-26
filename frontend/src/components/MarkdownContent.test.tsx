import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { MarkdownContent } from './MarkdownContent'

describe('MarkdownContent', () => {
  it('renders headings, emphasis and lists without raw markdown markers', () => {
    render(<MarkdownContent value={'## 建议\n\n* **窗口期**：只有 20 天\n* 成本'} />)
    expect(screen.getByRole('heading', { name: '建议' })).toBeInTheDocument()
    expect(screen.getByText('窗口期').tagName).toBe('STRONG')
    expect(screen.getByRole('list')).toHaveTextContent('成本')
  })
})
