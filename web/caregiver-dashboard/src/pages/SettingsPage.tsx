import { FormEvent, useEffect, useState } from 'react'
import { Bell, KeyRound, LogOut, ShieldAlert, User } from 'lucide-react'
import { authApi } from '../api/dashboardApi'
import { readAccessToken, storeSession } from '../auth/authStorage'
import type { AuthUser, CaregiverPreferences, SecuritySession } from '../types/dashboard'
import { ErrorState, LoadingState } from '../components/ui/AsyncState'

// ── Profile Settings ──────────────────────────────────────────────────────────
function ProfileSettingsPanel({ user, onUpdated }: { user: AuthUser; onUpdated: (user: AuthUser) => void }) {
  const [name, setName]       = useState(user.name)
  const [message, setMessage] = useState('')
  const [error, setError]     = useState('')
  const [saving, setSaving]   = useState(false)

  const save = async (event: FormEvent) => {
    event.preventDefault()
    setSaving(true)
    setMessage('')
    setError('')
    try {
      const updated = await authApi.updateProfile(name)
      storeSession(readAccessToken() ?? '', updated)
      onUpdated(updated)
      setMessage('Profile settings saved.')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to save profile settings.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <article className="panel config" aria-labelledby="settings-heading">
      <div className="panel-head">
        <div>
          <p className="eyebrow">SETTINGS</p>
          <h2 id="settings-heading">Caregiver profile</h2>
          <p>Update the name shown in the caregiver portal.</p>
        </div>
        <User size={22} style={{ color: 'var(--text-muted)' }} aria-hidden="true" />
      </div>
      <form className="config-form" onSubmit={save}>
        <label>
          Display name
          <input
            value={name}
            onChange={event => setName(event.target.value)}
            minLength={2}
            maxLength={80}
            required
            aria-required="true"
          />
        </label>
        {message && <p className="success" role="status">{message}</p>}
        {error && <ErrorState message={error} />}
        <button className="auth-submit" disabled={saving} aria-busy={saving}>
          {saving ? 'Saving…' : 'Save profile'}
        </button>
      </form>
    </article>
  )
}

// ── Security Settings ─────────────────────────────────────────────────────────
function SecuritySettingsPanel({
  sessions,
  sessionsError,
  revoke,
  revoking
}: {
  sessions: SecuritySession[]
  sessionsError: string
  revoke: (id: string) => void
  revoking: string | null
}) {
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword]         = useState('')
  const [message, setMessage]                 = useState('')
  const [error, setError]                     = useState('')
  const [saving, setSaving]                   = useState(false)

  const changePassword = async (event: FormEvent) => {
    event.preventDefault()
    setSaving(true)
    setMessage('')
    setError('')
    try {
      await authApi.changePassword(currentPassword, newPassword)
      setCurrentPassword('')
      setNewPassword('')
      setMessage('Password updated. Other sessions have been signed out.')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to update password.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <article className="panel config">
        <div className="panel-head">
          <div>
            <p className="eyebrow">SECURITY</p>
            <h2>Change password</h2>
            <p>Changing your password signs out every refresh session.</p>
          </div>
          <KeyRound size={22} style={{ color: 'var(--text-muted)' }} aria-hidden="true" />
        </div>
        <form className="config-form" onSubmit={changePassword}>
          <label>
            Current password
            <input
              type="password"
              value={currentPassword}
              onChange={event => setCurrentPassword(event.target.value)}
              minLength={8}
              required
              aria-required="true"
            />
          </label>
          <label>
            New password
            <input
              type="password"
              value={newPassword}
              onChange={event => setNewPassword(event.target.value)}
              minLength={8}
              required
              aria-required="true"
            />
          </label>
          {message && <p className="success" role="status">{message}</p>}
          {error && <ErrorState message={error} />}
          <button className="auth-submit" disabled={saving} aria-busy={saving}>
            {saving ? 'Updating…' : 'Update password'}
          </button>
        </form>
      </article>

      <article className="panel contacts" aria-labelledby="sessions-heading">
        <div className="panel-head">
          <div>
            <p className="eyebrow">ACCESS</p>
            <h2 id="sessions-heading">Active sessions</h2>
            <p>Revoke a session you no longer recognize.</p>
          </div>
          <ShieldAlert size={22} style={{ color: 'var(--text-muted)' }} aria-hidden="true" />
        </div>
        {sessionsError && <ErrorState message={sessionsError} />}
        {!sessionsError && sessions.length === 0 && (
          <p className="empty" style={{ margin: '16px 0' }}>No active refresh sessions.</p>
        )}
        <div className="schedule-list">
          {sessions.map(session => (
            <div className="contact-row" key={session.id}>
              <div className="dot" style={{ background: 'var(--teal)' }} aria-hidden="true" />
              <div>
                <b>{session.device_name}</b>
                <p>
                  Session {session.id.slice(0, 8)} · created {new Date(session.created_at).toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}
                </p>
                <small>Expires {new Date(session.expires_at).toLocaleDateString()}</small>
              </div>
              <button
                className="ack"
                disabled={revoking === session.id}
                onClick={() => revoke(session.id)}
                aria-label={`Revoke session on ${session.device_name}`}
              >
                {revoking === session.id ? 'Revoking…' : 'Revoke'}
              </button>
            </div>
          ))}
        </div>
      </article>
    </div>
  )
}

// ── Notification Settings ─────────────────────────────────────────────────────
function NotificationSettingsPanel({
  preferences,
  updatePreference,
  error,
  message,
}: {
  preferences: CaregiverPreferences
  updatePreference: (payload: Parameters<typeof authApi.updatePreferences>[0]) => void
  error: string
  message: string
}) {
  return (
    <article className="panel contacts" aria-labelledby="preferences-heading">
      <div className="panel-head">
        <div>
          <p className="eyebrow">NOTIFICATIONS</p>
          <h2 id="preferences-heading">Availability and alerts</h2>
          <p>Choose which caregiver workflows should notify you.</p>
        </div>
        <Bell size={22} style={{ color: 'var(--text-muted)' }} aria-hidden="true" />
      </div>
      
      {error && <ErrorState message={error} />}
      {message && <p className="success" role="status" style={{ marginBottom: 16 }}>{message}</p>}
      
      <div className="preference-list">
        <label className="preference-row">
          <span>
            <b>Available for alerts</b>
            <small>Include me in caregiver escalation workflows.</small>
          </span>
          <input
            type="checkbox"
            checked={preferences.available}
            onChange={event => updatePreference({ available: event.target.checked })}
          />
        </label>
        <label className="preference-row">
          <span>
            <b>SOS notifications</b>
            <small>Urgent patient help requests.</small>
          </span>
          <input
            type="checkbox"
            checked={preferences.notifySos}
            onChange={event => updatePreference({ notify_sos: event.target.checked })}
          />
        </label>
        <label className="preference-row">
          <span>
            <b>Safety alerts</b>
            <small>Safe-zone and expected-return alerts.</small>
          </span>
          <input
            type="checkbox"
            checked={preferences.notifySafetyAlerts}
            onChange={event => updatePreference({ notify_safety_alerts: event.target.checked })}
          />
        </label>
        <label className="preference-row">
          <span>
            <b>Reminder updates</b>
            <small>Changes to patient routines.</small>
          </span>
          <input
            type="checkbox"
            checked={preferences.notifyReminders}
            onChange={event => updatePreference({ notify_reminders: event.target.checked })}
          />
        </label>
      </div>
    </article>
  )
}

// ── Settings Page ─────────────────────────────────────────────────────────────
export function SettingsPage({
  user,
  onUpdated,
  onSignOut,
}: {
  user: AuthUser
  onUpdated: (user: AuthUser) => void
  onSignOut: () => void
}) {
  const [sessions, setSessions] = useState<SecuritySession[]>([])
  const [sessionsError, setSessionsError] = useState('')
  const [revoking, setRevoking] = useState<string | null>(null)
  const [preferences, setPreferences] = useState<CaregiverPreferences | null>(null)
  const [preferencesMessage, setPreferencesMessage] = useState('')
  const [preferencesError, setPreferencesError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    Promise.all([
      authApi.sessions().catch(err => {
        if (active) setSessionsError(err instanceof Error ? err.message : 'Unable to load active sessions.')
        return []
      }),
      authApi.preferences().catch(err => {
        if (active) setPreferencesError(err instanceof Error ? err.message : 'Unable to load notification preferences.')
        return null
      })
    ]).then(([sess, prefs]) => {
      if (active) {
        setSessions(sess)
        setPreferences(prefs)
        setLoading(false)
      }
    })
    return () => { active = false }
  }, [])

  const revoke = async (id: string) => {
    setRevoking(id)
    setSessionsError('')
    try {
      await authApi.revokeSession(id)
      setSessions(current => current.filter(session => session.id !== id))
    } catch (cause) {
      setSessionsError(cause instanceof Error ? cause.message : 'Unable to revoke the session.')
    } finally {
      setRevoking(null)
    }
  }

  const updatePreference = async (payload: Parameters<typeof authApi.updatePreferences>[0]) => {
    setPreferencesMessage('')
    setPreferencesError('')
    try {
      setPreferences(await authApi.updatePreferences(payload))
      setPreferencesMessage('Availability and notification preferences saved.')
    } catch (cause) {
      setPreferencesError(cause instanceof Error ? cause.message : 'Unable to save notification preferences.')
    }
  }

  if (loading) {
    return (
      <section className="config-layout">
        <LoadingState label="Loading settings..." />
      </section>
    )
  }

  return (
    <section className="config-layout" aria-label="Account Settings">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        <ProfileSettingsPanel user={user} onUpdated={onUpdated} />
        {preferences && (
          <NotificationSettingsPanel
            preferences={preferences}
            updatePreference={updatePreference}
            error={preferencesError}
            message={preferencesMessage}
          />
        )}
        <div style={{ marginTop: 'auto', paddingTop: 32 }}>
           <button className="auth-toggle" onClick={onSignOut} style={{ color: 'var(--red)', display: 'flex', alignItems: 'center', gap: 8 }}>
             <LogOut size={16} aria-hidden="true" />
             Sign out securely
           </button>
        </div>
      </div>
      <SecuritySettingsPanel
        sessions={sessions}
        sessionsError={sessionsError}
        revoke={revoke}
        revoking={revoking}
      />
    </section>
  )
}
