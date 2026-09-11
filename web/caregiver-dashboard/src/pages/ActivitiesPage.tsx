import { useEffect, useState } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { dashboardApi, type ActivityHistory } from '../api/dashboardApi'
import { EmptyState, ErrorState, LoadingState } from '../components/ui/AsyncState'

const ACTIVITY_LABELS: Record<string, string> = {
  'memory-match':         'Memory Match',
  'object-recall':        'Object Recall',
  'pattern-completion':   'Pattern Completion',
  'sequence-recall':      'Sequence Recall',
  'daily-routine-recall': 'Daily Routine Recall',
  'story-recall':         'Story Recall',
}

function activityName(id: string): string {
  return ACTIVITY_LABELS[id] ?? id.split('-').map(w => w[0].toUpperCase() + w.slice(1)).join(' ')
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 2)  return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

function DifficultyBadge({ level }: { level: number }) {
  const clamped = Math.max(1, Math.min(5, level)) as 1|2|3|4|5
  const label = ['Easy', 'Moderate', 'Medium', 'Challenging', 'Hard'][clamped - 1]
  return (
    <span className={`badge badge-difficulty-${clamped}`} aria-label={`Difficulty: ${label}`}>
      Lv {clamped} · {label}
    </span>
  )
}

function ActivityCard({ item }: { item: ActivityHistory }) {
  const accuracy     = item.accuracy !== null ? Math.round(item.accuracy * 100) : null
  const completion   = item.status === 'completed' ? 100 : item.status === 'abandoned' ? 0 : 50
  const responseTime = item.responseTime !== null ? `${item.responseTime.toFixed(1)}s` : null

  return (
    <div className="activity-card" aria-label={`Activity: ${activityName(item.activityId)}`}>
      <div className="activity-meta">
        <span className="activity-title">{activityName(item.activityId)}</span>
        <DifficultyBadge level={item.difficulty} />
        <span
          className={`badge ${item.status === 'completed' ? 'badge-difficulty-1' : item.status === 'abandoned' ? 'badge-difficulty-5' : 'badge-difficulty-3'}`}
          style={{ textTransform: 'capitalize' }}
        >
          {item.status}
        </span>
        <span className="activity-time">{relativeTime(item.startedAt)}</span>
      </div>

      <div className="completion-bar-wrap">
        <div className="completion-bar-bg" aria-label={`Session completion ${completion}%`}>
          <div
            className="completion-bar-fill"
            style={{ width: `${completion}%` }}
            role="progressbar"
            aria-valuenow={completion}
            aria-valuemin={0}
            aria-valuemax={100}
          />
        </div>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', width: 36, textAlign: 'right', flexShrink: 0 }}>
          {completion}%
        </span>
      </div>

      <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
        <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
          Accuracy: <strong style={{ color: accuracy !== null && accuracy >= 70 ? 'var(--teal)' : 'var(--amber)' }}>
            {accuracy !== null ? `${accuracy}%` : '—'}
          </strong>
        </span>
        {responseTime && (
          <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
            Response: <strong style={{ color: 'var(--text-primary)' }}>{responseTime}</strong>
          </span>
        )}
        <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
          Attempts: <strong style={{ color: 'var(--text-primary)' }}>{item.attempts}</strong>
        </span>
        <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
          {new Date(item.startedAt).toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}
        </span>
      </div>
    </div>
  )
}

const PAGE_SIZE = 10

export function ActivitiesPage({ patientId }: { patientId?: string }) {
  const [items, setItems]   = useState<ActivityHistory[]>([])
  const [loading, setLoading] = useState(Boolean(patientId))
  const [error, setError]   = useState('')
  const [page, setPage]     = useState(0)

  useEffect(() => {
    if (!patientId) { setLoading(false); return }
    setPage(0)
    let active = true
    setLoading(true)
    dashboardApi.history(patientId)
      .then(value => { if (active) setItems(value) })
      .catch(cause => { if (active) setError(cause instanceof Error ? cause.message : 'Unable to load activity history.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [patientId])

  const totalPages = Math.ceil(items.length / PAGE_SIZE)
  const pageItems  = items.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  return (
    <section className="panel" aria-labelledby="activities-heading">
      <div className="panel-head">
        <div>
          <p className="eyebrow">ACTIVITIES</p>
          <h2 id="activities-heading">Activity history</h2>
          <p>Supportive engagement records — not a medical assessment.</p>
        </div>
        {items.length > 0 && (
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            {items.length} session{items.length !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {loading ? (
        <LoadingState label="Loading activity history…" />
      ) : error ? (
        <ErrorState message={error} />
      ) : items.length === 0 ? (
        <EmptyState message="No completed activities are available yet. Synced sessions will appear here." />
      ) : (
        <>
          {pageItems.map(item => <ActivityCard key={item.id} item={item} />)}

          {totalPages > 1 && (
            <nav className="pagination" aria-label="Activity history pages">
              <button
                className="page-btn"
                disabled={page === 0}
                onClick={() => setPage(p => p - 1)}
                aria-label="Previous page"
              >
                <ChevronLeft size={16} />
              </button>
              <span className="page-info">Page {page + 1} of {totalPages}</span>
              <button
                className="page-btn"
                disabled={page >= totalPages - 1}
                onClick={() => setPage(p => p + 1)}
                aria-label="Next page"
              >
                <ChevronRight size={16} />
              </button>
            </nav>
          )}
        </>
      )}
    </section>
  )
}