import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { authApi } from '../api/dashboardApi'
import { ResetPassword, VerifyEmail } from '../pages/AccountRecoveryPages'

vi.mock('../api/dashboardApi', async importOriginal => {
  const actual = await importOriginal<typeof import('../api/dashboardApi')>()
  return {
    ...actual,
    authApi: {
      ...actual.authApi,
      confirmEmailVerification: vi.fn(),
      confirmPasswordReset: vi.fn(),
    },
  }
})

const confirmEmail = vi.mocked(authApi.confirmEmailVerification)
const confirmPassword = vi.mocked(authApi.confirmPasswordReset)

describe('account recovery pages', () => {
  beforeEach(() => vi.clearAllMocks())

  it('confirms a password reset token', async () => {
    confirmPassword.mockResolvedValue({reset: true})
    const user = userEvent.setup()
    render(<ResetPassword token="a-valid-reset-token-with-more-than-32-characters"/>)
    await user.type(screen.getByLabelText('New password'), 'Replacement!456')
    await user.click(screen.getByRole('button', {name: 'Reset password'}))
    expect(confirmPassword).toHaveBeenCalledWith('a-valid-reset-token-with-more-than-32-characters', 'Replacement!456')
    expect(await screen.findByText(/Password reset/)).toBeInTheDocument()
  })

  it('confirms email verification on arrival', async () => {
    confirmEmail.mockResolvedValue({verified: true})
    render(<VerifyEmail token="a-valid-verification-token-with-32-characters"/>)
    await waitFor(() => expect(confirmEmail).toHaveBeenCalled())
    expect(await screen.findByText(/Email verified/)).toBeInTheDocument()
  })

  it('rejects an incomplete verification link locally', async () => {
    render(<VerifyEmail token=""/>)
    expect(await screen.findByRole('alert')).toHaveTextContent('incomplete')
    expect(confirmEmail).not.toHaveBeenCalled()
  })
})
