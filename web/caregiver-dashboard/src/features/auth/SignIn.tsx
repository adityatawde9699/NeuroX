import { FormEvent, useEffect, useState } from 'react'
import { authApi } from '../../api/dashboardApi'
import { storeSession } from '../../auth/authStorage'
import type { AuthUser } from '../../types/dashboard'

type AuthResponse = { access_token: string; user: AuthUser }

type Props = {
  onAuthenticated: (user: AuthUser) => void
  notice?: string
}

export function SignIn({ onAuthenticated, notice }: Props) {
  const [creatingAccount, setCreatingAccount] = useState(false)
  const [name, setName]         = useState('')
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)
  const [recoveryMessage, setRecoveryMessage] = useState('')

  const finish = (data: AuthResponse) => {
    storeSession(data.access_token, data.user)
    onAuthenticated(data.user)
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const data = creatingAccount
        ? await authApi.register(name.trim(), email.trim(), password)
        : await authApi.login(email.trim(), password)

      if (creatingAccount && data.user.emailVerified === false) {
        setCreatingAccount(false)
        setPassword('')
        try {
          const verification = await authApi.requestEmailVerification(data.access_token)
          setRecoveryMessage(verification.message)
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Unable to send the verification email.')
        }
      } else {
        finish(data)
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : creatingAccount ? 'Unable to create your account.' : 'Unable to sign in.'
      )
    } finally {
      setLoading(false)
    }
  }

  const changeMode = () => {
    setCreatingAccount(current => !current)
    setError('')
    setPassword('')
    setRecoveryMessage('')
  }

  const requestReset = async () => {
    setError('')
    setRecoveryMessage('')
    if (!email.trim()) { setError('Enter your email address first.'); return }
    try {
      setRecoveryMessage((await authApi.requestPasswordReset(email.trim())).message)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to request a password reset.')
    }
  }

  // Google Sign-In
  useEffect(() => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID
    if (!clientId) return
    const script = document.createElement('script')
    script.src = 'https://accounts.google.com/gsi/client'
    script.async = true
    script.onload = () => {
      window.google?.accounts.id.initialize({
        client_id: clientId,
        callback: async ({ credential }: { credential: string }) => {
          try {
            finish(await authApi.google(credential))
          } catch (err) {
            setError(err instanceof Error ? err.message : 'Google sign-in failed.')
          }
        },
      })
      const target = document.getElementById('google-button')
      if (target) {
        target.textContent = ''
        window.google?.accounts.id.renderButton(target, {
          theme: 'filled_black', size: 'large', width: 360, text: 'continue_with',
        })
      }
    }
    document.head.appendChild(script)
    return () => script.remove()
  }, [])

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="auth-heading">
        <div className="brand" style={{ paddingBottom: 0 }}>
          <span className="logo" aria-hidden="true">N</span>
          <span>neuro<span>X</span></span>
        </div>

        <p className="eyebrow" style={{ marginTop: 24 }}>CAREGIVER PORTAL</p>
        <h1 id="auth-heading">
          {creatingAccount ? 'Create your account' : 'Welcome back'}
        </h1>
        <p className="subtitle">
          {creatingAccount
            ? 'Create a caregiver account to coordinate supportive activity and safety information.'
            : 'Sign in to view supportive activity and safety information for your patients.'}
        </p>

        <form onSubmit={submit} noValidate>
          {creatingAccount && (
            <label>
              Full name
              <input
                id="auth-name"
                value={name}
                onChange={e => setName(e.target.value)}
                autoComplete="name"
                minLength={2}
                maxLength={80}
                required
                aria-required="true"
              />
            </label>
          )}
          <label>
            Email address
            <input
              id="auth-email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              autoComplete="email"
              type="email"
              required
              aria-required="true"
            />
          </label>
          <label>
            Password
            <input
              id="auth-password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              autoComplete={creatingAccount ? 'new-password' : 'current-password'}
              type="password"
              minLength={8}
              required
              aria-required="true"
            />
          </label>

          {(error || notice) && (
            <p className="auth-error" role="alert">{error || notice}</p>
          )}
          {recoveryMessage && (
            <p className="success" role="status">{recoveryMessage}</p>
          )}

          <button
            id="auth-submit"
            className="auth-submit"
            disabled={loading}
            aria-busy={loading}
          >
            {loading
              ? (creatingAccount ? 'Creating account…' : 'Signing in…')
              : (creatingAccount ? 'Create caregiver account' : 'Sign in')}
          </button>
        </form>

        {!creatingAccount && (
          <button
            type="button"
            className="auth-toggle"
            id="auth-forgot-password"
            onClick={() => void requestReset()}
          >
            Forgot password?
          </button>
        )}

        <button
          type="button"
          className="auth-toggle"
          id="auth-mode-toggle"
          onClick={changeMode}
        >
          {creatingAccount
            ? 'Already have an account? Sign in'
            : 'New to NeuroX? Create a caregiver account'}
        </button>

        <div className="or" aria-hidden="true">
          <span /><span>or continue with</span><span />
        </div>

        <div
          id="google-button"
          className="google-placeholder"
          role="region"
          aria-label="Google sign-in"
        >
          Google sign-in appears after you set VITE_GOOGLE_CLIENT_ID.
        </div>

        <p className="auth-foot">
          NeuroX provides caregiver coordination and supportive insights.
          It does not replace clinical care or guarantee emergency response.
        </p>
      </section>
    </main>
  )
}
