import { FormEvent, useEffect, useState } from 'react'
import { dashboardApi, type ActivityReport } from '../api/dashboardApi'
import { EmptyState, ErrorState, LoadingState } from '../components/ui/AsyncState'

export function ReportsPage({patientId}: {patientId?: string}) {
  const [report, setReport] = useState<ActivityReport | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(Boolean(patientId))
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [activityId, setActivityId] = useState('')

  const load = async (event?: FormEvent) => {
    event?.preventDefault()
    if (!patientId) return
    setLoading(true)
    setError('')
    try {
      setReport(await dashboardApi.report(patientId, {from, to, activityId}))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to load the activity report.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [patientId])

  return <section className="panel" aria-labelledby="reports-heading">
    <div className="panel-head"><div><p className="eyebrow">REPORTS</p><h2 id="reports-heading">Activity report</h2><p>Supportive engagement information, not a medical assessment.</p></div></div>
    <form className="config-form" onSubmit={load}>
      <label>From<input type="datetime-local" value={from} onChange={event => setFrom(event.target.value)}/></label>
      <label>To<input type="datetime-local" value={to} onChange={event => setTo(event.target.value)}/></label>
      <label>Activity ID<input placeholder="memory-match" value={activityId} onChange={event => setActivityId(event.target.value)}/></label>
      <button className="auth-submit" disabled={loading}>{loading ? 'Loading…' : 'Apply filters'}</button>
    </form>
    {loading ? <LoadingState/> : error ? <ErrorState message={error} onRetry={() => void load()}/> : !report || report.summary.sessions === 0 ? <EmptyState message="No completed activities are available for this report."/> : <>
      <div className="stats"><div><small>Sessions</small><h2>{report.summary.sessions}</h2></div><div><small>Completion</small><h2>{Math.round(report.summary.completionRate * 100)}%</h2></div><div><small>Average accuracy</small><h2>{Math.round(report.summary.averageAccuracy * 100)}%</h2></div><div><small>Average response</small><h2>{report.summary.averageResponseTime}s</h2></div></div>
      <div className="location-history">{report.series.map((point, index) => <div className="contact-row" key={`${point.date}-${index}`}><div><b>{new Date(point.date).toLocaleString()}</b><p>Completion {Math.round(point.completionRate * 100)}% · Accuracy {Math.round(point.accuracy * 100)}% · Difficulty {point.difficulty}</p></div><span>{point.responseTime}s</span></div>)}</div>
    </>}
  </section>
}
