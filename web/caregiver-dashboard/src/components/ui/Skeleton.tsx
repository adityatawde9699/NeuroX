/** Animated skeleton placeholder components for loading states. */

type SkeletonProps = { className?: string; style?: React.CSSProperties }

export function SkeletonText({ short, xshort, style }: { short?: boolean; xshort?: boolean; style?: React.CSSProperties }) {
  const cls = ['skeleton', 'skeleton-text', short ? 'short' : xshort ? 'xshort' : ''].filter(Boolean).join(' ')
  return <span className={cls} style={style} aria-hidden="true" />
}

export function SkeletonTitle({ style }: SkeletonProps = {}) {
  return <span className="skeleton skeleton-title" style={style} aria-hidden="true" />
}

export function SkeletonCard({ style }: SkeletonProps = {}) {
  return <span className="skeleton skeleton-card" style={style} aria-hidden="true" />
}

export function SkeletonChart({ style }: SkeletonProps = {}) {
  return <span className="skeleton skeleton-chart" style={style} aria-hidden="true" />
}

/** Panel-level skeleton for a stat or list panel. */
export function SkeletonPanel() {
  return (
    <div aria-busy="true" aria-label="Loading…">
      <SkeletonTitle />
      <SkeletonText />
      <SkeletonCard />
      <SkeletonCard />
    </div>
  )
}
