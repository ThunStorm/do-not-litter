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
})
