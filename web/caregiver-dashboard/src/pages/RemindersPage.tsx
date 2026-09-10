import { FormEvent, useEffect, useState } from 'react'
import { dashboardApi } from '../api/dashboardApi'
import type { Reminder } from '../types/dashboard'

const displayTime = (value: string) => new Date(value).toLocaleString([], {
  month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
})
const browserTimezone = () => {
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone
  // Some Linux tzdata/browser combinations still emit this legacy alias.
  return timezone === 'Asia/Calcutta' ? 'Asia/Kolkata' : timezone || 'Asia/Kolkata'
}

export function RemindersPage({patientId}:{patientId?:string}) {
  const [reminders, setReminders] = useState<Reminder[]>([])
  const [type, setType] = useState<Reminder['type']>('hydration')
  const [title, setTitle] = useState('')
  const [scheduled, setScheduled] = useState('')
  const [repeat, setRepeat] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const load = async () => {
    if (!patientId) return setReminders([])
    setReminders(await dashboardApi.reminders(patientId))
  }
  useEffect(() => { void load().catch(() => setError('Reminders could not be loaded.')) }, [patientId])

  const submit = async (event:FormEvent) => {
    event.preventDefault()
    if (!patientId || (type === 'medication' && !confirmed)) return
    setBusy(true); setError(''); setMessage('')
    try {
      const scheduledDate = new Date(scheduled)
      if (Number.isNaN(scheduledDate.getTime())) throw new Error('Choose a valid local date and time.')
      await dashboardApi.createReminder({patient_id:patientId, type, title:title.trim(), scheduled_time:scheduledDate.toISOString(), repeat_rule:repeat || null, timezone_name:browserTimezone()})
      setTitle(''); setScheduled(''); setRepeat(''); setConfirmed(false)
      setMessage('Reminder schedule saved and sent to the patient app.')
      await load()
    } catch (err) { setError(err instanceof Error ? err.message : 'Unable to save this reminder.') }
    finally { setBusy(false) }
  }

  const setEnabled = async (reminder:Reminder, enabled:boolean) => {
    if (reminder.type === 'medication' && !window.confirm('Confirm this medication schedule change? This does not give dosage advice or confirm medicine was taken.')) return
    try {
      const updated = await dashboardApi.updateReminder(reminder.id, {enabled})
      setReminders(current => current.map(item => item.id === updated.id ? updated : item))
      setError(''); setMessage('Reminder schedule updated.')
    } catch (err) { setError(err instanceof Error ? err.message : 'Unable to update this reminder.') }
  }

  if (!patientId) return <section className="panel"><h2>Reminders</h2><p className="empty">Select a patient to manage reminders.</p></section>
  return <section className="config-layout reminder-layout">
    <article className="panel config">
      <p className="eyebrow">PATIENT ROUTINE</p><h2>Create a reminder</h2>
      <p className="subtitle">Times use your device time zone. The patient app keeps saved schedules available offline.</p>
      {error && <p className="auth-error" role="alert">{error}</p>}{message && <p className="success" role="status">{message}</p>}
      <form className="config-form" onSubmit={submit}>
        <label>Reminder type<select aria-label="Reminder type" value={type} onChange={event => { setType(event.target.value as Reminder['type']); setConfirmed(false) }}><option value="hydration">Hydration</option><option value="appointment">Appointment</option><option value="activity">Activity</option><option value="medication">Medication schedule</option></select></label>
        <label>Title<input value={title} onChange={event=>setTitle(event.target.value)} minLength={2} maxLength={100} required/></label>
        <label>Local date and time<input type="datetime-local" value={scheduled} onChange={event=>setScheduled(event.target.value)} required/></label>
        <label>Repeat<select aria-label="Repeat" value={repeat} onChange={event=>setRepeat(event.target.value)}><option value="">Do not repeat</option><option value="daily">Daily</option><option value="weekly">Weekly</option></select></label>
        {type === 'medication' && <><p className="medication-note">Schedule coordination only: NeuroX does not provide dosage advice and Done does not confirm medicine was consumed.</p><label className="confirmation"><input type="checkbox" checked={confirmed} onChange={event=>setConfirmed(event.target.checked)}/> I confirm this medication reminder matches the patient’s agreed care schedule.</label></>}
        <button className="auth-submit" disabled={busy || (type === 'medication' && !confirmed)}>{busy ? 'Saving…' : 'Save reminder'}</button>
      </form>
    </article>
    <article className="panel"><p className="eyebrow">SCHEDULED</p><h2>Patient reminders</h2>{reminders.length === 0 ? <p className="empty">No reminders scheduled.</p> : <div className="schedule-list">{reminders.map(reminder=><div className="schedule-row" key={reminder.id}><div><b>{reminder.title}</b><p>{displayTime(reminder.snoozedUntil ?? reminder.scheduledTime)} · {reminder.type} · {reminder.repeatRule ?? 'once'}</p><small>{reminder.status}</small></div><button className="quiet" onClick={()=>void setEnabled(reminder, !reminder.enabled)}>{reminder.enabled ? 'Disable' : 'Enable'}</button></div>)}</div>}</article>
  </section>
}
