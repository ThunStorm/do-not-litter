import { useEffect, useRef, type PointerEvent } from 'react'

type DragState = {
  cards: HTMLElement[]
  rects: DOMRect[]
  from: number
  to: number
  startY: number
  scrollY: number
}

function clearDrag(drag: DragState | null) {
  drag?.cards.forEach((card) => {
    card.style.removeProperty('transform')
    card.classList.remove('model-profile--dragging', 'model-profile--shifting', 'model-profile--drop-before', 'model-profile--drop-after')
  })
}

export function useModelProfileDrag(move: (source: string, target: string) => void) {
  const active = useRef<DragState | null>(null)
  useEffect(() => () => clearDrag(active.current), [])

  const start = (event: PointerEvent<HTMLButtonElement>, id: string) => {
    if (event.button !== 0) return
    const list = event.currentTarget.closest('.model-library__list')
    const cards = [...(list?.querySelectorAll<HTMLElement>('[data-model-profile-id]') ?? [])]
    const from = cards.findIndex((card) => card.dataset.modelProfileId === id)
    if (from < 0) return
    event.preventDefault()
    event.currentTarget.setPointerCapture(event.pointerId)
    active.current = { cards, rects: cards.map((card) => card.getBoundingClientRect()), from, to: from, startY: event.clientY, scrollY: window.scrollY }
    cards[from].classList.add('model-profile--dragging')
    cards.forEach((card, index) => { if (index !== from) card.classList.add('model-profile--shifting') })
  }

  const update = (event: PointerEvent<HTMLButtonElement>) => {
    const drag = active.current
    if (!drag) return
    const offset = event.clientY - drag.startY + window.scrollY - drag.scrollY
    const source = drag.rects[drag.from]
    const center = source.top + source.height / 2 + offset
    let to = drag.from
    drag.rects.forEach((rect, index) => {
      if (index < drag.from && center < rect.top + rect.height / 2) to = Math.min(to, index)
      if (index > drag.from && center > rect.top + rect.height / 2) to = Math.max(to, index)
    })
    drag.to = to
    const gap = drag.rects.length > 1 ? drag.rects[1].top - drag.rects[0].bottom : 0
    drag.cards.forEach((card, index) => {
      const shift = index === drag.from ? offset
        : index > drag.from && index <= to ? -(source.height + gap)
        : index < drag.from && index >= to ? source.height + gap : 0
      card.style.transform = `translateY(${shift}px)`
      card.classList.toggle('model-profile--drop-before', index === to && to < drag.from)
      card.classList.toggle('model-profile--drop-after', index === to && to > drag.from)
    })
  }

  const finish = (event: PointerEvent<HTMLButtonElement>, cancel = false) => {
    const drag = active.current
    active.current = null
    clearDrag(drag)
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId)
    if (drag && !cancel && drag.from !== drag.to) {
      move(drag.cards[drag.from].dataset.modelProfileId!, drag.cards[drag.to].dataset.modelProfileId!)
    }
  }

  return { start, update, finish }
}
