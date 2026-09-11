import { SkeletonPanel } from './Skeleton'

export function LoadingState({ label = 'Loading data…' }: { label?: string }) {
  return (
    <div role="status" aria-label={label}>
      <SkeletonPanel />
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="auth-error" role="alert">
      <span style={{ flex: 1 }}>{message}</span>
      {onRetry && (
        <button className="quiet" onClick={onRetry} style={{ marginLeft: 8, flexShrink: 0 }}>
          Retry
        </button>
      )}
    </div>
  )
}

export function EmptyState({ message }: { message: string }) {
  return <p className="empty">{message}</p>
}