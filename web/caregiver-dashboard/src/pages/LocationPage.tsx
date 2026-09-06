import { FormEvent, useEffect, useState } from 'react'
import { LocateFixed, MapPin, Phone } from 'lucide-react'
import { dashboardApi, type LocationHistoryItem } from '../api/dashboardApi'
import type { Patient, SafetyState } from '../types/dashboard'
import { EmptyState, ErrorState, LoadingState } from '../components/ui/AsyncState'
import { ContactManager } from '../components/contacts/ContactManager'

const inputTime = (value: string | null) => value ? new Date(value).toISOString().slice(0, 16) : ''

export function LocationPage({patient, safety, reload}: {patient: Patient | null; safety: SafetyState | null; reload: () => void}) {
  const [history, setHistory] = useState<LocationHistoryItem[]>([])
  const [name, setName] = useState('Home safe zone')
  const [latitude, setLatitude] = useState('')
  const [longitude, setLongitude] = useState('')
  const [radius, setRadius] = useState(250)
  const [expected, setExpected] = useState('')
  const [note, setNote] = useState('')
  const [loading, setLoading] = useState(Boolean(patient))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (!safety) return
    setName(safety.settings.safeZoneName)
    setLatitude(String(safety.settings.safeZoneLatitude ?? ''))
    setLongitude(String(safety.settings.safeZoneLongitude ?? ''))
    setRadius(safety.settings.safeZoneRadiusM)
    setExpected(inputTime(safety.settings.expectedReturnAt))
    setNote(safety.settings.expectedReturnNote ?? '')
  }, [safety])

  useEffect(() => {
    if (!patient) return
    let active = true
    setLoading(true)
    dashboardApi.locationHistory(patient.id).then(items => { if (active) setHistory(items) }).catch(cause => { if (active) setError(cause instanceof Error ? cause.message : 'Unable to load location history.') }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [patient])

  const save = async (event: FormEvent) => {
    event.preventDefault()
    if (!patient) return
    const numericLatitude = Number(latitude)
    const numericLongitude = Number(longitude)
    if (!Number.isFinite(numericLatitude) || numericLatitude < -90 || numericLatitude > 90 || !Number.isFinite(numericLongitude) || numericLongitude < -180 || numericLongitude > 180 || radius < 50 || radius > 5000) {
      setError('Enter valid coordinates and a radius between 50 and 5000 meters.')
      return
    }
    setSaving(true); setError(''); setSaved(false)
    try {
      await dashboardApi.updateSafetySettings(patient.id, {safe_zone_name: name, safe_zone_latitude: numericLatitude, safe_zone_longitude: numericLongitude, safe_zone_radius_m: radius, expected_return_at: expected ? new Date(expected).toISOString() : null, expected_return_note: note, late_return_grace_minutes: safety?.settings.lateReturnGraceMinutes ?? 10})
      setSaved(true); reload()
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to save safety settings.') } finally { setSaving(false) }
  }

  const location = safety?.location
  return <section className="config-layout"><article className="panel config"><div className="panel-head"><div><p className="eyebrow">LOCATION</p><h2>Safety location</h2><p>{location?.label ?? 'Location not shared'} · {location?.freshness ?? 'No update available'} · {location ? `${Math.round(location.accuracyM)} m accuracy` : 'accuracy unknown'}</p></div><LocateFixed size={24}/></div><div className="map"><div className="roads a"/><div className="roads b"/><div className="zone"><span>{name}</span><MapPin fill="currentColor"/></div><div className="map-label">{location?.label ?? 'Waiting for location'}<br/><small>{location?.connectionState ?? 'not connected'} · {location?.freshness ?? 'no timestamp'}</small></div></div>{loading ? <LoadingState label="Loading location history…"/> : history.length === 0 ? <EmptyState message="No location history is available."/> : <div className="location-history">{history.slice(0, 10).map(item => <div className="contact-row" key={item.id}><div><b>{item.label}</b><p>{new Date(item.capturedAt).toLocaleString()} · {item.connectionState} · {Math.round(item.accuracyM)} m accuracy</p></div><span>{item.latitude.toFixed(4)}, {item.longitude.toFixed(4)}</span></div>)}</div>}</article><article className="panel config"><div className="panel-head"><div><p className="eyebrow">SAFE ZONE</p><h2>Caregiver configuration</h2></div></div>{error && <ErrorState message={error}/>} {saved && <p className="success">Safety settings saved.</p>}<form className="config-form" onSubmit={save}><label>Safe zone name<input value={name} onChange={event => setName(event.target.value)} required/></label><label>Latitude<input type="number" step="0.000001" value={latitude} onChange={event => setLatitude(event.target.value)} required/></label><label>Longitude<input type="number" step="0.000001" value={longitude} onChange={event => setLongitude(event.target.value)} required/></label><label>Radius in meters<input type="number" min={50} max={5000} value={radius} onChange={event => setRadius(Number(event.target.value))} required/></label><label>Expected return<input type="datetime-local" value={expected} onChange={event => setExpected(event.target.value)}/></label><label>Return note<input value={note} onChange={event => setNote(event.target.value)} maxLength={160}/></label><button className="auth-submit" disabled={saving}>{saving ? 'Saving…' : 'Save safety settings'}</button></form></article><ContactManager patient={patient} contacts={safety?.contacts ?? []} onChanged={reload}/></section>
}