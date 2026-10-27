import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { expect, it } from 'vitest'
import type { VideoPlace } from '../../lib/api'
import { VideoPlaceCandidate } from './VideoPlaceCandidate'

const candidate = { id: 'a', name: '通灵大峡谷', poi_policy: 'RESOLVE', resolution_status: 'REVIEW', start_ms: 94000, recommendation_summary: { status: 'UNKNOWN' } } as VideoPlace
it('shows candidate state and a real video time link without a confirmation action or default attitude tag', () => {
  render(<MemoryRouter><ul><VideoPlaceCandidate place={candidate} canonicalUrl="https://www.bilibili.com/video/BVtest" platform="BILIBILI" /></ul></MemoryRouter>)
  expect(screen.getByText('通灵大峡谷')).toBeVisible()
  expect(screen.getByText('待确认')).toBeVisible()
  expect(screen.queryByText('态度未明确')).not.toBeInTheDocument()
  expect(screen.queryByRole('button')).not.toBeInTheDocument()
  expect(screen.getByRole('link')).toHaveAttribute('href', 'https://www.bilibili.com/video/BVtest?t=94')
})
it('keeps a negative mark on a confirmed place without treating position confirmation as a recommendation', () => {
  render(<MemoryRouter><ul><VideoPlaceCandidate place={{ ...candidate, resolution_status: 'CONFIRMED', place_id: 'p', place: { name: '通灵大峡谷', address: '广西' }, recommendation_summary: { status: 'NOT_RECOMMENDED' } }} canonicalUrl="" platform="LOCAL" /></ul></MemoryRouter>)
  expect(screen.getByText('已确认')).toBeVisible()
  expect(screen.getByText('不推荐')).toBeVisible()
  expect(screen.getByRole('link', { name: '通灵大峡谷' })).toHaveAttribute('href', '/places/p')
  expect(screen.queryByText('作者推荐')).not.toBeInTheDocument()
})

it('links a representative destination to the map without calling it a confirmed Place', () => {
  const value = { ...candidate, resolution_status: 'AREA_RESOLVED', destination: { id: 'dst-1', name: '玉龙雪山', scope_type: 'SCENIC_AREA', anchor_kind: 'SCENIC_ENTRY' } }
  render(<MemoryRouter><ul><VideoPlaceCandidate place={value} canonicalUrl="" platform="LOCAL" /></ul></MemoryRouter>)
  expect(screen.getByText('已定位至游客中心')).toBeVisible()
  expect(screen.getByRole('link', { name: '通灵大峡谷' })).toHaveAttribute('href', '/map?place=dst-1')
  expect(screen.queryByText('已确认')).not.toBeInTheDocument()
})

it('shows an administrative area with missing context as awaiting location', () => {
  render(<MemoryRouter><ul><VideoPlaceCandidate place={{ ...candidate, poi_policy: 'AREA_RESOLVE', resolution_status: 'AREA_UNRESOLVED', destination: null }} canonicalUrl="" platform="LOCAL" /></ul></MemoryRouter>)
  expect(screen.getByText('区域待定位')).toBeVisible()
  expect(screen.queryByRole('link')).not.toBeInTheDocument()
})
