import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { RecommendationSummary } from './RecommendationSummary'

it('omits default labels across recommended, optional, unknown and missing source opinions', () => {
  const { container } = render(<>{[undefined, 'UNKNOWN', 'RECOMMENDED', 'OPTIONAL'].map((status, index) => <RecommendationSummary key={index} compact value={status ? { status } : undefined} />)}</>)
  expect(container).toBeEmptyDOMElement()
})
it('marks negative sources and preserves the distinction for conflicting sources', () => {
  render(<><RecommendationSummary compact value={{ status: 'NOT_RECOMMENDED' }} /><RecommendationSummary compact value={{ status: 'CONFLICT' }} /></>)
  expect(screen.getByText('不推荐')).toBeVisible()
  expect(screen.getByText('有来源不推荐')).toBeVisible()
})
