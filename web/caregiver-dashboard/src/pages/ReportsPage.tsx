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
    if (from && to && new Date(from) > new Date(to)) {
      setError('Report start must precede end.')
      return
    }
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

  const downloadCsv = () => {
    if (!report) return
    const rows = [
      ['NeuroX supportive activity report — not a diagnosis'],
      [report.truncated ? 'Partial report: narrow the filters to include all matching records.' : 'Filtered synced records'],
      ['date', 'completion_rate', 'accuracy', 'response_time_seconds', 'difficulty', 'offline_created', 'policy_version'],
      ...report.series.map(point => [point.date, String(point.completionRate), String(point.accuracy), String(point.responseTime), String(point.difficulty), String(point.offlineCreated ?? 'unknown'), point.modelVersion ?? 'unknown']),
    ]
    const csv = rows.map(row => row.map(value => `"${(/^[\s]*[=+@-]/.test(value) ? "'" + value : value).split('"').join('""')}"`).join(',')).join('\n')
    const url = URL.createObjectURL(new Blob([csv], {type: 'text/csv;charset=utf-8'}))
    const link = document.createElement('a')
    link.href = url
    link.download = `neurox-supportive-activity-report-${patientId ?? 'patient'}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  return <section className="panel" aria-labelledby="reports-heading">
    <div className="panel-head"><div><p className="eyebrow">REPORTS</p><h2 id="reports-heading">Activity report</h2><p>Supportive engagement information, not a medical assessment.</p></div></div>
    <form className="config-form" onSubmit={load}>
      <label>From<input type="datetime-local" value={from} onChange={event => setFrom(event.target.value)}/></label>
      <label>To<input type="datetime-local" value={to} onChange={event => setTo(event.target.value)}/></label>
      <label>Activity ID<input placeholder="memory-match" value={activityId} onChange={event => setActivityId(event.target.value)}/></label>
      <button className="auth-submit" disabled={loading}>{loading ? 'Loading…' : 'Apply filters'}</button>
    </form>
    {loading ? <LoadingState/> : error ? <ErrorState message={error} onRetry={() => void load()}/> : !report || report.summary.sessions === 0 ? <EmptyState message="No completed activities are available for this report. Missing dates mean NeuroX has no synced completed activity for that period."/> : <>
      <div className="header-actions" aria-label="Report export options">
        <button className="quiet" onClick={downloadCsv}>Download CSV</button>
        <button className="quiet" onClick={() => window.print()}>Print / Save as PDF</button>
      </div>
      <p className="empty">This report uses synced activity records only. Offline or missing periods are not interpreted as a change in health or ability.</p>
      {report.truncated && <p role="status">Partial report: narrow the date or activity filters to view all matching records.</p>}
      {report.generatedAt && <p>Report generated: {new Date(report.generatedAt).toLocaleString()}</p>}
      <div className="stats"><div><small>Sessions</small><h2>{report.summary.sessions}</h2></div><div><small>Completion</small><h2>{Math.round(report.summary.completionRate * 100)}%</h2></div><div><small>Average accuracy</small><h2>{Math.round(report.summary.averageAccuracy * 100)}%</h2></div><div><small>Average response</small><h2>{report.summary.averageResponseTime}s</h2></div></div>
      <div className="location-history">{report.series.map((point, index) => <div className="contact-row" key={`${point.date}-${index}`}><div><b>{new Date(point.date).toLocaleString()}</b><p>Completion {Math.round(point.completionRate * 100)}% · Accuracy {Math.round(point.accuracy * 100)}% · Difficulty {point.difficulty}</p></div><span>{point.responseTime}s</span></div>)}</div>
    </>}
  </section>
}
