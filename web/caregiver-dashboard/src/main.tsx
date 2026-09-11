import { useEffect, useState } from 'react'
import {
  Activity, AlertTriangle, Bell, CalendarClock, ChevronRight,
  Clock, HeartPulse, Home, LifeBuoy, MapPin, Menu,
  MoreHorizontal, Phone, Radar, Settings, ShieldCheck,
  Siren, Users, Wifi, WifiOff,
} from 'lucide-react'
import {
  Area, AreaChart, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, useLocation, useNavigate } from 'react-router-dom'
import { dashboardApi } from './api/dashboardApi'
import { api } from './api/client'
import { SettingsPage } from './pages/SettingsPage'
import { ResetPassword, VerifyEmail } from './pages/AccountRecoveryPages'
import { storeSession } from './auth/authStorage'
import { useAuth } from './auth/useAuth'
import { useDashboardBootstrap } from './hooks/useDashboardBootstrap'
import { AppSidebar } from './layout/AppSidebar'
import { AppErrorBoundary } from './components/AppErrorBoundary'
import { PatientsPage } from './pages/PatientsPage'
import { ReportsPage } from './pages/ReportsPage'
import { ActivitiesPage } from './pages/ActivitiesPage'
import { AlertsPage } from './pages/AlertsPage'
import { LocationPage } from './pages/LocationPage'
import { PatientProfilePage } from './pages/PatientProfilePage'
import { RemindersPage } from './pages/RemindersPage'
import { SignIn } from './features/auth/SignIn'
import type {
  AuthUser, Contact, LanguageConfig, Patient,
  SafetyAlert, SafetyLocation, SafetySettings, SafetyState,
  SosEvent, TrendPoint,
} from './types/dashboard'
import './styles.css'

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: unknown) => void
          renderButton: (element: HTMLElement, config: unknown) => void
        }
      }
    }
  }
}

// ── Helpers ──────────────────────────────────────────────────────────────────
const initials = (name: string) =>
  name.split(' ').map(p => p[0]).join('').slice(0, 2).toUpperCase()

const formatReturn = (value?: string | null) =>
  value
    ? new Date(value).toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
    : 'Not set'

const alertTitle = (type: string) =>
  type.split('_').map(w => w[0].toUpperCase() + w.slice(1)).join(' ')

const browserLocation = () =>
  new Promise<{ latitude: number; longitude: number; accuracy: number }>((resolve, reject) => {
    if (!navigator.geolocation) return reject(new Error('Location is not available on this device.'))
    navigator.geolocation.getCurrentPosition(
      pos => resolve({ latitude: pos.coords.latitude, longitude: pos.coords.longitude, accuracy: pos.coords.accuracy }),
      ()  => reject(new Error('Location permission was not granted.')),
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
    )
  })

// ── Nav items ─────────────────────────────────────────────────────────────────
const nav = [
  { label: 'Overview',  path: '/overview',   icon: Home },
  { label: 'Patients',  path: '/patients',   icon: Users },
  { label: 'Activities',path: '/activities', icon: Activity },
  { label: 'Reminders', path: '/reminders',  icon: CalendarClock },
  { label: 'Alerts',    path: '/alerts',     icon: Bell },
  { label: 'Location',  path: '/location',   icon: MapPin },
  { label: 'Reports',   path: '/reports',    icon: HeartPulse },
  { label: 'Settings',  path: '/settings',   icon: Settings },
]

// ── App Root ──────────────────────────────────────────────────────────────────
function App() {
  const location   = useLocation()
  const navigate   = useNavigate()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // Resolve patient/section from URL
  const patientMatch      = location.pathname.match(/^\/patients\/([^/]+)(?:\/([^/]+))?$/)
  const selectedPatientId = patientMatch?.[1]
  const nestedSection     = patientMatch?.[2]
  const activePath        = selectedPatientId
    ? nestedSection ? `/${nestedSection}` : '/overview'
    : location.pathname
  const active = nav.find(item => item.path === activePath)?.label ?? 'Overview'

  const { user, setUser, checking, error: sessionError, signOut } = useAuth()
  const { patient, safety, trend, performanceLoaded, activityCount, patientLang, loading, error, loadSafety } =
    useDashboardBootstrap(user, selectedPatientId)

  // Special routes (no auth required)
  if (location.pathname === '/reset-password') {
    return <ResetPassword token={new URLSearchParams(location.search).get('token') ?? ''} />
  }
  if (location.pathname === '/verify-email') {
    return <VerifyEmail token={new URLSearchParams(location.search).get('token') ?? ''} />
  }

  // Session restoring
  if (checking) {
    return (
      <main style={{ display: 'grid', placeItems: 'center', minHeight: '100vh', background: 'var(--bg-base)' }}>
        <p role="status" style={{ color: 'var(--text-muted)' }}>Restoring your session…</p>
      </main>
    )
  }

  // Sign in
  if (!user) return <SignIn onAuthenticated={setUser} notice={sessionError} />

  // Patient safety screen
  if (user.role === 'PATIENT') {
    return (
      <PatientSafetyScreen
        user={user}
        patient={patient}
        safety={safety}
        reload={() => patient && loadSafety(patient.id)}
        signOut={() => void signOut()}
      />
    )
  }

  const openCount = (safety?.alerts.length ?? 0) + (safety?.sosEvents.length ?? 0)

  const navigateToSection = (path: string) => {
    const patientScoped = ['/activities', '/reminders', '/alerts', '/location', '/reports'].includes(path)
    navigate(patientScoped && selectedPatientId ? `/patients/${selectedPatientId}${path}` : path)
  }

  // Render page content
  const renderPage = () => {
    if (loading) return <p className="empty" role="status">Loading caregiver data…</p>
    if (error)   return <p className="auth-error" role="alert">{error} <button className="quiet" onClick={() => window.location.reload()}>Retry</button></p>
    if (active === 'Patients')   return <PatientsPage />
    if (active === 'Activities') return <ActivitiesPage patientId={patient?.id} />
    if (active === 'Reminders')  return <RemindersPage patientId={patient?.id} />
    if (active === 'Alerts')     return <AlertsPage patientId={patient?.id} />
    if (active === 'Reports')    return <ReportsPage patientId={patient?.id} />
    if (active === 'Settings')   return <SettingsPage user={user} onUpdated={setUser} onSignOut={signOut} />
    if (active === 'Location')   return <LocationPage patient={patient} safety={safety} reload={() => patient && loadSafety(patient.id)} />
    if (selectedPatientId && !nestedSection) return <PatientProfilePage patient={patient} safety={safety} />
    return (
      <DashboardOverview
        patient={patient}
        safety={safety}
        trend={trend}
        performanceLoaded={performanceLoaded}
        patientLang={patientLang}
        activityCount={activityCount}
        reload={() => patient && loadSafety(patient.id)}
        onViewProfile={() => patient && navigate(`/patients/${patient.id}`)}
        onNavigate={navigateToSection}
      />
    )
  }

  return (
    <div className="app-shell">
      <AppSidebar
        items={nav}
        activePath={activePath}
        openAlerts={openCount}
        userName={user.name}
        onNavigate={navigateToSection}
        onSignOut={() => void signOut()}
        mobileOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />
      {sidebarOpen && (
        <button
          className="sidebar-backdrop"
          aria-label="Close navigation"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <main>
        <header>
          <div className="header-left">
            <p className="eyebrow">
              CAREGIVER PORTAL
              <span className="live-dot" aria-hidden="true" />
              LIVE
            </p>
            <h1>Good morning, {user.name.split(' ')[0]}</h1>
            <p className="subtitle">
              Here is how your patients are doing today.
              <span className="today">
                {new Intl.DateTimeFormat([], { weekday: 'long', month: 'short', day: 'numeric' }).format(new Date())}
              </span>
            </p>
          </div>
          <div className="header-actions">
            <button
              className="icon-button"
              id="header-alerts-button"
              aria-label={`${openCount} open alert${openCount !== 1 ? 's' : ''}`}
              onClick={() => navigateToSection('/alerts')}
            >
              <Bell size={21} />
              {openCount > 0 && <em aria-hidden="true" />}
            </button>
            <button
              className="profile"
              id="header-profile-button"
              aria-label="Open profile settings"
              onClick={() => navigateToSection('/settings')}
            >
              {initials(user.name)}
            </button>
          </div>
        </header>

        {/* Stat cards */}
        <section className="stats" aria-label="Dashboard summary">
          <StatCard icon={<Users size={20} />}       label="Active patients"    value={patient ? '1' : '0'}           detail={patient ? `${patient.name} connected` : 'No assignment'}          tone="blue" />
          <StatCard icon={<Activity size={20} />}    label="Completed sessions" value={activityCount === null ? '—' : String(activityCount)} detail={performanceLoaded ? 'From synced activity data' : 'Waiting for activity data'} tone="green" />
          <StatCard icon={<Bell size={20} />}        label="Pending alerts"     value={String(openCount)}            detail={openCount ? 'Needs acknowledgement' : 'All clear'}                  tone="amber" />
          <StatCard icon={<ShieldCheck size={20} />} label="Safety status"      value={openCount ? 'Review' : 'Safe'} detail={safety?.location?.label ?? 'No location yet'}                    tone="mint" />
        </section>

        {sessionError && <p className="auth-error" role="alert">{sessionError}</p>}

        {renderPage()}

        <p className="disclaimer">
          NeuroX provides caregiver coordination and supportive insights.
          SOS workflows notify configured caregivers and do not contact government or emergency services directly.
        </p>
      </main>

      {/* Mobile FAB */}
      <button
        className="mobile-menu"
        id="mobile-menu-button"
        aria-label="Open navigation"
        onClick={() => setSidebarOpen(true)}
      >
        <Menu size={22} />
      </button>
    </div>
  )
}

// ── Stat Card ─────────────────────────────────────────────────────────────────
function StatCard({ icon, label, value, detail, tone }: {
  icon: React.ReactNode; label: string; value: string; detail: string; tone: string
}) {
  return (
    <article className="stat" aria-label={`${label}: ${value}`}>
      <div className={`stat-icon ${tone}`} aria-hidden="true">{icon}</div>
      <p>{label}</p>
      <h2>{value}</h2>
      <small>{detail}</small>
    </article>
  )
}

// ── Dashboard Overview ────────────────────────────────────────────────────────
function DashboardOverview({
  patient, safety, trend, performanceLoaded, patientLang, activityCount,
  reload, onViewProfile, onNavigate,
}: {
  patient: Patient | null
  safety: SafetyState | null
  trend: TrendPoint[]
  performanceLoaded: boolean
  patientLang: LanguageConfig | null
  activityCount: number | null
  reload: () => void
  onViewProfile: () => void
  onNavigate: (path: string) => void
}) {
  const location = safety?.location
  return (
    <>
      <section className="grid">
        {/* Patient card */}
        <article className="panel patient">
          <div className="panel-head">
            <div>
              <p className="eyebrow">YOUR PATIENT</p>
              <h2>{patient?.name ?? 'No patient selected'}</h2>
              <p>{patient ? `${patient.age} years · ${patient.preferredLanguage}` : 'Assign a patient to begin'}</p>
            </div>
            <button className="quiet" onClick={onViewProfile} aria-label="View patient profile">
              View profile <ChevronRight size={16} aria-hidden="true" />
            </button>
          </div>

          <div className="patient-body">
            <div className="maya-avatar" aria-hidden="true">
              {patient ? initials(patient.name) : 'NX'}
            </div>
            <div className="patient-info">
              <div className="safe">
                <ShieldCheck size={17} aria-hidden="true" />
                {safety?.status ?? 'Loading safety status…'}
              </div>
              <p><MapPin size={13} aria-hidden="true" /> {location ? `${location.label} · ${location.freshness}` : 'No location shared yet'}</p>
              <p><Radar size={13} aria-hidden="true" /> Accuracy {location ? `±${Math.round(location.accuracyM)} m` : 'unknown'} · {location?.connectionState ?? 'not connected'}</p>
              <LanguageBadge config={patientLang} />
            </div>
          </div>

          <div className="reminder">
            <div className="reminder-icon" aria-hidden="true"><Bell size={18} /></div>
            <div>
              <b>Expected return</b>
              <p>{formatReturn(safety?.settings.expectedReturnAt)}{safety?.settings.expectedReturnNote ? ` · ${safety.settings.expectedReturnNote}` : ''}</p>
            </div>
            <button onClick={onViewProfile} aria-label="View patient profile for return time">View</button>
          </div>
        </article>

        {/* Performance panel */}
        <PerformancePanel
          trend={trend}
          performanceLoaded={performanceLoaded}
          activityCount={activityCount}
          onViewReports={() => onNavigate('/reports')}
        />
      </section>

      <section className="lower">
        {/* Safety alerts */}
        <article className="panel alerts">
          <div className="panel-head">
            <div>
              <p className="eyebrow">NEEDS ATTENTION</p>
              <h2>Safety workflow</h2>
            </div>
            <button className="quiet" onClick={reload} aria-label="Refresh safety status">
              Refresh <ChevronRight size={16} aria-hidden="true" />
            </button>
          </div>
          {safety
            ? <AlertList patientId={patient?.id} safety={safety} reload={reload} />
            : <p className="empty" role="status">Loading alerts…</p>}
        </article>

        {/* Location panel */}
        <LocationPanel safety={safety} />
      </section>
    </>
  )
}

// ── Language Badge ────────────────────────────────────────────────────────────
function LanguageBadge({ config }: { config: LanguageConfig | null }) {
  if (!config) return null
  return (
    <div className="lang-badge">
      <span className="lang-name">{config.languageName}</span>
      <span className={`lang-pill ${config.speechSupported ? 'supported' : 'fallback'}`}>
        Speech {config.speechSupported ? 'on' : 'fallback'}
      </span>
      <span className={`lang-pill ${config.ttsSupported ? 'supported' : 'fallback'}`}>
        Voice guides {config.ttsSupported ? 'on' : 'English fallback'}
      </span>
      {config.bhashinSupported && <span className="lang-pill bhashini">BHASHINI on</span>}
      {config.ttsFallbackNote && <span className="lang-note">{config.ttsFallbackNote}</span>}
      {config.bhashinSupported && config.bhashinNote && (
        <span className="lang-note bhashini-note">{config.bhashinNote}</span>
      )}
    </div>
  )
}

// ── Performance Panel ─────────────────────────────────────────────────────────
function PerformancePanel({ trend, performanceLoaded, activityCount, onViewReports }: {
  trend: TrendPoint[]
  performanceLoaded: boolean
  activityCount: number | null
  onViewReports: () => void
}) {
  if (!performanceLoaded || trend.length === 0) {
    return (
      <article className="panel performance">
        <div className="panel-head">
          <div>
            <p className="eyebrow">ACTIVITY PERFORMANCE</p>
            <h2>Engagement trend</h2>
          </div>
        </div>
        <p className="empty">
          {performanceLoaded ? 'No completed activities yet.' : 'Activity performance is loading…'}
        </p>
      </article>
    )
  }

  const avg = Math.round(trend.reduce((sum, p) => sum + p.value, 0) / trend.length)

  return (
    <article className="panel performance">
      <div className="panel-head">
        <div>
          <p className="eyebrow">ACTIVITY PERFORMANCE</p>
          <h2>Engagement trend</h2>
          <p>Synced from completed activity sessions</p>
        </div>
        <button className="quiet" onClick={onViewReports} aria-label="View full activity report">
          Report <ChevronRight size={16} aria-hidden="true" />
        </button>
      </div>

      <div className="chart-top">
        <div>
          <strong>{avg}%</strong>
          <span>average completion · {activityCount ?? 0} sessions</span>
        </div>
        <span className="up">Difficulty levels 1–5</span>
      </div>

      <div className="chart" aria-label="Activity completion and accuracy chart" aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={trend}>
            <defs>
              <linearGradient id="fillVal" x1="0" x2="0" y1="0" y2="1">
                <stop stopColor="#5b8df0" stopOpacity="0.28" />
                <stop offset="1" stopColor="#5b8df0" stopOpacity="0" />
              </linearGradient>
            </defs>
            <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
            <Tooltip contentStyle={{ background: 'var(--bg-raised)', border: '1px solid var(--border-strong)', borderRadius: 8, fontSize: 12 }} />
            <Area type="monotone" dataKey="value"    name="Completion" stroke="#5b8df0" strokeWidth={2.5} fill="url(#fillVal)" />
            <Line type="monotone" dataKey="accuracy" name="Accuracy"   stroke="#34c9a0" strokeWidth={2}   dot={false} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="mini-chart" aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={trend}>
            <XAxis dataKey="day" hide />
            <YAxis yAxisId="response"   hide domain={[0, 'dataMax + 2']} />
            <YAxis yAxisId="difficulty" hide domain={[1, 5]} />
            <Tooltip contentStyle={{ background: 'var(--bg-raised)', border: '1px solid var(--border-strong)', borderRadius: 8, fontSize: 12 }} />
            <Line yAxisId="response"   type="monotone"  dataKey="response"   name="Response time (s)" stroke="#f5a623" strokeWidth={2} dot={false} />
            <Line yAxisId="difficulty" type="stepAfter" dataKey="difficulty" name="Difficulty"         stroke="#34c9a0" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </article>
  )
}

// ── Location Panel ────────────────────────────────────────────────────────────
function LocationPanel({ safety }: { safety: SafetyState | null }) {
  const location  = safety?.location
  const isOffline = location?.connectionState !== 'online'

  return (
    <article className="panel location">
      <div className="panel-head">
        <div>
          <p className="eyebrow">LOCATION</p>
          <h2>{location?.label ?? 'Location not shared'}</h2>
        </div>
        <span
          className={isOffline ? 'offline' : 'online'}
          role="status"
          aria-label={`Device ${location?.connectionState ?? 'not connected'}`}
        >
          {isOffline ? <WifiOff size={14} aria-hidden="true" /> : <Wifi size={14} aria-hidden="true" />}
          {location?.connectionState ?? 'Not connected'}
        </span>
      </div>
      <div className="map" aria-label="Illustrative safe zone map" aria-hidden="true">
        <div className="roads a" />
        <div className="roads b" />
        <div className="zone">
          <span>{safety?.settings.safeZoneName ?? 'Safe zone'}</span>
          <MapPin fill="currentColor" size={18} />
        </div>
        <div className="map-label">
          {location ? location.freshness : 'Waiting for location'}
          <small>Accuracy {location ? `±${Math.round(location.accuracyM)} m` : 'unknown'}</small>
        </div>
      </div>
    </article>
  )
}

// ── Alert List ────────────────────────────────────────────────────────────────
function AlertList({ patientId, safety, reload }: {
  patientId?: string; safety: SafetyState; reload: () => void
}) {
  const [error, setError] = useState('')

  const acknowledge = async (kind: 'alert' | 'sos', id: string) => {
    if (!patientId) return
    try {
      await dashboardApi.acknowledge(patientId, kind, id)
      setError('')
      reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to acknowledge this safety event.')
    }
  }

  if (!safety.alerts.length && !safety.sosEvents.length) {
    return <p className="empty">No open alerts. Location still shows freshness, accuracy, and connection state.</p>
  }

  return (
    <>
      {error && <p className="auth-error" role="alert">{error}</p>}
      {safety.sosEvents.map(item => (
        <div className="alert-row critical" key={item.id}>
          <Siren size={17} aria-hidden="true" />
          <div>
            <b>SOS caregiver workflow</b>
            <p>{item.message} · notifying {item.escalatedContact?.name ?? 'configured caregiver'}</p>
          </div>
          <div className="alert-tags">
            <span className="tag red">Critical</span>
            <span className="tag purple">P{item.escalatedToPriority}</span>
          </div>
          <button className="ack" onClick={() => void acknowledge('sos', item.id)} aria-label="Acknowledge SOS event">
            Acknowledge
          </button>
        </div>
      ))}
      {safety.alerts.map(item => (
        <div className="alert-row" key={item.id}>
          <AlertTriangle size={17} aria-hidden="true" />
          <div>
            <b>{alertTitle(item.type)}</b>
            <p>{item.message} · notifying {item.escalatedContact?.name ?? 'configured caregiver'}</p>
          </div>
          <div className="alert-tags">
            <span className={`tag ${item.severity === 'high' ? 'red' : item.severity === 'medium' ? 'orange' : 'amber'}`}>
              {item.severity.charAt(0).toUpperCase() + item.severity.slice(1)}
            </span>
            <span className="tag purple">P{item.escalatedToPriority}</span>
          </div>
          <button className="ack" onClick={() => void acknowledge('alert', item.id)} aria-label={`Acknowledge: ${alertTitle(item.type)}`}>
            Acknowledge
          </button>
        </div>
      ))}
    </>
  )
}

// ── Patient Safety Screen ─────────────────────────────────────────────────────
function PatientSafetyScreen({ user, patient, safety, reload, signOut }: {
  user: AuthUser; patient: Patient | null; safety: SafetyState | null; reload: () => void; signOut: () => void
}) {
  const [busy, setBusy]   = useState(false)
  const [error, setError] = useState('')

  const sendHelp = async () => {
    if (!patient) return
    setBusy(true)
    try {
      let location = null
      try { location = await browserLocation() } catch { setError('Location was unavailable; sending the caregiver alert without a new location.') }
      if (location) {
        await api.post(`/api/v1/patients/${patient.id}/location-updates`, {
          latitude: location.latitude, longitude: location.longitude,
          accuracy_m: location.accuracy, connection_state: 'online',
          captured_at: new Date().toISOString(),
        })
      }
      await api.post(`/api/v1/patients/${patient.id}/sos-events`, { message: 'I need help. Please check on me when you can.' })
      await reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to send the caregiver alert.')
    } finally { setBusy(false) }
  }

  const sendSos = async () => {
    if (!patient) return
    setBusy(true)
    try {
      await api.post(`/api/v1/patients/${patient.id}/sos-events`, { message: 'I need help. Please check on me.' })
      await reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to send the SOS caregiver workflow.')
    } finally { setBusy(false) }
  }

  const location = safety?.location

  return (
    <main className="patient-safety">
      <section className="patient-card" aria-labelledby="patient-safety-heading">
        <div className="patient-top">
          <div className="brand" style={{ paddingBottom: '20px' }}>
            <span className="logo" aria-hidden="true">N</span>
            <span>neuro<span>X</span></span>
          </div>
          <button className="quiet" onClick={signOut} aria-label="Sign out">Sign out</button>
        </div>

        <p className="eyebrow">PATIENT SAFETY</p>
        <h1 id="patient-safety-heading">Hello, {user.name.split(' ')[0]}</h1>
        <p className="subtitle">Your safety screen shares updates with your configured caregivers only.</p>

        {error && <p className="auth-error" role="alert">{error}</p>}

        <div className="safety-status">
          <ShieldCheck size={24} aria-hidden="true" />
          <div>
            <b>{safety?.status ?? 'Loading safety status…'}</b>
            <p>
              {location
                ? `${location.label} · ${location.freshness} · accuracy ±${Math.round(location.accuracyM)} m · ${location.connectionState}`
                : 'No location has been shared yet.'}
            </p>
          </div>
        </div>

        <div className="return-row">
          <Clock size={20} aria-hidden="true" />
          <div>
            <b>Expected return</b>
            <p>{formatReturn(safety?.settings.expectedReturnAt)}</p>
          </div>
        </div>

        <div className="patient-actions">
          <button
            id="patient-help-button"
            className="help-button"
            disabled={busy}
            onClick={() => void sendHelp()}
            aria-label="Send a help request to your caregiver"
          >
            <LifeBuoy size={24} aria-hidden="true" />
            I Need Help
          </button>
          <button
            id="patient-sos-button"
            className="sos-button"
            disabled={busy}
            onClick={() => void sendSos()}
            aria-label="Trigger SOS caregiver workflow"
          >
            <Siren size={24} aria-hidden="true" />
            SOS
          </button>
        </div>

        <p className="sos-note">
          SOS starts a NeuroX caregiver workflow. It does not directly call government or emergency services.
        </p>

        <section className="contact-list" aria-label="Emergency contacts">
          {safety?.contacts.map(contact => (
            <div className="contact-row" key={contact.id}>
              <Phone size={17} aria-hidden="true" />
              <div>
                <b>{contact.name}</b>
                <p>{contact.relationship} · {contact.phone}</p>
              </div>
            </div>
          ))}
        </section>

        <PrivacyControls />
      </section>
    </main>
  )
}

// ── Privacy Controls ──────────────────────────────────────────────────────────
function PrivacyControls() {
  const [locationSharing, setLocationSharing] = useState(false)
  const [caregivers, setCaregivers]           = useState<Array<{ id: string; name: string; email: string }>>([])
  const [message, setMessage]                 = useState('')
  const [error, setError]                     = useState('')

  const load = async () => {
    const [privacy, people] = await Promise.all([
      (await import('./api/dashboardApi')).authApi.privacy(),
      (await import('./api/dashboardApi')).authApi.caregivers(),
    ])
    setLocationSharing(privacy.locationSharingEnabled)
    setCaregivers(people)
  }

  useEffect(() => { void load().catch(() => setError('Privacy controls could not be loaded.')) }, [])

  const updateLocation = async () => {
    try {
      const next   = !locationSharing
      const result = await (await import('./api/dashboardApi')).authApi.setLocationSharing(next)
      setLocationSharing(result.enabled)
      setMessage(result.message)
      setError('')
    } catch (err) { setError(err instanceof Error ? err.message : 'Unable to update location sharing.') }
  }

  const revoke = async (id: string) => {
    try {
      await (await import('./api/dashboardApi')).authApi.revokeCaregiver(id)
      setCaregivers(current => current.filter(p => p.id !== id))
      setMessage('Caregiver access was revoked immediately.')
      setError('')
    } catch (err) { setError(err instanceof Error ? err.message : 'Unable to revoke caregiver access.') }
  }

  const exportData = async () => {
    try {
      const data = await (await import('./api/dashboardApi')).authApi.exportData()
      const url  = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }))
      const link = document.createElement('a')
      link.href     = url
      link.download = 'neurox-my-data.json'
      link.click()
      URL.revokeObjectURL(url)
      setMessage('Your data export was downloaded.')
    } catch (err) { setError(err instanceof Error ? err.message : 'Unable to export your data.') }
  }

  const requestDeletion = async () => {
    try {
      setMessage((await (await import('./api/dashboardApi')).authApi.requestDeletion()).message)
      setError('')
    } catch (err) { setError(err instanceof Error ? err.message : 'Unable to record deletion request.') }
  }

  return (
    <section className="privacy-controls" aria-labelledby="privacy-heading">
      <p className="eyebrow">PRIVACY CONTROLS</p>
      <h2 id="privacy-heading">Your choices</h2>
      <p className="subtitle">You can stop new location sharing or remove caregiver access at any time.</p>
      {error   && <p className="auth-error" role="alert">{error}</p>}
      {message && <p className="success" role="status">{message}</p>}
      <button className="quiet" onClick={() => void updateLocation()}>
        Location sharing: {locationSharing ? 'On — turn off' : 'Off — turn on'}
      </button>
      <div className="privacy-caregivers">
        <b style={{ fontSize: '0.88rem' }}>Caregivers with access</b>
        {caregivers.length
          ? caregivers.map(person => (
            <div className="contact-row" key={person.id}>
              <div><b>{person.name}</b><p>{person.email}</p></div>
              <button className="quiet" onClick={() => void revoke(person.id)}>Revoke access</button>
            </div>
          ))
          : <p>No caregiver currently has access.</p>}
      </div>
      <div className="privacy-actions">
        <button className="quiet" onClick={() => void exportData()}>Download my data</button>
        <button className="quiet" onClick={() => void requestDeletion()}>Request data deletion</button>
      </div>
    </section>
  )
}

// ── Bootstrap ─────────────────────────────────────────────────────────────────
const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false },
  },
})

createRoot(document.getElementById('root')!).render(
  <AppErrorBoundary>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </AppErrorBoundary>
)
