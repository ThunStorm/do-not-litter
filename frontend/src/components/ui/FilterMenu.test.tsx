import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { FilterMenu } from './FilterMenu'

describe('FilterMenu portal', () => {
  it('escapes scroll clipping, navigates with keyboard, and returns focus', () => {
    const onChange = vi.fn()
    const { container } = render(<div style={{ overflow: 'auto', height: 38 }}><FilterMenu label="状态" value="" onChange={onChange} options={[{ value: '', label: '全部' }, { value: 'SAVED', label: '想去' }]} /></div>)
    const trigger = screen.getByRole('button', { name: '状态' })
    fireEvent.click(trigger)
    const list = screen.getByRole('listbox', { name: '状态' })
    expect(container.contains(list)).toBe(false)
    fireEvent.keyDown(within(list).getByRole('option', { name: '全部' }), { key: 'End' })
    expect(within(list).getByRole('option', { name: '想去' })).toHaveFocus()
    fireEvent.click(within(list).getByRole('option', { name: '想去' }))
    expect(onChange).toHaveBeenCalledWith('SAVED')
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
    expect(trigger).toHaveFocus()
  })
  it('allows one open menu and closes on an outside pointer', () => {
    render(<><FilterMenu label="季节" value="" options={[{ value: '', label: '全部' }]} onChange={vi.fn()} /><FilterMenu label="月份" value="" options={[{ value: '', label: '全部' }]} onChange={vi.fn()} /></>)
    fireEvent.click(screen.getByRole('button', { name: '季节' }))
    fireEvent.click(screen.getByRole('button', { name: '月份' }))
    expect(screen.queryByRole('listbox', { name: '季节' })).not.toBeInTheDocument()
    expect(screen.getByRole('listbox', { name: '月份' })).toBeInTheDocument()
    fireEvent.pointerDown(document.body)
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument()
  })
})
