import { useEffect, useState } from 'react'
import { dashboardApi, type DashboardAlert } from '../api/dashboardApi'
import { EmptyState, ErrorState, LoadingState } from '../components/ui/AsyncState'

/** Sort order: open before acknowledged, then newest first within each group. */
function sortAlerts(alerts: DashboardAlert[]): DashboardAlert[] {
  return [...alerts].sort((a, b) => {
    const openA = a.status === 'open' ? 0 : 1
    const openB = b.status === 'open' ? 0 : 1
    if (openA !== openB) return openA - openB
    return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
  })
}

function SeverityBadge({ severity }: { severity?: string }) {
  if (!severity) return null
  const classes: Record<string, string> = {
    high:   'tag red',
    medium: 'tag orange',
    low:    'tag amber',
  }
  const label: Record<string, string> = {high: 'High', medium: 'Medium', low: 'Low'}
  return <span className={classes[severity] ?? 'tag orange'}>{label[severity] ?? severity}</span>
}

export function AlertsPage({ patientId }: { patientId?: string }) {
  const [alerts, setAlerts] = useState<DashboardAlert[]>([])
  const [loading, setLoading] = useState(Boolean(patientId))
  const [error, setError] = useState('')

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

  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <p className="eyebrow">ALERTS</p>
          <h2>Safety history</h2>
          <p>Caregiver workflow events, not emergency-service integration.</p>
        </div>
      </div>
      {loading ? <LoadingState /> : error ? (
        <ErrorState message={error} onRetry={() => void load()} />
      ) : alerts.length === 0 ? (
        <EmptyState message="No safety alerts are available." />
      ) : (
        <div className="location-history">
          {alerts.map(alert => (
            <div className="alert-row" key={`${alert.kind}-${alert.id}`}>
              <div>
                <b>{alert.kind === 'sos' ? 'SOS caregiver workflow' : alert.type ?? 'Safety alert'}</b>
                <p>{alert.message}</p>
                {/* Phase 7: escalation priority indicator */}
                {alert.escalatedToPriority > 1 && (
                  <p className="escalation-note">
                    Escalated to priority {alert.escalatedToPriority}.
                    {alert.workflowNote && <> {alert.workflowNote}</>}
                  </p>
                )}
              </div>
              <div className="alert-tags">
                {alert.kind === 'sos' ? <span className="tag red">Critical</span> : <SeverityBadge severity={alert.severity} />}
                <span className="tag purple">P{alert.escalatedToPriority}</span>
                <span className={`tag ${alert.status === 'open' ? 'orange' : 'muted'}`}>
                  {alert.status}
                </span>
              </div>
              {alert.status === 'open' && (
                <button className="ack" onClick={() => void acknowledge(alert)}>
                  Acknowledge
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  )
}