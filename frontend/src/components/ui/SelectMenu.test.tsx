import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { SelectMenu } from './SelectMenu'

describe('SelectMenu', () => {
  it('supports keyboard selection and escape close', () => {
    const onChange = vi.fn()
    render(<SelectMenu label="部署位置" value="LOCAL" onChange={onChange} options={[{ value: 'LOCAL', label: '本机' }, { value: 'REMOTE', label: '远程' }]} />)

    const trigger = screen.getByRole('button', { name: '本机' })
    fireEvent.keyDown(trigger, { key: 'ArrowDown' })
    expect(onChange).toHaveBeenCalledWith('REMOTE')
    fireEvent.click(trigger)
    expect(screen.getByRole('listbox', { name: '部署位置' })).toBeInTheDocument()
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(screen.queryByRole('listbox', { name: '部署位置' })).not.toBeInTheDocument()
  })

  it('filters searchable options and selects an exact model id', () => {
    const onChange = vi.fn()
    render(<SelectMenu label="模型名" searchable value="old/model" onChange={onChange} options={[{ value: 'old/model', label: 'old/model' }, { value: 'codebuddy/hy3', label: 'codebuddy/hy3' }]} />)
    fireEvent.click(screen.getByRole('button', { name: 'old/model' }))
    fireEvent.change(screen.getByRole('textbox', { name: '搜索模型名' }), { target: { value: 'HY3' } })
    expect(screen.queryByRole('option', { name: 'old/model' })).not.toBeInTheDocument()
    fireEvent.keyDown(screen.getByRole('textbox', { name: '搜索模型名' }), { key: 'Enter' })
    expect(onChange).toHaveBeenCalledWith('codebuddy/hy3')
    expect(screen.queryByRole('listbox', { name: '模型名' })).not.toBeInTheDocument()
  })
})
