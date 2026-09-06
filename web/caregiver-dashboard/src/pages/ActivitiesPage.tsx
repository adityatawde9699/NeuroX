import { useEffect, useState } from 'react'
import { dashboardApi, type ActivityHistory } from '../api/dashboardApi'
import { EmptyState, ErrorState, LoadingState } from '../components/ui/AsyncState'

export function ActivitiesPage({patientId}: {patientId?: string}) {
  const [items, setItems] = useState<ActivityHistory[]>([])
  const [loading, setLoading] = useState(Boolean(patientId))
  const [error, setError] = useState('')
  useEffect(() => { if (!patientId) { setLoading(false); return } let active = true; dashboardApi.history(patientId).then(value => { if (active) setItems(value) }).catch(cause => { if (active) setError(cause instanceof Error ? cause.message : 'Unable to load activity history.') }).finally(() => { if (active) setLoading(false) }); return () => { active = false } }, [patientId])
  return <section className="panel"><div className="panel-head"><div><p className="eyebrow">ACTIVITIES</p><h2>Activity history</h2><p>Supportive engagement records for the selected patient.</p></div></div>{loading ? <LoadingState/> : error ? <ErrorState message={error}/> : items.length === 0 ? <EmptyState message="No completed activities are available yet."/> : items.map(item => <div className="contact-row" key={item.id}><div><b>{item.activityId}</b><p>{new Date(item.startedAt).toLocaleString()} · {item.status} · level {item.difficulty}</p></div><strong>{item.accuracy === null ? '-' : `${Math.round(item.accuracy * 100)}%`}</strong></div>)}</section>
}