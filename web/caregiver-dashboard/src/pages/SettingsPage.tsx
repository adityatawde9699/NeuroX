import { FormEvent, useEffect, useState } from 'react'
import { authApi } from '../api/dashboardApi'
import { readAccessToken, storeSession } from '../auth/authStorage'
import type { AuthUser, CaregiverPreferences, SecuritySession } from '../types/dashboard'

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
  const [sessions, setSessions] = useState<SecuritySession[]>([])
  const [sessionsError, setSessionsError] = useState('')
  const [revoking, setRevoking] = useState<string | null>(null)
  const [preferences, setPreferences] = useState<CaregiverPreferences | null>(null)
  const [preferencesMessage, setPreferencesMessage] = useState('')
  const [preferencesError, setPreferencesError] = useState('')

  useEffect(() => {
    authApi.sessions().then(setSessions).catch(cause => {
      setSessionsError(cause instanceof Error ? cause.message : 'Unable to load active sessions.')
    })
    authApi.preferences().then(setPreferences).catch(cause => {
      setPreferencesError(cause instanceof Error ? cause.message : 'Unable to load notification preferences.')
    })
  }, [])

  const save = async (event: FormEvent) => {
    event.preventDefault()
    setSaving(true); setMessage(''); setError('')
    try {
      const updated = await authApi.updateProfile(name)
      storeSession(readAccessToken() ?? '', updated)
      onUpdated(updated)
      setMessage('Profile settings saved.')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to save profile settings.')
    } finally { setSaving(false) }
  }

  const changePassword = async (event: FormEvent) => {
    event.preventDefault()
    setPasswordSaving(true); setPasswordMessage(''); setPasswordError('')
    try {
      await authApi.changePassword(currentPassword, newPassword)
      setCurrentPassword(''); setNewPassword(''); setSessions([])
      setPasswordMessage('Password updated. Other sessions have been signed out.')
    } catch (cause) {
      setPasswordError(cause instanceof Error ? cause.message : 'Unable to update password.')
    } finally { setPasswordSaving(false) }
  }

  const revoke = async (id: string) => {
    setRevoking(id); setSessionsError('')
    try {
      await authApi.revokeSession(id)
      setSessions(current => current.filter(session => session.id !== id))
    } catch (cause) {
      setSessionsError(cause instanceof Error ? cause.message : 'Unable to revoke the session.')
    } finally { setRevoking(null) }
  }

  const updatePreference = async (payload: Parameters<typeof authApi.updatePreferences>[0]) => {
    setPreferencesMessage(''); setPreferencesError('')
    try {
      setPreferences(await authApi.updatePreferences(payload))
      setPreferencesMessage('Availability and notification preferences saved.')
    } catch (cause) {
      setPreferencesError(cause instanceof Error ? cause.message : 'Unable to save notification preferences.')
    }
  }

  return <section className="config-layout">
    <article className="panel config" aria-labelledby="settings-heading">
      <div className="panel-head"><div><p className="eyebrow">SETTINGS</p><h2 id="settings-heading">Caregiver profile</h2><p>Update the name shown in the caregiver portal.</p></div></div>
      <form className="config-form" onSubmit={save}>
        <label>Display name<input value={name} onChange={event => setName(event.target.value)} minLength={2} maxLength={80} required/></label>
        {message && <p className="success">{message}</p>}{error && <p className="auth-error" role="alert">{error}</p>}
        <button className="auth-submit" disabled={saving}>{saving ? 'Saving…' : 'Save profile'}</button>
      </form>
    </article>
    <article className="panel config">
      <div className="panel-head"><div><p className="eyebrow">SECURITY</p><h2>Change password</h2><p>Changing your password signs out every refresh session.</p></div></div>
      <form className="config-form" onSubmit={changePassword}>
        <label>Current password<input type="password" value={currentPassword} onChange={event => setCurrentPassword(event.target.value)} minLength={8} required/></label>
        <label>New password<input type="password" value={newPassword} onChange={event => setNewPassword(event.target.value)} minLength={8} required/></label>
        {passwordMessage && <p className="success">{passwordMessage}</p>}{passwordError && <p className="auth-error" role="alert">{passwordError}</p>}
        <button className="auth-submit" disabled={passwordSaving}>{passwordSaving ? 'Updating…' : 'Update password'}</button>
      </form>
    </article>
    <article className="panel contacts" aria-labelledby="sessions-heading">
      <div className="panel-head"><div><p className="eyebrow">ACCESS</p><h2 id="sessions-heading">Active sessions</h2><p>Revoke a session you no longer recognize.</p></div></div>
      {sessionsError && <p className="auth-error" role="alert">{sessionsError}</p>}
      {!sessionsError && sessions.length === 0 && <p className="empty">No active refresh sessions.</p>}
      {sessions.map(session => <div className="contact-row" key={session.id}>
        <div><b>{session.device_name}</b><p>Session {session.id.slice(0, 8)} · created {new Date(session.created_at).toLocaleString()} · expires {new Date(session.expires_at).toLocaleDateString()}</p></div>
        <button className="ack" disabled={revoking === session.id} onClick={() => void revoke(session.id)}>{revoking === session.id ? 'Revoking…' : 'Revoke'}</button>
      </div>)}
    </article>
    <article className="panel contacts" aria-labelledby="preferences-heading">
      <div className="panel-head"><div><p className="eyebrow">NOTIFICATIONS</p><h2 id="preferences-heading">Availability and alerts</h2><p>Choose which caregiver workflows should notify you.</p></div></div>
      {preferencesError && <p className="auth-error" role="alert">{preferencesError}</p>}
      {preferencesMessage && <p className="success" role="status">{preferencesMessage}</p>}
      {preferences && <div className="preference-list">
        <label className="preference-row"><span><b>Available for alerts</b><small>Include me in caregiver escalation workflows.</small></span><input type="checkbox" checked={preferences.available} onChange={event => void updatePreference({available: event.target.checked})}/></label>
        <label className="preference-row"><span><b>SOS notifications</b><small>Urgent patient help requests.</small></span><input type="checkbox" checked={preferences.notifySos} onChange={event => void updatePreference({notify_sos: event.target.checked})}/></label>
        <label className="preference-row"><span><b>Safety alerts</b><small>Safe-zone and expected-return alerts.</small></span><input type="checkbox" checked={preferences.notifySafetyAlerts} onChange={event => void updatePreference({notify_safety_alerts: event.target.checked})}/></label>
        <label className="preference-row"><span><b>Reminder updates</b><small>Changes to patient routines.</small></span><input type="checkbox" checked={preferences.notifyReminders} onChange={event => void updatePreference({notify_reminders: event.target.checked})}/></label>
      </div>}
    </article>
  </section>
}
