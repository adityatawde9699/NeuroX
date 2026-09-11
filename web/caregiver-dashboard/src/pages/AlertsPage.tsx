import { useEffect, useState } from 'react'
import { AlertTriangle, ChevronDown, ChevronUp, Siren } from 'lucide-react'
import { dashboardApi, type DashboardAlert } from '../api/dashboardApi'
import { EmptyState, ErrorState, LoadingState } from '../components/ui/AsyncState'

type Filter = 'all' | 'open' | 'acknowledged'

function sortAlerts(alerts: DashboardAlert[]): DashboardAlert[] {
  return [...alerts].sort((a, b) => {
    const openA = a.status === 'open' ? 0 : 1
    const openB = b.status === 'open' ? 0 : 1
    if (openA !== openB) return openA - openB
    return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
  })
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 2)  return 'just now'
  if (m < 60) return `${m} min ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h} hour${h !== 1 ? 's' : ''} ago`
  const d = Math.floor(h / 24)
  return `${d} day${d !== 1 ? 's' : ''} ago`
}

function SeverityBadge({ severity }: { severity?: string }) {
  if (!severity) return null
  const map: Record<string, string> = { high: 'tag red', medium: 'tag orange', low: 'tag amber' }
  const labels: Record<string, string> = { high: 'High', medium: 'Medium', low: 'Low' }
  return <span className={map[severity] ?? 'tag orange'}>{labels[severity] ?? severity}</span>
}

function AlertRow({
  alert,
  onAcknowledge,
}: {
  alert: DashboardAlert
  onAcknowledge: (a: DashboardAlert) => void
}) {
  const isSos       = alert.kind === 'sos'
  const isOpen      = alert.status === 'open'
  const Icon        = isSos ? Siren : AlertTriangle

  return (
    <div
      className={`alert-row${isSos ? ' critical' : ''}`}
      aria-label={`${isSos ? 'SOS' : 'Safety alert'}: ${alert.message}`}
    >
      <Icon size={18} aria-hidden="true" />
      <div style={{ flex: 1, minWidth: 0 }}>
        <b>{isSos ? 'SOS caregiver workflow' : alert.type ?? 'Safety alert'}</b>
        <p>{alert.message}</p>
        {alert.escalatedToPriority > 1 && (
          <p className="escalation-note">
            Escalated to priority {alert.escalatedToPriority}.
            {alert.workflowNote && <> {alert.workflowNote}</>}
          </p>
        )}
        <p style={{ marginTop: 6, fontSize: '0.72rem', color: 'var(--text-muted)' }}>
          {relativeTime(alert.createdAt)} · {new Date(alert.createdAt).toLocaleString()}
        </p>
      </div>
      <div className="alert-tags">
        {isSos
          ? <span className="tag red">Critical</span>
          : <SeverityBadge severity={alert.severity} />
        }
        <span className="tag purple">P{alert.escalatedToPriority}</span>
        <span className={`tag ${isOpen ? 'orange' : 'muted'}`} style={{ textTransform: 'capitalize' }}>
          {alert.status}
        </span>
      </div>
      {isOpen && (
        <button
          className="ack"
          onClick={() => onAcknowledge(alert)}
          aria-label={`Acknowledge alert: ${alert.message}`}
        >
          Acknowledge
        </button>
      )}
    </div>
  )
}

export function AlertsPage({ patientId }: { patientId?: string }) {
  const [alerts, setAlerts]   = useState<DashboardAlert[]>([])
  const [loading, setLoading] = useState(Boolean(patientId))
  const [error, setError]     = useState('')
  const [filter, setFilter]   = useState<Filter>('all')
  const [historyOpen, setHistoryOpen] = useState(false)

  const load = async () => {
    if (!patientId) return
    setLoading(true)
    try {
      const data = await dashboardApi.alerts(patientId)
      setAlerts(sortAlerts(data))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to load alerts.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [patientId])

  const acknowledge = async (alert: DashboardAlert) => {
    if (!patientId) return
    try {
      await dashboardApi.acknowledge(patientId, alert.kind === 'sos' ? 'sos' : 'alert', alert.id)
      setAlerts(current =>
        sortAlerts(current.map(item =>
          item.id === alert.id ? { ...item, status: 'acknowledged' } : item
        ))
      )
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to acknowledge alert.')
    }
  }

  const open         = alerts.filter(a => a.status === 'open')
  const acknowledged = alerts.filter(a => a.status === 'acknowledged')
  const filtered     = filter === 'open'
    ? open
    : filter === 'acknowledged'
      ? acknowledged
      : alerts

  return (
    <section className="panel" aria-labelledby="alerts-heading">
      <div className="panel-head">
        <div>
          <p className="eyebrow">ALERTS</p>
          <h2 id="alerts-heading">Safety workflow history</h2>
          <p>Caregiver workflow events. Not emergency-service integration.</p>
        </div>
        <button className="quiet" onClick={() => void load()} aria-label="Refresh alerts">
          Refresh
        </button>
      </div>

      {loading ? (
        <LoadingState label="Loading alerts…" />
      ) : error ? (
        <ErrorState message={error} onRetry={() => void load()} />
      ) : alerts.length === 0 ? (
        <EmptyState message="No safety alerts are available." />
      ) : (
        <>
          <div className="filter-bar" role="group" aria-label="Filter alerts">
            {(['all', 'open', 'acknowledged'] as Filter[]).map(f => (
              <button
                key={f}
                className={`filter-btn${filter === f ? ' active' : ''}`}
                onClick={() => setFilter(f)}
                aria-pressed={filter === f}
              >
                {f === 'all'
                  ? `All (${alerts.length})`
                  : f === 'open'
                    ? `Open (${open.length})`
                    : `Resolved (${acknowledged.length})`}
              </button>
            ))}
          </div>

          {filtered.length === 0 ? (
            <EmptyState message={`No ${filter} alerts.`} />
          ) : (
            filtered.map(alert => (
              <AlertRow
                key={`${alert.kind}-${alert.id}`}
                alert={alert}
                onAcknowledge={acknowledge}
              />
            ))
          )}

          {filter === 'all' && acknowledged.length > 0 && (
            <button
              className="quiet"
              style={{ marginTop: 12, width: '100%', justifyContent: 'center', gap: 6 }}
              onClick={() => setHistoryOpen(o => !o)}
              aria-expanded={historyOpen}
            >
              {historyOpen ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
              {historyOpen ? 'Hide' : 'Show'} {acknowledged.length} resolved alert{acknowledged.length !== 1 ? 's' : ''}
            </button>
          )}
        </>
      )}
    </section>
  )
}