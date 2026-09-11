import { MapPin, Phone, ShieldCheck, UserRound } from 'lucide-react'
import type { Patient, SafetyState } from '../types/dashboard'
import { EmptyState } from '../components/ui/AsyncState'

function initials(name: string) {
  return name.split(' ').map(p => p[0]).join('').slice(0, 2).toUpperCase()
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600 }}>{label}</span>
      <span style={{ fontSize: '0.875rem', color: 'var(--text-primary)', fontWeight: 500 }}>{value}</span>
    </div>
  )
}

export function PatientProfilePage({ patient, safety }: { patient: Patient | null; safety: SafetyState | null }) {
  if (!patient) {
    return (
      <section className="panel">
        <EmptyState message="Patient profile is unavailable. Select a patient from the Patients page." />
      </section>
    )
  }

  const location = safety?.location
  const openAlerts = (safety?.alerts.length ?? 0) + (safety?.sosEvents.length ?? 0)

  return (
    <div className="grid" style={{ alignItems: 'start' }}>
      {/* Profile Card */}
      <article className="panel patient" aria-labelledby="profile-heading">
        <div className="panel-head">
          <div>
            <p className="eyebrow">PATIENT PROFILE</p>
            <h2 id="profile-heading">{patient.name}</h2>
            <p>{patient.age} years · {patient.preferredLanguage}</p>
          </div>
          <UserRound size={24} style={{ color: 'var(--text-muted)' }} aria-hidden="true" />
        </div>

        <div className="patient-body">
          <div className="maya-avatar" aria-hidden="true">{initials(patient.name)}</div>
          <div className="patient-info" style={{ flex: 1 }}>
            <div className="safe">
              <ShieldCheck size={16} aria-hidden="true" />
              {safety?.status ?? 'Safety status loading…'}
            </div>
            <p>
              <MapPin size={13} aria-hidden="true" />
              {location
                ? `${location.label} · ${location.freshness} · ±${Math.round(location.accuracyM)} m`
                : 'No location shared yet'}
            </p>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: 4 }}>
              {patient.email}
            </p>
          </div>
        </div>

        {/* Patient detail rows */}
        <div style={{ marginTop: 16 }}>
          <InfoRow label="Patient ID" value={patient.id.slice(0, 12) + '…'} />
          <InfoRow label="Preferred language" value={patient.preferredLanguage} />
          <InfoRow label="Emergency contacts" value={`${safety?.contacts.length ?? 0} configured`} />
          <InfoRow label="Open alerts" value={openAlerts > 0 ? `${openAlerts} need attention` : 'All clear'} />
          <InfoRow label="Safe zone" value={safety?.settings.safeZoneName ?? 'Not configured'} />
          <InfoRow
            label="Expected return"
            value={safety?.settings.expectedReturnAt
              ? new Date(safety.settings.expectedReturnAt).toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
              : 'Not set'}
          />
        </div>
      </article>

      {/* Caregiver coordination summary */}
      <article className="panel" aria-labelledby="coordination-heading">
        <div className="panel-head">
          <div>
            <p className="eyebrow">SAFETY SUMMARY</p>
            <h2 id="coordination-heading">Caregiver coordination</h2>
          </div>
        </div>
        <p style={{ marginBottom: 14 }}>
          {safety?.workflowNote ?? 'Safety information is loading.'}
        </p>
        <p className="empty" style={{ borderTop: '1px solid var(--border)', paddingTop: 14 }}>
          Use <strong>Activities</strong>, <strong>Alerts</strong>, <strong>Location</strong>, and{' '}
          <strong>Reports</strong> tabs to review this patient's support information.
        </p>

        {/* Emergency contacts */}
        {safety && safety.contacts.length > 0 && (
          <>
            <p className="eyebrow" style={{ marginTop: 18 }}>Emergency contacts</p>
            {safety.contacts.map(contact => (
              <div className="contact-row" key={contact.id}>
                <Phone size={16} style={{ color: 'var(--accent)' }} aria-hidden="true" />
                <div>
                  <b>{contact.name}</b>
                  <p>Priority {contact.priority} · {contact.relationship} · {contact.phone}</p>
                </div>
              </div>
            ))}
          </>
        )}
      </article>
    </div>
  )
}
