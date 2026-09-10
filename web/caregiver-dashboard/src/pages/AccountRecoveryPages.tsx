import { FormEvent, useEffect, useState } from 'react'
import { authApi } from '../api/dashboardApi'

export function ResetPassword({token}:{token:string}) {
  const [password, setPassword] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const submit = async (event:FormEvent) => {
    event.preventDefault(); setMessage(''); setError('')
    if (!token) { setError('This reset link is incomplete.'); return }
    try { await authApi.confirmPasswordReset(token, password); setMessage('Password reset. You can now return to sign in.') }
    catch (err) { setError(err instanceof Error ? err.message : 'Unable to reset the password.') }
  }
  return <main className="auth-page"><section className="auth-card"><p className="eyebrow">ACCOUNT RECOVERY</p><h1>Choose a new password</h1><form onSubmit={submit}><label>New password<input type="password" autoComplete="new-password" minLength={8} required value={password} onChange={event=>setPassword(event.target.value)}/></label>{error&&<p className="auth-error" role="alert">{error}</p>}{message&&<p className="success" role="status">{message}</p>}<button className="auth-submit">Reset password</button></form><a className="auth-toggle" href="/">Return to sign in</a></section></main>
}

export function VerifyEmail({token}:{token:string}) {
  const [message, setMessage] = useState('Verifying your email…')
  const [error, setError] = useState('')
  useEffect(() => {
    if (!token) { setMessage(''); setError('This verification link is incomplete.'); return }
    void authApi.confirmEmailVerification(token).then(() => setMessage('Email verified. You can now sign in.')).catch(err => { setMessage(''); setError(err instanceof Error ? err.message : 'Unable to verify this email.') })
  }, [token])
  return <main className="auth-page"><section className="auth-card"><p className="eyebrow">EMAIL VERIFICATION</p><h1>Verify your email</h1>{message&&<p className="success" role="status">{message}</p>}{error&&<p className="auth-error" role="alert">{error}</p>}<a className="auth-toggle" href="/">Return to sign in</a></section></main>
}
