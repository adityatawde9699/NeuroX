import { useEffect, useState } from 'react'
import { dashboardApi, type DashboardAlert } from '../api/dashboardApi'
import { EmptyState, ErrorState, LoadingState } from '../components/ui/AsyncState'

export function AlertsPage({patientId}: {patientId?: string}) {
  const [alerts, setAlerts] = useState<DashboardAlert[]>([])
  const [loading, setLoading] = useState(Boolean(patientId))
  const [error, setError] = useState('')
  const load = async () => { if (!patientId) return; setLoading(true); try { setAlerts(await dashboardApi.alerts(patientId)) } catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to load alerts.') } finally { setLoading(false) } }
  useEffect(() => { void load() }, [patientId])
  const acknowledge = async (alert: DashboardAlert) => { if (!patientId) return; try { await dashboardApi.acknowledge(patientId, alert.kind === 'sos' ? 'sos' : 'alert', alert.id); setAlerts(current => current.map(item => item.id === alert.id ? {...item, status: 'acknowledged'} : item)) } catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to acknowledge alert.') } }
  return <section className="panel"><div className="panel-head"><div><p className="eyebrow">ALERTS</p><h2>Safety history</h2><p>Caregiver workflow events, not emergency-service integration.</p></div></div>{loading ? <LoadingState/> : error ? <ErrorState message={error} onRetry={() => void load()}/> : alerts.length === 0 ? <EmptyState message="No safety alerts are available."/> : alerts.map(alert => <div className="alert-row" key={`${alert.kind}-${alert.id}`}><div><b>{alert.kind === 'sos' ? 'SOS caregiver workflow' : alert.type ?? 'Safety alert'}</b><p>{alert.message}</p></div><span className="tag orange">{alert.status}</span>{alert.status === 'open' && <button className="ack" onClick={() => void acknowledge(alert)}>Acknowledge</button>}</div>)}</section>
}