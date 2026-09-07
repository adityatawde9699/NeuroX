import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AlertsPage } from '../pages/AlertsPage'
import { dashboardApi } from '../api/dashboardApi'
import { makeAlert, makeSosAlert } from './helpers'

// Mock the entire dashboardApi module so no real HTTP calls occur.
vi.mock('../api/dashboardApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/dashboardApi')>()
  return {
    ...actual,
    dashboardApi: {
      ...actual.dashboardApi,
      alerts: vi.fn(),
      acknowledge: vi.fn(),
    },
  }
})

const mockAlerts = vi.mocked(dashboardApi.alerts)
const mockAcknowledge = vi.mocked(dashboardApi.acknowledge)

describe('AlertsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the empty state when no patientId is provided', () => {
    render(<AlertsPage />)
    expect(screen.getByText('No safety alerts are available.')).toBeInTheDocument()
  })

  it('shows a loading state then renders alerts', async () => {
    const alert = makeAlert()
    mockAlerts.mockResolvedValue([alert])

    render(<AlertsPage patientId="maya-demo" />)

    // Loading state is visible initially.
    expect(screen.getByRole('status')).toBeInTheDocument()

    // After the promise resolves, the alert is shown.
    await waitFor(() => expect(screen.getByText('Patient may have left the safe zone.')).toBeInTheDocument())
    expect(mockAlerts).toHaveBeenCalledWith('maya-demo')
  })

  it('displays the severity badge for high-severity alerts', async () => {
    mockAlerts.mockResolvedValue([makeAlert({ severity: 'high' })])
    render(<AlertsPage patientId="maya-demo" />)
    await waitFor(() => expect(screen.getByText('High')).toBeInTheDocument())
  })

  it('displays "medium" severity badge', async () => {
    mockAlerts.mockResolvedValue([makeAlert({ severity: 'medium' })])
    render(<AlertsPage patientId="maya-demo" />)
    await waitFor(() => expect(screen.getByText('Medium')).toBeInTheDocument())
  })

  it('shows the SOS label for sos-kind alerts', async () => {
    mockAlerts.mockResolvedValue([makeSosAlert()])
    render(<AlertsPage patientId="maya-demo" />)
    await waitFor(() => expect(screen.getByText('SOS caregiver workflow')).toBeInTheDocument())
  })

  it('shows escalation note when escalatedToPriority > 1', async () => {
    const escalated = makeAlert({ escalatedToPriority: 2, workflowNote: 'Caregiver notified.' })
    mockAlerts.mockResolvedValue([escalated])
    render(<AlertsPage patientId="maya-demo" />)
    await waitFor(() => expect(screen.getByText(/Escalated to priority 2/)).toBeInTheDocument())
    expect(screen.getByText(/Caregiver notified/)).toBeInTheDocument()
  })

  it('does not show escalation note when escalatedToPriority is 1', async () => {
    mockAlerts.mockResolvedValue([makeAlert({ escalatedToPriority: 1 })])
    render(<AlertsPage patientId="maya-demo" />)
    await waitFor(() => expect(screen.getByText('Patient may have left the safe zone.')).toBeInTheDocument())
    expect(screen.queryByText(/Escalated to priority/)).toBeNull()
  })

  it('shows the Acknowledge button only for open alerts', async () => {
    const open = makeAlert({ id: 'a1', status: 'open' })
    const acked = makeAlert({ id: 'a2', status: 'acknowledged' })
    mockAlerts.mockResolvedValue([open, acked])
    render(<AlertsPage patientId="maya-demo" />)
    await waitFor(() => expect(screen.getAllByText('Patient may have left the safe zone.')).toHaveLength(2))
    const buttons = screen.getAllByRole('button', { name: /Acknowledge/i })
    expect(buttons).toHaveLength(1)
  })

  it('marks an alert as acknowledged after clicking Acknowledge', async () => {
    const alert = makeAlert({ id: 'ack-test' })
    mockAlerts.mockResolvedValue([alert])
    mockAcknowledge.mockResolvedValue(undefined as never)
    const user = userEvent.setup()

    render(<AlertsPage patientId="maya-demo" />)
    await waitFor(() => expect(screen.getByRole('button', { name: /Acknowledge/i })).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: /Acknowledge/i }))

    expect(mockAcknowledge).toHaveBeenCalledWith('maya-demo', 'alert', 'ack-test')
    await waitFor(() => expect(screen.queryByRole('button', { name: /Acknowledge/i })).toBeNull())
  })

  it('sorts open alerts before acknowledged ones', async () => {
    const open = makeAlert({ id: 'open-1', status: 'open', message: 'Open alert' })
    const acked = makeAlert({ id: 'acked-1', status: 'acknowledged', message: 'Acked alert' })
    // Provide acknowledged first in the API response to verify sorting.
    mockAlerts.mockResolvedValue([acked, open])
    render(<AlertsPage patientId="maya-demo" />)
    await waitFor(() => expect(screen.getByText('Open alert')).toBeInTheDocument())
    const items = screen.getAllByRole('button', { name: /Acknowledge/i })
    // Only the open alert has an Acknowledge button — it must appear first in DOM.
    const allText = document.body.textContent ?? ''
    expect(allText.indexOf('Open alert')).toBeLessThan(allText.indexOf('Acked alert'))
  })

  it('shows an error state when the API rejects', async () => {
    mockAlerts.mockRejectedValue(new Error('Network failure'))
    render(<AlertsPage patientId="maya-demo" />)
    await waitFor(() => expect(screen.getByText(/Network failure/)).toBeInTheDocument())
    expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument()
  })
})
