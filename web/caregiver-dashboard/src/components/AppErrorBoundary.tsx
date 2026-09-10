import { Component } from 'react'
import type { ErrorInfo, ReactNode } from 'react'

export class AppErrorBoundary extends Component<{children: ReactNode}, {failed: boolean}> {
  state = {failed: false}

  static getDerivedStateFromError() { return {failed: true} }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Dashboard render failed', {name: error.name, componentStack: info.componentStack})
  }

  render() {
    if (this.state.failed) return <main className="auth-page"><section className="auth-card" role="alert"><p className="eyebrow">RECOVERY</p><h1>The dashboard could not be displayed</h1><p className="subtitle">Your data was not changed. Reload the page to try again.</p><button className="auth-submit" onClick={() => window.location.reload()}>Reload dashboard</button></section></main>
    return this.props.children
  }
}
