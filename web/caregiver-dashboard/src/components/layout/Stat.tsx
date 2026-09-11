import type { ReactNode } from 'react'
import { Activity, Bell, ShieldCheck, Users } from 'lucide-react'

type Props = {
  icon: ReactNode
  label: string
  value: string
  detail: string
  tone: string
}

export function Stat({ icon, label, value, detail, tone }: Props) {
  return (
    <article className="stat" aria-label={`${label}: ${value}`}>
      <div className={`stat-icon ${tone}`} aria-hidden="true">{icon}</div>
      <p>{label}</p>
      <h2>{value}</h2>
      <small>{detail}</small>
    </article>
  )
}

/** Pre-built stat grid for the dashboard overview. */
export function DashboardStats({
  patientName,
  activityCount,
  performanceLoaded,
  openAlerts,
  safetyStatus,
  locationLabel,
}: {
  patientName: string | null
  activityCount: number | null
  performanceLoaded: boolean
  openAlerts: number
  safetyStatus: string | null
  locationLabel: string | null
}) {
  return (
    <section className="stats" aria-label="Dashboard summary">
      <Stat
        icon={<Users size={20} />}
        label="Active patients"
        value={patientName ? '1' : '0'}
        detail={patientName ? `${patientName} connected` : 'No assignment'}
        tone="blue"
      />
      <Stat
        icon={<Activity size={20} />}
        label="Completed sessions"
        value={activityCount === null ? '—' : String(activityCount)}
        detail={performanceLoaded ? 'From synced activity data' : 'Waiting for activity data'}
        tone="green"
      />
      <Stat
        icon={<Bell size={20} />}
        label="Pending alerts"
        value={String(openAlerts)}
        detail={openAlerts ? 'Needs acknowledgement' : 'All clear'}
        tone="amber"
      />
      <Stat
        icon={<ShieldCheck size={20} />}
        label="Safety status"
        value={openAlerts ? 'Review' : (safetyStatus ?? 'Safe')}
        detail={locationLabel ?? 'No location yet'}
        tone="mint"
      />
    </section>
  )
}
