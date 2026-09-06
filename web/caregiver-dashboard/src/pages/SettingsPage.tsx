import { FormEvent, useState } from 'react'
import { authApi } from '../api/dashboardApi'
import { storeSession } from '../auth/authStorage'
import type { AuthUser } from '../types/dashboard'

export function SettingsPage({user, onUpdated}: {user: AuthUser; onUpdated: (user: AuthUser) => void}) {
  const [name, setName] = useState(user.name)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [passwordMessage, setPasswordMessage] = useState('')
  const [passwordError, setPasswordError] = useState('')
  const [passwordSaving, setPasswordSaving] = useState(false)
  const save = async (event: FormEvent) => {
    event.preventDefault(); setSaving(true); setMessage(''); setError('')
    try { const updated = await authApi.updateProfile(name); const token = localStorage.getItem('neurox-token') ?? ''; const refresh = localStorage.getItem('neurox-refresh-token') ?? ''; storeSession(token, refresh, updated); onUpdated(updated); setMessage('Profile settings saved.') } catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to save profile settings.') } finally { setSaving(false) }
  }
  const changePassword = async (event: FormEvent) => {
    event.preventDefault(); setPasswordSaving(true); setPasswordMessage(''); setPasswordError('')
    try { await authApi.changePassword(currentPassword, newPassword); setCurrentPassword(''); setNewPassword(''); setPasswordMessage('Password updated.') } catch (cause) { setPasswordError(cause instanceof Error ? cause.message : 'Unable to update password.') } finally { setPasswordSaving(false) }
  }
  return <section className="config-layout"><article className="panel config" aria-labelledby="settings-heading"><div className="panel-head"><div><p className="eyebrow">SETTINGS</p><h2 id="settings-heading">Caregiver profile</h2><p>Update the name shown in the caregiver portal.</p></div></div><form className="config-form" onSubmit={save}><label>Display name<input value={name} onChange={event => setName(event.target.value)} minLength={2} maxLength={80} required/></label>{message && <p className="success">{message}</p>}{error && <p className="auth-error" role="alert">{error}</p>}<button className="auth-submit" disabled={saving}>{saving ? 'Saving…' : 'Save profile'}</button></form></article><article className="panel config"><div className="panel-head"><div><p className="eyebrow">SECURITY</p><h2>Change password</h2><p>Use a new password of at least eight characters.</p></div></div><form className="config-form" onSubmit={changePassword}><label>Current password<input type="password" value={currentPassword} onChange={event => setCurrentPassword(event.target.value)} minLength={8} required/></label><label>New password<input type="password" value={newPassword} onChange={event => setNewPassword(event.target.value)} minLength={8} required/></label>{passwordMessage && <p className="success">{passwordMessage}</p>}{passwordError && <p className="auth-error" role="alert">{passwordError}</p>}<button className="auth-submit" disabled={passwordSaving}>{passwordSaving ? 'Updating…' : 'Update password'}</button></form></article></section>
}