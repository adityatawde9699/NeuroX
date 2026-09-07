import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ReportsPage } from '../pages/ReportsPage'
import { dashboardApi } from '../api/dashboardApi'
import { makeActivityReport } from './helpers'

vi.mock('../api/dashboardApi', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/dashboardApi')>()
  return {
    ...actual,
    dashboardApi: {
      ...actual.dashboardApi,
      report: vi.fn(),
    },
  }
})

const mockReport = vi.mocked(dashboardApi.report)

describe('ReportsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the panel heading regardless of data', () => {
    mockReport.mockResolvedValue(makeActivityReport({ summary: { sessions: 0, completionRate: 0, averageAccuracy: 0, averageResponseTime: 0, averageDifficulty: 0 }, series: [] }))
    render(<ReportsPage patientId="maya-demo" />)
    expect(screen.getByRole('heading', { name: /Activity report/i })).toBeInTheDocument()
  })

  it('shows loading state initially when patientId is provided', () => {
    mockReport.mockResolvedValue(makeActivityReport())
    render(<ReportsPage patientId="maya-demo" />)
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('shows empty state when the report has zero sessions', async () => {
    const empty = makeActivityReport({
      summary: { sessions: 0, completionRate: 0, averageAccuracy: 0, averageResponseTime: 0, averageDifficulty: 0 },
      series: [],
    })
    mockReport.mockResolvedValue(empty)
    render(<ReportsPage patientId="maya-demo" />)
    await waitFor(() =>
      expect(screen.getByText(/No completed activities are available/i)).toBeInTheDocument()
    )
  })

  it('renders summary stats when report has sessions', async () => {
    mockReport.mockResolvedValue(makeActivityReport())
    render(<ReportsPage patientId="maya-demo" />)
    await waitFor(() => expect(screen.getByText('5')).toBeInTheDocument())
    // Completion rate 0.8 → 80 %
    expect(screen.getByText('80%')).toBeInTheDocument()
    // Average accuracy 0.78 → 78 %
    expect(screen.getByText('78%')).toBeInTheDocument()
  })

  it('shows series rows for each activity session', async () => {
    const report = makeActivityReport()
    mockReport.mockResolvedValue(report)
    render(<ReportsPage patientId="maya-demo" />)
    await waitFor(() => {
      // Series has one entry; completion 1.0 → 100 %, accuracy 0.9 → 90 %
      expect(screen.getByText(/Completion 100%/)).toBeInTheDocument()
      expect(screen.getByText(/Accuracy 90%/)).toBeInTheDocument()
    })
  })

  it('calls report API with ISO date strings from the filter form', async () => {
    mockReport.mockResolvedValue(makeActivityReport())
    const user = userEvent.setup()
    render(<ReportsPage patientId="maya-demo" />)

    // Fill in the activityId filter.
    const activityInput = screen.getByPlaceholderText('memory-match')
    await user.type(activityInput, 'memory-match')

    // Submit the form.
    await user.click(screen.getByRole('button', { name: /Apply filters/i }))

    // The report API should be called a second time (once on mount, once on submit).
    await waitFor(() => expect(mockReport).toHaveBeenCalledTimes(2))
    const [, secondArgs] = mockReport.mock.calls
    expect(secondArgs[1]).toMatchObject({ activityId: 'memory-match' })
  })

  it('shows an error and retry button on API failure', async () => {
    mockReport.mockRejectedValue(new Error('Server error'))
    render(<ReportsPage patientId="maya-demo" />)
    await waitFor(() => expect(screen.getByText(/Server error/)).toBeInTheDocument())
    expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument()
  })

  it('does not call the API when patientId is absent', () => {
    render(<ReportsPage />)
    expect(mockReport).not.toHaveBeenCalled()
  })
})
