import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { authApi } from '../api/dashboardApi'
import { SettingsPage } from '../pages/SettingsPage'

vi.mock('../api/dashboardApi', async importOriginal => {
  const actual = await importOriginal<typeof import('../api/dashboardApi')>()
  return {
    ...actual,
    authApi: {
      ...actual.authApi,
      sessions: vi.fn(),
      revokeSession: vi.fn(),
      preferences: vi.fn(),
      updatePreferences: vi.fn(),
    },
  }
})

const mockSessions = vi.mocked(authApi.sessions)
const mockRevoke = vi.mocked(authApi.revokeSession)
const mockPreferences = vi.mocked(authApi.preferences)
const mockUpdatePreferences = vi.mocked(authApi.updatePreferences)
const session = {
  id: '12345678-abcd-1234-abcd-123456789abc',
  created_at: '2026-09-10T08:00:00Z',
  last_used_at: null,
  expires_at: '2026-09-24T08:00:00Z',
  device_name: 'NeuroX Web',
}

describe('SettingsPage sessions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockPreferences.mockResolvedValue({available: true, notifySos: true, notifySafetyAlerts: true, notifyReminders: true, updatedAt: '2026-09-10T08:00:00Z'})
  })

  it('lists active sessions', async () => {
    mockSessions.mockResolvedValue([session])
    render(<SettingsPage user={{id: 'u1', name: 'Caregiver', email: 'c@example.com', role: 'CAREGIVER'}} onUpdated={vi.fn()}/>)
    await waitFor(() => expect(screen.getByText('NeuroX Web')).toBeInTheDocument())
    expect(screen.getByRole('button', {name: 'Revoke'})).toBeInTheDocument()
  })

  it('revokes and removes a selected session', async () => {
    mockSessions.mockResolvedValue([session])
    mockRevoke.mockResolvedValue({revoked: true, session_id: session.id})
    const user = userEvent.setup()
    render(<SettingsPage user={{id: 'u1', name: 'Caregiver', email: 'c@example.com', role: 'CAREGIVER'}} onUpdated={vi.fn()}/>)
    await user.click(await screen.findByRole('button', {name: 'Revoke'}))
    expect(mockRevoke).toHaveBeenCalledWith(session.id)
    await waitFor(() => expect(screen.queryByText('NeuroX Web')).not.toBeInTheDocument())
  })

  it('updates caregiver availability', async () => {
    mockSessions.mockResolvedValue([])
    mockUpdatePreferences.mockResolvedValue({available: false, notifySos: true, notifySafetyAlerts: true, notifyReminders: true, updatedAt: '2026-09-10T09:00:00Z'})
    const user = userEvent.setup()
    render(<SettingsPage user={{id: 'u1', name: 'Caregiver', email: 'c@example.com', role: 'CAREGIVER'}} onUpdated={vi.fn()}/>)
    const availability = await screen.findByRole('checkbox', {name: /Available for alerts/})
    await user.click(availability)
    expect(mockUpdatePreferences).toHaveBeenCalledWith({available: false})
    expect(await screen.findByText(/preferences saved/)).toBeInTheDocument()
  })
})
