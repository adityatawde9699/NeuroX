import { FormEvent, ReactNode, useEffect, useState } from 'react'
import { Activity, AlertTriangle, Bell, ChevronRight, Clock, HeartPulse, Home, LifeBuoy, LocateFixed, MapPin, Menu, MoreHorizontal, Phone, Radar, Settings, ShieldCheck, Siren, Users, Wifi, WifiOff } from 'lucide-react'
import { Area, AreaChart, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { createRoot } from 'react-dom/client'
import './styles.css'

declare global { interface Window { google?: { accounts: { id: { initialize: (config: unknown) => void; renderButton: (element: HTMLElement, config: unknown) => void } } } } }

const fallbackTrend = [{day:'Mon', value:72, accuracy:78, response:8, difficulty:2},{day:'Tue',value:86,accuracy:84,response:7,difficulty:2},{day:'Wed',value:80,accuracy:81,response:6,difficulty:2},{day:'Thu',value:91,accuracy:90,response:5,difficulty:2},{day:'Fri',value:84,accuracy:86,response:5,difficulty:2},{day:'Sat',value:89,accuracy:88,response:4,difficulty:2},{day:'Sun',value:88,accuracy:91,response:4,difficulty:2}]
const nav = [{label:'Overview', icon:Home},{label:'Patients',icon:Users},{label:'Activities',icon:Activity},{label:'Alerts',icon:Bell},{label:'Location',icon:MapPin},{label:'Reports',icon:HeartPulse}]
const apiUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

type AuthUser = { id: string; name: string; email: string; role: string }
type AuthResponse = { access_token: string; refresh_token: string; user: AuthUser }
type Patient = { id: string; name: string; email: string; age: number; preferredLanguage: string }
type PerformanceData = { completion: number[]; accuracyScores: number[]; responseTimes: number[]; difficultyProgression: number[]; difficulty: number }
type LanguageConfig = { languageCode: string; languageName: string; speechSupported: boolean; ttsSupported: boolean; ttsFallbackNote: string | null; bhashinSupported: boolean; bhashinNote: string | null }
type Contact = { id: string; name: string; phone: string; relationship: string; priority: number; active: boolean }
type SafetyLocation = { id: string; latitude: number; longitude: number; accuracyM: number; connectionState: string; capturedAt: string; freshness: string; label: string }
type SafetySettings = { safeZoneName: string; safeZoneLatitude: number | null; safeZoneLongitude: number | null; safeZoneRadiusM: number; expectedReturnAt: string | null; expectedReturnNote: string | null; lateReturnGraceMinutes: number }
type SafetyAlert = { id: string; type: string; severity: string; message: string; createdAt: string; escalatedToPriority: number; escalatedContact?: Contact | null }
type SosEvent = { id: string; message: string; createdAt: string; escalatedToPriority: number; escalatedContact?: Contact | null; workflowNote: string }
type SafetyState = { status: string; location: SafetyLocation | null; settings: SafetySettings; contacts: Contact[]; alerts: SafetyAlert[]; sosEvents: SosEvent[]; workflowNote: string }

const authHeaders = () => ({Authorization: `Bearer ${localStorage.getItem('neurox-token') ?? ''}`})
const jsonHeaders = () => ({...authHeaders(), 'Content-Type': 'application/json'})
const initials = (name: string) => name.split(' ').map(part => part[0]).join('').slice(0, 2).toUpperCase()
const localInputValue = (iso: string | null) => iso ? new Date(iso).toISOString().slice(0, 16) : ''
const formatReturn = (value?: string | null) => value ? new Date(value).toLocaleString([], {month:'short', day:'numeric', hour:'numeric', minute:'2-digit'}) : 'Not set'
const alertTitle = (type:string) => type.split('_').map(word => word[0].toUpperCase() + word.slice(1)).join(' ')

function App() {
  const [active, setActive] = useState('Overview')
  const [user, setUser] = useState<AuthUser | null>(() => { const saved = localStorage.getItem('neurox-user'); return saved ? JSON.parse(saved) as AuthUser : null })
  const [patient, setPatient] = useState<Patient | null>(null)
  const [safety, setSafety] = useState<SafetyState | null>(null)
  const [trend, setTrend] = useState(fallbackTrend)
  const [performanceLoaded, setPerformanceLoaded] = useState(false)
  const [patientLang, setPatientLang] = useState<LanguageConfig | null>(null)

  const loadSafety = async (patientId: string) => {
    const response = await fetch(`${apiUrl}/patients/${patientId}/safety`, {headers: authHeaders()})
    if (!response.ok) throw new Error('Unable to load safety details.')
    setSafety(await response.json() as SafetyState)
  }

  useEffect(() => {
    if (!user) return
    const load = async () => {
      if (user.role === 'PATIENT') {
        const profile = await fetch(`${apiUrl}/patients/me`, {headers: authHeaders()}).then(r => r.json() as Promise<Patient>)
        setPatient(profile)
        await loadSafety(profile.id)
        return
      }
      const patients = await fetch(`${apiUrl}/caregivers/me/patients`, {headers: authHeaders()}).then(r => r.json() as Promise<Patient[]>)
      const assigned = patients[0]
      if (!assigned) return
      setPatient(assigned)
      await loadSafety(assigned.id)
      const perfResponse = await fetch(`${apiUrl}/patients/${assigned.id}/performance`, {headers: authHeaders()})
      if (perfResponse.ok) {
        const data = await perfResponse.json() as PerformanceData
        const points = data.completion.map((value, index) => ({day: `Session ${index + 1}`, value, accuracy: data.accuracyScores[index] ?? value, response: data.responseTimes[index] ?? 0, difficulty: data.difficultyProgression[index] ?? data.difficulty}))
        if (points.length) setTrend(points)
        setPerformanceLoaded(true)
      }
      fetch(`${apiUrl}/language-config`)
        .then(response => response.ok ? response.json() as Promise<LanguageConfig[]> : Promise.reject())
        .then(configs => { const assamese = configs.find(config => config.languageCode === 'as-IN'); if (assamese) setPatientLang(assamese) })
        .catch(() => setPatientLang(null))
    }
    load().catch(() => setPerformanceLoaded(false))
  }, [user])

  if (!user) return <SignIn onAuthenticated={setUser}/>
  if (user.role === 'PATIENT') return <PatientSafetyScreen user={user} patient={patient} safety={safety} reload={() => patient && loadSafety(patient.id)} signOut={() => signOut(setUser)}/>

  const openCount = (safety?.alerts.length ?? 0) + (safety?.sosEvents.length ?? 0)
  return <div className="app-shell">
    <aside><div className="brand"><span className="logo">N</span><span>neuro<span>X</span></span></div><nav>{nav.map(({label,icon:Icon})=><button key={label} className={active===label?'selected':''} onClick={()=>setActive(label)}><Icon size={20}/>{label}{label==='Alerts'&&openCount>0&&<i>{openCount}</i>}</button>)}</nav><div className="sidebar-bottom"><button><Settings size={20}/>Settings</button><button className="user" onClick={()=>signOut(setUser)} title="Sign out"><div className="avatar">{initials(user.name)}</div><div><b>{user.name}</b><small>Caregiver - Sign out</small></div><MoreHorizontal size={20}/></button></div></aside>
    <main><header><div><p className="eyebrow">CAREGIVER PORTAL</p><h1>Good morning, {user.name.split(' ')[0]}</h1><p className="subtitle">Here is how your family members are doing today.</p></div><div className="header-actions"><button className="icon-button"><Bell size={21}/>{openCount>0&&<em/>}</button><button className="profile">{initials(user.name)}</button></div></header>
      <section className="stats"><Stat icon={<Users/>} label="Active patients" value={patient ? '1' : '0'} detail={patient ? `${patient.name} connected` : 'No assignment'} tone="blue"/><Stat icon={<Activity/>} label="Activities today" value="8 / 10" detail="2 remaining" tone="green"/><Stat icon={<Bell/>} label="Pending alerts" value={String(openCount)} detail={openCount ? 'Needs acknowledgement' : 'All clear'} tone="amber"/><Stat icon={<ShieldCheck/>} label="Safety status" value={openCount ? 'Review' : 'Safe'} detail={safety?.location?.label ?? 'No location yet'} tone="mint"/></section>
      {active === 'Location' ? <LocationConfiguration patient={patient} safety={safety} reload={() => patient && loadSafety(patient.id)}/> : <DashboardOverview patient={patient} safety={safety} trend={trend} performanceLoaded={performanceLoaded} patientLang={patientLang} reload={() => patient && loadSafety(patient.id)}/>}
      <p className="disclaimer">NeuroX provides caregiver coordination and supportive insights. SOS workflows notify configured caregivers and do not contact government or emergency services directly.</p>
    </main><button className="mobile-menu"><Menu/></button></div>
}

function DashboardOverview({patient, safety, trend, performanceLoaded, patientLang, reload}:{patient:Patient|null;safety:SafetyState|null;trend:typeof fallbackTrend;performanceLoaded:boolean;patientLang:LanguageConfig|null;reload:()=>void}) {
  const location = safety?.location
  return <>
    <section className="grid"><article className="panel patient"><div className="panel-head"><div><p className="eyebrow">YOUR PATIENT</p><h2>{patient?.name ?? 'No patient selected'}</h2><p>{patient ? `${patient.age} years - ${patient.preferredLanguage}` : 'Assign a patient to begin'}</p></div><button className="quiet">View profile <ChevronRight size={16}/></button></div><div className="patient-body"><div className="maya-avatar">{patient ? initials(patient.name) : 'NX'}</div><div className="patient-info"><div className="safe"><ShieldCheck size={18}/> {safety?.status ?? 'Loading safety status'}</div><p><MapPin size={16}/> {location ? `${location.label} - ${location.freshness}` : 'No location shared yet'}</p><p><Radar size={16}/> Accuracy {location ? `+/- ${Math.round(location.accuracyM)} m` : 'unknown'} - {location?.connectionState ?? 'not connected'}</p><LanguageBadge config={patientLang}/></div></div><div className="reminder"><div className="reminder-icon"><Bell size={19}/></div><div><b>Expected return</b><p>{formatReturn(safety?.settings.expectedReturnAt)}{safety?.settings.expectedReturnNote ? ` - ${safety.settings.expectedReturnNote}` : ''}</p></div><button>View</button></div></article>
      <PerformancePanel trend={trend} performanceLoaded={performanceLoaded}/>
    </section>
    <section className="lower"><article className="panel alerts"><div className="panel-head"><div><p className="eyebrow">NEEDS ATTENTION</p><h2>Safety workflow</h2></div><button className="quiet" onClick={reload}>Refresh <ChevronRight size={16}/></button></div>{safety ? <AlertList patientId={patient?.id} safety={safety} reload={reload}/> : <p className="empty">Loading alerts.</p>}</article><LocationPanel safety={safety}/></section>
  </>
}

function LanguageBadge({ config }: { config: LanguageConfig | null }) {
  if (!config) return null
  return (
    <div className="lang-badge">
      <span className="lang-name">{config.languageName}</span>
      <span className={`lang-pill ${config.speechSupported ? 'supported' : 'fallback'}`}>Speech {config.speechSupported ? 'on' : 'fallback'}</span>
      <span className={`lang-pill ${config.ttsSupported ? 'supported' : 'fallback'}`}>Voice guides {config.ttsSupported ? 'on' : 'English fallback'}</span>
      {config.bhashinSupported && <span className="lang-pill bhashini">BHASHINI on</span>}
      {config.ttsFallbackNote && <span className="lang-note">{config.ttsFallbackNote}</span>}
      {config.bhashinSupported && config.bhashinNote && <span className="lang-note bhashini-note">{config.bhashinNote}</span>}
    </div>
  )
}

function PerformancePanel({trend, performanceLoaded}:{trend:typeof fallbackTrend;performanceLoaded:boolean}) {
  return <article className="panel performance"><div className="panel-head"><div><p className="eyebrow">ACTIVITY PERFORMANCE</p><h2>Engagement trend</h2><p>{performanceLoaded ? 'Synced from completed activity sessions' : 'Supportive engagement trend'}</p></div><button className="quiet">Report <ChevronRight size={16}/></button></div><div className="chart-top"><div><strong>{Math.round(trend.reduce((sum, point) => sum + point.value, 0) / trend.length)}%</strong><span>average completion</span></div><span className="up">Difficulty levels 1-5</span></div><div className="chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={trend}><defs><linearGradient id="fill" x1="0" x2="0" y1="0" y2="1"><stop stopColor="#4d73d9" stopOpacity=".26"/><stop offset="1" stopColor="#4d73d9" stopOpacity="0"/></linearGradient></defs><XAxis dataKey="day" axisLine={false} tickLine={false}/><Tooltip/><Area type="monotone" dataKey="value" name="Completion" stroke="#4168d5" strokeWidth={3} fill="url(#fill)"/><Line type="monotone" dataKey="accuracy" name="Accuracy" stroke="#218567" strokeWidth={2} dot={false}/></AreaChart></ResponsiveContainer></div><div className="mini-chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={trend}><XAxis dataKey="day" hide/><YAxis yAxisId="response" hide domain={[0, 'dataMax + 2']}/><YAxis yAxisId="difficulty" hide domain={[1, 5]}/><Tooltip/><Line yAxisId="response" type="monotone" dataKey="response" name="Response time (sec)" stroke="#e58a4e" strokeWidth={2} dot={false}/><Line yAxisId="difficulty" type="stepAfter" dataKey="difficulty" name="Difficulty" stroke="#218567" strokeWidth={2} dot={false}/></LineChart></ResponsiveContainer></div></article>
}

function LocationPanel({safety}:{safety:SafetyState|null}) {
  const location = safety?.location
  const isOffline = location?.connectionState !== 'online'
  return <article className="panel location"><div className="panel-head"><div><p className="eyebrow">LOCATION</p><h2>{location?.label ?? 'Location not shared'}</h2></div><span className={isOffline ? 'offline' : 'online'}>{isOffline ? <WifiOff size={14}/> : <Wifi size={14}/>} {location?.connectionState ?? 'Not connected'}</span></div><div className="map"><div className="roads a"/><div className="roads b"/><div className="zone"><span>{safety?.settings.safeZoneName ?? 'Safe zone'}</span><MapPin fill="currentColor"/></div><div className="map-label">{location ? `${location.freshness}` : 'Waiting for location'}<br/><small>Accuracy {location ? `+/- ${Math.round(location.accuracyM)} m` : 'unknown'}</small></div></div></article>
}

function AlertList({patientId, safety, reload}:{patientId?:string;safety:SafetyState;reload:()=>void}) {
  const acknowledge = async (kind:'alert'|'sos', id:string) => {
    if (!patientId) return
    const path = kind === 'alert' ? 'safety-alerts' : 'sos-events'
    await fetch(`${apiUrl}/patients/${patientId}/${path}/${id}/acknowledge`, {method:'POST', headers:jsonHeaders(), body:JSON.stringify({note:'Acknowledged from caregiver dashboard'})})
    reload()
  }
  if (!safety.alerts.length && !safety.sosEvents.length) return <p className="empty">No open alerts. Location still shows freshness, accuracy, and connection state.</p>
  return <>{safety.sosEvents.map(item=><div className="alert-row critical" key={item.id}><Siren size={18}/><div><b>SOS caregiver workflow</b><p>{item.message} - notifying {item.escalatedContact?.name ?? 'configured caregiver'}</p></div><span className="tag red">P{item.escalatedToPriority}</span><button className="ack" onClick={()=>acknowledge('sos', item.id)}>Acknowledge</button></div>)}{safety.alerts.map(item=><div className="alert-row" key={item.id}><AlertTriangle size={18}/><div><b>{alertTitle(item.type)}</b><p>{item.message} - notifying {item.escalatedContact?.name ?? 'configured caregiver'}</p></div><span className={`tag ${item.severity === 'high' ? 'red' : 'orange'}`}>P{item.escalatedToPriority}</span><button className="ack" onClick={()=>acknowledge('alert', item.id)}>Acknowledge</button></div>)}</>
}

function LocationConfiguration({patient, safety, reload}:{patient:Patient|null;safety:SafetyState|null;reload:()=>void}) {
  const [name, setName] = useState('Home safe zone')
  const [latitude, setLatitude] = useState('')
  const [longitude, setLongitude] = useState('')
  const [radius, setRadius] = useState(250)
  const [expected, setExpected] = useState('')
  const [note, setNote] = useState('')
  useEffect(() => { if (!safety) return; setName(safety.settings.safeZoneName); setLatitude(String(safety.settings.safeZoneLatitude ?? '')); setLongitude(String(safety.settings.safeZoneLongitude ?? '')); setRadius(safety.settings.safeZoneRadiusM); setExpected(localInputValue(safety.settings.expectedReturnAt)); setNote(safety.settings.expectedReturnNote ?? '') }, [safety])
  const save = async (event:FormEvent) => {
    event.preventDefault()
    if (!patient) return
    await fetch(`${apiUrl}/patients/${patient.id}/safety/settings`, {method:'PUT', headers:jsonHeaders(), body:JSON.stringify({safe_zone_name:name, safe_zone_latitude:latitude ? Number(latitude) : null, safe_zone_longitude:longitude ? Number(longitude) : null, safe_zone_radius_m:radius, expected_return_at: expected ? new Date(expected).toISOString() : null, expected_return_note:note, late_return_grace_minutes:10})})
    reload()
  }
  return <section className="config-layout"><article className="panel config"><div className="panel-head"><div><p className="eyebrow">SAFE ZONE</p><h2>Caregiver configuration</h2><p>Update the allowed area and expected return time for {patient?.name ?? 'this patient'}.</p></div><LocateFixed size={24}/></div><form className="config-form" onSubmit={save}><label>Safe zone name<input value={name} onChange={event=>setName(event.target.value)}/></label><label>Latitude<input type="number" step="0.000001" value={latitude} onChange={event=>setLatitude(event.target.value)}/></label><label>Longitude<input type="number" step="0.000001" value={longitude} onChange={event=>setLongitude(event.target.value)}/></label><label>Radius in meters<input type="number" min={50} max={5000} value={radius} onChange={event=>setRadius(Number(event.target.value))}/></label><label>Expected return<input type="datetime-local" value={expected} onChange={event=>setExpected(event.target.value)}/></label><label>Return note<input value={note} onChange={event=>setNote(event.target.value)} placeholder="Walk, appointment, market visit"/></label><button className="auth-submit">Save safety settings</button></form></article><LocationPanel safety={safety}/><article className="panel contacts"><div className="panel-head"><div><p className="eyebrow">ESCALATION</p><h2>Emergency contacts</h2></div></div>{safety?.contacts.map(contact=><div className="contact-row" key={contact.id}><Phone size={17}/><div><b>{contact.name}</b><p>Priority {contact.priority} - {contact.relationship} - {contact.phone}</p></div></div>)}</article></section>
}

function PatientSafetyScreen({user, patient, safety, reload, signOut}:{user:AuthUser;patient:Patient|null;safety:SafetyState|null;reload:()=>void;signOut:()=>void}) {
  const [busy, setBusy] = useState(false)
  const sendHelp = async () => {
    if (!patient) return
    setBusy(true)
    await fetch(`${apiUrl}/patients/${patient.id}/location-updates`, {method:'POST', headers:jsonHeaders(), body:JSON.stringify({latitude:26.1447, longitude:91.7364, accuracy_m:18, connection_state:'online', captured_at:new Date().toISOString()})})
    await fetch(`${apiUrl}/patients/${patient.id}/sos-events`, {method:'POST', headers:jsonHeaders(), body:JSON.stringify({message:'I need help. Please check on me when you can.'})})
    await reload()
    setBusy(false)
  }
  const sendSos = async () => {
    if (!patient) return
    setBusy(true)
    await fetch(`${apiUrl}/patients/${patient.id}/sos-events`, {method:'POST', headers:jsonHeaders(), body:JSON.stringify({message:'I need help. Please check on me.'})})
    await reload()
    setBusy(false)
  }
  const location = safety?.location
  return <main className="patient-safety"><section className="patient-card"><div className="patient-top"><div className="brand"><span className="logo">N</span><span>neuro<span>X</span></span></div><button className="quiet" onClick={signOut}>Sign out</button></div><p className="eyebrow">PATIENT SAFETY</p><h1>Hello, {user.name.split(' ')[0]}</h1><p className="subtitle">Your safety screen shares updates with your configured caregivers only.</p><div className="safety-status"><ShieldCheck size={25}/><div><b>{safety?.status ?? 'Loading safety status'}</b><p>{location ? `${location.label} - ${location.freshness} - accuracy +/- ${Math.round(location.accuracyM)} m - ${location.connectionState}` : 'No location has been shared yet.'}</p></div></div><div className="return-row"><Clock size={20}/><div><b>Expected return</b><p>{formatReturn(safety?.settings.expectedReturnAt)}</p></div></div><div className="patient-actions"><button className="help-button" disabled={busy} onClick={sendHelp}><LifeBuoy size={24}/>I Need Help</button><button className="sos-button" disabled={busy} onClick={sendSos}><Siren size={25}/>SOS</button></div><p className="sos-note">SOS starts a NeuroX caregiver workflow. It does not directly call government or emergency services.</p><section className="contact-list">{safety?.contacts.map(contact=><div className="contact-row" key={contact.id}><Phone size={18}/><div><b>{contact.name}</b><p>{contact.relationship} - {contact.phone}</p></div></div>)}</section></section></main>
}

function SignIn({onAuthenticated}:{onAuthenticated:(user:AuthUser)=>void}) {
  const [email, setEmail] = useState('anita@neurox.demo'), [password, setPassword] = useState('NeuroXDemo!2026'), [error, setError] = useState(''), [loading, setLoading] = useState(false)
  const finish = (data: AuthResponse) => { localStorage.setItem('neurox-token', data.access_token); localStorage.setItem('neurox-refresh-token', data.refresh_token); localStorage.setItem('neurox-user', JSON.stringify(data.user)); onAuthenticated(data.user) }
  const submit = async (event:FormEvent) => { event.preventDefault(); setLoading(true); setError(''); try { const response = await fetch(`${apiUrl}/auth/login`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password})}); const data = await response.json(); if(!response.ok) throw new Error(data.detail ?? 'Unable to sign in.'); finish(data) } catch (err) { setError(err instanceof Error ? err.message : 'Unable to sign in.') } finally { setLoading(false) } }
  useEffect(() => { const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID; if (!clientId) return; const script = document.createElement('script'); script.src='https://accounts.google.com/gsi/client'; script.async=true; script.onload=()=>{ window.google?.accounts.id.initialize({client_id:clientId, callback:async ({credential}:{credential:string})=>{ try { const response=await fetch(`${apiUrl}/auth/google`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({credential})}); const data=await response.json(); if(!response.ok) throw new Error(data.detail); finish(data) } catch(err) { setError(err instanceof Error ? err.message : 'Google sign-in failed.') } }}); const target=document.getElementById('google-button'); if(target) { target.textContent=''; window.google?.accounts.id.renderButton(target,{theme:'outline',size:'large',width:360,text:'continue_with'}) } }; document.head.appendChild(script); return ()=>script.remove() }, [])
  return <main className="auth-page"><section className="auth-card"><div className="brand"><span className="logo">N</span><span>neuro<span>X</span></span></div><p className="eyebrow">CAREGIVER PORTAL</p><h1>Welcome back</h1><p className="subtitle">Sign in to view supportive activity and safety information.</p><form onSubmit={submit}><label>Email<input value={email} onChange={event=>setEmail(event.target.value)} type="email" required/></label><label>Password<input value={password} onChange={event=>setPassword(event.target.value)} type="password" minLength={8} required/></label>{error&&<p className="auth-error">{error}</p>}<button className="auth-submit" disabled={loading}>{loading?'Signing in...':'Sign in'}</button></form><div className="or"><span/>or continue with<span/></div><div id="google-button" className="google-placeholder">Google sign-in appears after you set VITE_GOOGLE_CLIENT_ID.</div><p className="auth-foot">Demo caregiver: anita@neurox.demo / NeuroXDemo!2026<br/>Demo patient: maya@neurox.demo / NeuroXDemo!2026</p></section></main>
}

function Stat({icon,label,value,detail,tone}:{icon:ReactNode,label:string,value:string,detail:string,tone:string}) {return <article className="stat"><div className={`stat-icon ${tone}`}>{icon}</div><p>{label}</p><h2>{value}</h2><small>{detail}</small></article>}
function signOut(setUser:(user:AuthUser|null)=>void) { localStorage.removeItem('neurox-token'); localStorage.removeItem('neurox-refresh-token'); localStorage.removeItem('neurox-user'); setUser(null) }

export default App
createRoot(document.getElementById('root')!).render(<App />)
