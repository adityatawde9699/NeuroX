import { FormEvent, useEffect, useState } from 'react'
import {
  AlarmClock, Bell, BellOff, CalendarClock, CalendarPlus,
  CheckCircle, Pill, Droplets, Dumbbell, Stethoscope,
} from 'lucide-react'
import { dashboardApi } from '../api/dashboardApi'
import type { Reminder } from '../types/dashboard'
import { EmptyState, ErrorState, LoadingState } from '../components/ui/AsyncState'

// ── Helpers ───────────────────────────────────────────────────────────────────
const displayTime = (value: string) =>
  new Date(value).toLocaleString([], {
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
  })

const browserTimezone = () => {
  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone
  return tz === 'Asia/Calcutta' ? 'Asia/Kolkata' : tz || 'Asia/Kolkata'
}

const REMINDER_ICONS: Record<Reminder['type'], typeof Pill> = {
  medication:  Pill,
  hydration:   Droplets,
  appointment: Stethoscope,
  activity:    CalendarClock,
  exercise:    Dumbbell,
}

const REMINDER_TONES: Record<Reminder['type'], string> = {
  medication:  'blue',
  hydration:   'mint',
  appointment: 'purple',
  activity:    'green',
  exercise:    'amber',
}

const STATUS_COLOR: Record<string, string> = {
  upcoming: 'var(--accent)',
  done:     'var(--teal)',
  missed:   'var(--red)',
  snoozed:  'var(--amber)',
}

// ── Reminder Card ─────────────────────────────────────────────────────────────
function ReminderCard({
  reminder,
  onToggle,
}: {
  reminder: Reminder
  onToggle: (r: Reminder, enabled: boolean) => void
}) {
  const Icon = REMINDER_ICONS[reminder.type] ?? Bell
  const tone = REMINDER_TONES[reminder.type] ?? 'blue'

  return (
    <div className="schedule-row">
      <div className={`reminder-icon ${tone}`} aria-hidden="true">
        <Icon size={16} />
      </div>
      <div>
        <b>{reminder.title}</b>
        <p>
          {displayTime(reminder.snoozedUntil ?? reminder.scheduledTime)}
          {' · '}
          <span style={{ textTransform: 'capitalize' }}>{reminder.type}</span>
          {' · '}
          {reminder.repeatRule ?? 'once'}
        </p>
        <small
          style={{ color: STATUS_COLOR[reminder.status] ?? 'var(--text-muted)' }}
          aria-label={`Status: ${reminder.status}`}
        >
          {reminder.status.charAt(0).toUpperCase() + reminder.status.slice(1)}
        </small>
      </div>
      <button
        className="quiet"
        onClick={() => onToggle(reminder, !reminder.enabled)}
        aria-label={`${reminder.enabled ? 'Disable' : 'Enable'} reminder: ${reminder.title}`}
        aria-pressed={reminder.enabled}
        style={{ marginLeft: 'auto', flexShrink: 0 }}
      >
        {reminder.enabled
          ? <><Bell size={14} aria-hidden="true" /> On</>
          : <><BellOff size={14} aria-hidden="true" /> Off</>}
      </button>
    </div>
  )
}

// ── Reminders Page ────────────────────────────────────────────────────────────
export function RemindersPage({ patientId }: { patientId?: string }) {
  const [reminders, setReminders] = useState<Reminder[]>([])
  const [loading, setLoading]     = useState(Boolean(patientId))
  const [type, setType]           = useState<Reminder['type']>('hydration')
  const [title, setTitle]         = useState('')
  const [scheduled, setScheduled] = useState('')
  const [repeat, setRepeat]       = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const [busy, setBusy]           = useState(false)
  const [error, setError]         = useState('')
  const [message, setMessage]     = useState('')

  const load = async () => {
    if (!patientId) { setReminders([]); return }
    setLoading(true)
    try {
      setReminders(await dashboardApi.reminders(patientId))
    } catch {
      setError('Reminders could not be loaded.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patientId])

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!patientId) return
    if (type === 'medication' && !confirmed) return
    setBusy(true)
    setError('')
    setMessage('')
    try {
      const scheduledDate = new Date(scheduled)
      if (Number.isNaN(scheduledDate.getTime())) {
        throw new Error('Choose a valid local date and time.')
      }
      await dashboardApi.createReminder({
        patient_id:    patientId,
        type,
        title:         title.trim(),
        scheduled_time: scheduledDate.toISOString(),
        repeat_rule:   repeat || null,
        timezone_name: browserTimezone(),
      })
      setTitle('')
      setScheduled('')
      setRepeat('')
      setConfirmed(false)
      setMessage('Reminder schedule saved and sent to the patient app.')
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to save this reminder.')
    } finally {
      setBusy(false)
    }
  }

  const toggleEnabled = async (reminder: Reminder, enabled: boolean) => {
    if (
      reminder.type === 'medication' &&
      !window.confirm(
        'Confirm this medication schedule change?\nNeuroX does not give dosage advice or confirm medicine was taken.'
      )
    ) return
    try {
      const updated = await dashboardApi.updateReminder(reminder.id, { enabled })
      setReminders(current => current.map(item => item.id === updated.id ? updated : item))
      setError('')
      setMessage('Reminder schedule updated.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to update this reminder.')
    }
  }

  if (!patientId) {
    return (
      <section className="panel" aria-labelledby="reminders-heading">
        <div className="panel-head">
          <div>
            <p className="eyebrow">REMINDERS</p>
            <h2 id="reminders-heading">Patient reminders</h2>
          </div>
        </div>
        <EmptyState message="Select a patient to manage reminders." />
      </section>
    )
  }

  const upcoming = reminders.filter(r => r.status === 'upcoming' && r.enabled)
  const others   = reminders.filter(r => r.status !== 'upcoming' || !r.enabled)

  return (
    <section className={`config-layout reminder-layout`} aria-label="Reminders">
      {/* Create form */}
      <article className="panel config" aria-labelledby="create-reminder-heading">
        <div className="panel-head">
          <div>
            <p className="eyebrow">PATIENT ROUTINE</p>
            <h2 id="create-reminder-heading">Create a reminder</h2>
            <p>Times use your device time zone. Schedules stay available offline in the patient app.</p>
          </div>
          <CalendarPlus size={22} style={{ color: 'var(--text-muted)' }} aria-hidden="true" />
        </div>

        {error   && <ErrorState message={error} />}
        {message && <p className="success" role="status">{message}</p>}

        <form className="config-form" onSubmit={submit} id="reminder-form">
          <label>
            Reminder type
            <select
              aria-label="Reminder type"
              value={type}
              onChange={e => {
                setType(e.target.value as Reminder['type'])
                setConfirmed(false)
              }}
            >
              <option value="hydration">Hydration</option>
              <option value="appointment">Appointment</option>
              <option value="activity">Activity</option>
              <option value="exercise">Exercise</option>
              <option value="medication">Medication schedule</option>
            </select>
          </label>

          <label>
            Title
            <input
              id="reminder-title"
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder={`e.g. ${type === 'medication' ? 'Morning tablet' : type === 'hydration' ? 'Drink water' : 'Physiotherapy session'}`}
              minLength={2}
              maxLength={100}
              required
              aria-required="true"
            />
          </label>

          <label>
            Local date and time
            <input
              id="reminder-time"
              type="datetime-local"
              value={scheduled}
              onChange={e => setScheduled(e.target.value)}
              required
              aria-required="true"
            />
          </label>

          <label>
            Repeat
            <select aria-label="Repeat frequency" value={repeat} onChange={e => setRepeat(e.target.value)}>
              <option value="">Do not repeat</option>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
            </select>
          </label>

          {type === 'medication' && (
            <>
              <div className="medication-note">
                <Pill size={14} aria-hidden="true" style={{ marginRight: 6, verticalAlign: 'middle' }} />
                Schedule coordination only: NeuroX does not provide dosage advice and "Done" does not confirm medicine was consumed.
              </div>
              <label className="confirmation config-form">
                <input
                  type="checkbox"
                  checked={confirmed}
                  onChange={e => setConfirmed(e.target.checked)}
                  id="medication-confirm"
                  aria-required="true"
                />
                I confirm this medication reminder matches the patient's agreed care schedule.
              </label>
            </>
          )}

          <button
            id="reminder-submit"
            className="auth-submit"
            disabled={busy || (type === 'medication' && !confirmed)}
            aria-busy={busy}
          >
            {busy ? 'Saving…' : 'Save reminder'}
          </button>
        </form>
      </article>

      {/* Upcoming reminders */}
      <article className="panel" aria-labelledby="upcoming-reminders-heading">
        <div className="panel-head">
          <div>
            <p className="eyebrow">UPCOMING</p>
            <h2 id="upcoming-reminders-heading">Active reminders</h2>
            <p>Enabled reminders scheduled for the patient.</p>
          </div>
          {upcoming.length > 0 && (
            <span className="tag blue" aria-label={`${upcoming.length} upcoming reminder${upcoming.length !== 1 ? 's' : ''}`}>
              {upcoming.length} upcoming
            </span>
          )}
        </div>

        {loading ? (
          <LoadingState label="Loading reminders…" />
        ) : upcoming.length === 0 ? (
          <EmptyState message="No upcoming reminders. Create one using the form." />
        ) : (
          <div className="schedule-list">
            {upcoming.map(reminder => (
              <ReminderCard key={reminder.id} reminder={reminder} onToggle={toggleEnabled} />
            ))}
          </div>
        )}
      </article>

      {/* Past / disabled reminders */}
      {others.length > 0 && (
        <article className="panel" aria-labelledby="other-reminders-heading">
          <div className="panel-head">
            <div>
              <p className="eyebrow">HISTORY</p>
              <h2 id="other-reminders-heading">Past and disabled</h2>
              <p>Completed, missed, snoozed, or disabled reminders.</p>
            </div>
          </div>
          <div className="schedule-list">
            {others.map(reminder => (
              <ReminderCard key={reminder.id} reminder={reminder} onToggle={toggleEnabled} />
            ))}
          </div>
        </article>
      )}
    </section>
  )
}
