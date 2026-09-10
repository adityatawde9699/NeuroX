import { expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AppErrorBoundary } from '../components/AppErrorBoundary'

function Broken(): never { throw new Error('private render detail') }

it('shows a safe recovery screen when rendering fails', () => {
  vi.spyOn(console, 'error').mockImplementation(() => undefined)
  render(<AppErrorBoundary><Broken/></AppErrorBoundary>)
  expect(screen.getByRole('alert')).toHaveTextContent('could not be displayed')
  expect(screen.queryByText('private render detail')).not.toBeInTheDocument()
  expect(screen.getByRole('button', {name: 'Reload dashboard'})).toBeInTheDocument()
})
