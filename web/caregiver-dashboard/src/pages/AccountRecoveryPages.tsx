import { FormEvent, useEffect, useState } from 'react'
import { CheckCircle, KeyRound, Link2Off, Lock, MailCheck } from 'lucide-react'
import { authApi } from '../api/dashboardApi'

// ── Reset Password ────────────────────────────────────────────────────────────
export function ResetPassword({ token }: { token: string }) {
  const [password, setPassword]   = useState('')
  const [confirm, setConfirm]     = useState('')
  const [message, setMessage]     = useState('')
  const [error, setError]         = useState('')
  const [loading, setLoading]     = useState(false)
  const [done, setDone]           = useState(false)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setMessage('')
    setError('')
    if (password !== confirm) {
      setError('Passwords do not match.')
      return
    }
    if (!token) {
      setError('This reset link is incomplete or has already been used.')
      return
    }
    setLoading(true)
    try {
      await authApi.confirmPasswordReset(token, password)
      setDone(true)
      setMessage('Password reset. You can now return to sign in.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to reset the password.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="reset-heading">
        <div className="brand" style={{ paddingBottom: 0 }}>
          <img className="brand-image" src="/neurox-logo.svg" alt="NeuroX" />
        </div>

        <p className="eyebrow" style={{ marginTop: 24 }}>ACCOUNT RECOVERY</p>
        <h1 id="reset-heading">Choose a new password</h1>
        <p className="subtitle">
          Your new password must be at least 8 characters.
        </p>

        {done ? (
          <div style={{ marginTop: 24, display: 'flex', flexDirection: 'column', gap: 16, alignItems: 'center' }}>
            <div style={{ background: 'var(--teal-dim)', borderRadius: '50%', padding: 14, color: 'var(--teal)' }}>
              <CheckCircle size={32} aria-hidden="true" />
            </div>
            <p className="success" role="status" style={{ textAlign: 'center' }}>{message}</p>
            <a className="auth-submit" href="/" style={{ textDecoration: 'none', display: 'grid', placeItems: 'center', width: '100%' }}>
              Return to sign in
            </a>
          </div>
        ) : (
          <form onSubmit={submit} noValidate>
            {!token && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 14px', background: 'var(--red-dim)', borderRadius: 'var(--radius-sm)', marginTop: 16 }}>
                <Link2Off size={18} style={{ color: 'var(--red)', flexShrink: 0 }} aria-hidden="true" />
                <span style={{ color: 'var(--red)', fontSize: '0.82rem' }}>
                  This link is incomplete. Request a new password reset from the sign-in page.
                </span>
              </div>
            )}
            <label style={{ marginTop: 16, display: 'grid', gap: 7, color: 'var(--text-secondary)', fontSize: '0.82rem', fontWeight: 600 }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <KeyRound size={13} aria-hidden="true" />
                New password
              </span>
              <input
                id="reset-password"
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                autoComplete="new-password"
                minLength={8}
                required
                aria-required="true"
                disabled={!token}
              />
            </label>
            <label style={{ marginTop: 14, display: 'grid', gap: 7, color: 'var(--text-secondary)', fontSize: '0.82rem', fontWeight: 600 }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Lock size={13} aria-hidden="true" />
                Confirm new password
              </span>
              <input
                id="reset-confirm"
                type="password"
                value={confirm}
                onChange={e => setConfirm(e.target.value)}
                autoComplete="new-password"
                minLength={8}
                required
                aria-required="true"
                disabled={!token}
              />
            </label>

            {error && <p className="auth-error" role="alert" style={{ marginTop: 12 }}>{error}</p>}

            <button
              id="reset-submit"
              className="auth-submit"
              disabled={loading || !token}
              aria-busy={loading}
              style={{ marginTop: 20, width: '100%' }}
            >
              {loading ? 'Resetting password…' : 'Reset password'}
            </button>
          </form>
        )}

        <a className="auth-toggle" href="/" style={{ display: 'block', marginTop: 16 }}>
          ← Return to sign in
        </a>

        <p className="auth-foot">
          NeuroX provides caregiver coordination and supportive insights.
          It does not replace clinical care or guarantee emergency response.
        </p>
      </section>
    </main>
  )
}

// ── Verify Email ──────────────────────────────────────────────────────────────
export function VerifyEmail({ token }: { token: string }) {
  const [message, setMessage] = useState('')
  const [error, setError]     = useState('')
  const [loading, setLoading] = useState(true)
  const [done, setDone]       = useState(false)

  useEffect(() => {
    if (!token) {
      setLoading(false)
      setError('This verification link is incomplete or has already been used.')
      return
    }
    authApi.confirmEmailVerification(token)
      .then(() => {
        setDone(true)
        setMessage('Email verified. You can now sign in with your caregiver account.')
      })
      .catch(err => {
        setError(err instanceof Error ? err.message : 'Unable to verify this email.')
      })
      .finally(() => setLoading(false))
  }, [token])

  return (
    <main className="auth-page">
      <section className="auth-card" aria-labelledby="verify-heading">
        <div className="brand" style={{ paddingBottom: 0 }}>
          <img className="brand-image" src="/neurox-logo.svg" alt="NeuroX" />
        </div>

        <p className="eyebrow" style={{ marginTop: 24 }}>EMAIL VERIFICATION</p>
        <h1 id="verify-heading">Verify your email</h1>
        <p className="subtitle">
          Confirming your caregiver account email address.
        </p>

        <div style={{ marginTop: 24 }}>
          {loading && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--text-secondary)', fontSize: '0.88rem' }}>
              <div className="live-dot" aria-hidden="true" />
              <span role="status">Verifying your email address…</span>
            </div>
          )}

          {done && !loading && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
              <div style={{ background: 'var(--teal-dim)', borderRadius: '50%', padding: 14, color: 'var(--teal)' }}>
                <MailCheck size={32} aria-hidden="true" />
              </div>
              <p className="success" role="status" style={{ textAlign: 'center' }}>{message}</p>
              <a
                className="auth-submit"
                href="/"
                style={{ textDecoration: 'none', display: 'grid', placeItems: 'center', width: '100%' }}
              >
                Sign in to your account
              </a>
            </div>
          )}

          {error && (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 14px', background: 'var(--red-dim)', borderRadius: 'var(--radius-sm)' }}>
                <Link2Off size={18} style={{ color: 'var(--red)', flexShrink: 0 }} aria-hidden="true" />
                <p className="auth-error" role="alert" style={{ background: 'transparent', border: 0, padding: 0, margin: 0 }}>{error}</p>
              </div>
              <a className="auth-toggle" href="/" style={{ display: 'block', marginTop: 14 }}>
                Request a new verification email from the sign-in page.
              </a>
            </div>
          )}
        </div>

        <a className="auth-toggle" href="/" style={{ display: 'block', marginTop: 20 }}>
          ← Return to sign in
        </a>

        <p className="auth-foot">
          NeuroX provides caregiver coordination and supportive insights.
          It does not replace clinical care or guarantee emergency response.
        </p>
      </section>
    </main>
  )
}
