import { act, renderHook } from '@testing-library/react'
import type { PointerEvent } from 'react'
import { expect, it, vi } from 'vitest'

import { useModelProfileDrag } from './useModelProfileDrag'

it('moves the entire card, shifts its neighbor, and restores visuals on drop or cancellation', () => {
  const list = document.createElement('div')
  list.className = 'model-library__list'
  list.innerHTML = '<section data-model-profile-id="a"><button></button></section><section data-model-profile-id="b"></section>'
  document.body.append(list)
  const cards = [...list.querySelectorAll('section')]
  cards.forEach((card, index) => {
    card.getBoundingClientRect = () => ({ top: index * 112, bottom: index * 112 + 100, height: 100 }) as DOMRect
  })
  const handle = list.querySelector('button')!
  handle.setPointerCapture = vi.fn()
  handle.hasPointerCapture = () => true
  handle.releasePointerCapture = vi.fn()
  const event = (y: number) => ({ button: 0, pointerId: 1, clientY: y, currentTarget: handle, preventDefault: vi.fn() }) as unknown as PointerEvent<HTMLButtonElement>
  const move = vi.fn()
  const { result, unmount } = renderHook(() => useModelProfileDrag(move))
  act(() => { result.current.start(event(20), 'a'); result.current.update(event(140)) })
  expect(cards[0].style.transform).toBe('translateY(120px)')
  expect(cards[0]).toHaveClass('model-profile--dragging')
  expect(cards[1].style.transform).toBe('translateY(-112px)')
  act(() => result.current.finish(event(140)))
  expect(move).toHaveBeenCalledWith('a', 'b')
  expect(cards[0].style.transform).toBe('')
  act(() => { result.current.start(event(20), 'a'); result.current.update(event(140)); result.current.finish(event(140), true) })
  expect(move).toHaveBeenCalledTimes(1)
  expect(cards[0]).not.toHaveClass('model-profile--dragging')
  unmount()
  list.remove()
})
