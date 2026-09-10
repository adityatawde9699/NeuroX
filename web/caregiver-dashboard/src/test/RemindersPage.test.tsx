import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { dashboardApi } from '../api/dashboardApi'
import { RemindersPage } from '../pages/RemindersPage'

vi.mock('../api/dashboardApi', async importOriginal => {
  const actual = await importOriginal<typeof import('../api/dashboardApi')>()
  return {
    ...actual,
    dashboardApi: {
      ...actual.dashboardApi,
      reminders: vi.fn(),
      createReminder: vi.fn(),
      updateReminder: vi.fn(),
    },
  }
})

const mockReminders = vi.mocked(dashboardApi.reminders)
const mockCreate = vi.mocked(dashboardApi.createReminder)

describe('RemindersPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockReminders.mockResolvedValue([])
  })

  it('requires explicit caregiver confirmation for medication schedules', async () => {
    const user = userEvent.setup()
    render(<RemindersPage patientId="patient-1"/>)
    await user.selectOptions(screen.getByLabelText('Reminder type'), 'medication')

    expect(screen.getByText(/does not provide dosage advice/i)).toBeInTheDocument()
    expect(screen.getByRole('button', {name:'Save reminder'})).toBeDisabled()
    await user.click(screen.getByRole('checkbox', {name:/I confirm this medication reminder/}))
    expect(screen.getByRole('button', {name:'Save reminder'})).toBeEnabled()
  })

  it('submits a confirmed medication schedule with the browser time zone', async () => {
    const user = userEvent.setup()
    mockCreate.mockResolvedValue({id:'r1', patientId:'patient-1', type:'medication', title:'Check care plan', description:null, scheduledTime:'2026-09-12T03:30:00Z', repeatRule:'daily', enabled:true, completed:false, status:'upcoming', snoozedUntil:null, acknowledgedAt:null, timezoneName:'Asia/Kolkata'})
    render(<RemindersPage patientId="patient-1"/>)
    await user.selectOptions(screen.getByLabelText('Reminder type'), 'medication')
    await user.type(screen.getByLabelText('Title'), 'Check care plan')
    fireEvent.change(screen.getByLabelText('Local date and time'), {target:{value:'2026-09-12T09:00'}})
    await user.selectOptions(screen.getByLabelText('Repeat'), 'daily')
    await user.click(screen.getByRole('checkbox', {name:/I confirm this medication reminder/}))
    await user.click(screen.getByRole('button', {name:'Save reminder'}))

    await waitFor(() => expect(mockCreate).toHaveBeenCalledWith(expect.objectContaining({
      patient_id:'patient-1', type:'medication', title:'Check care plan', repeat_rule:'daily',
    })))
    expect(await screen.findByText(/schedule saved/)).toBeInTheDocument()
  })
})
