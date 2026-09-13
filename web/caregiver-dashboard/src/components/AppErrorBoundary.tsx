import { Component } from 'react'
import type { ErrorInfo, ReactNode } from 'react'
import { AlertTriangle } from 'lucide-react'

interface State { failed: boolean; errorName?: string }

export class AppErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { failed: false }

  static getDerivedStateFromError(error: Error): State {
    return { failed: true, errorName: error?.name }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Log without exposing internal detail to the UI
    console.error('Dashboard render failed', {
      name: error.name,
      componentStack: info.componentStack,
    })
  }

  render() {
    if (this.state.failed) {
      return (
        <main className="recovery-page">
          <section className="recovery-card" role="alert" aria-labelledby="recovery-heading">
            <div className="recovery-icon" aria-hidden="true">
              <AlertTriangle size={26} />
            </div>
            <div className="brand" style={{ justifyContent: 'center', paddingBottom: '20px' }}>
              <img className="brand-image" src="/neurox-logo.svg" alt="NeuroX" />
            </div>
            <p className="eyebrow">RECOVERY</p>
            <h1 id="recovery-heading">The dashboard could not be displayed</h1>
            <p className="subtitle" style={{ marginBottom: '24px' }}>
              Your data was not changed. Reload the page to try again.
              If this persists, clear your browser cache or contact support.
            </p>
            <button
              className="auth-submit"
              onClick={() => window.location.reload()}
              style={{ width: '100%' }}
            >
              Reload dashboard
            </button>
            <p className="auth-foot" style={{ marginTop: '16px' }}>
              NeuroX provides caregiver coordination and supportive insights only.
              It does not replace clinical care or guarantee emergency response.
            </p>
          </section>
        </main>
      )
    }
    return this.props.children
  }
}
