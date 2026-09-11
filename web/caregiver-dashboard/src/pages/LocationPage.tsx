import { FormEvent, useEffect, useState } from 'react'
import {
  CheckCircle, Clock, Compass, LocateFixed, MapPin,
  Navigation, Phone, Radar, ShieldCheck, Wifi, WifiOff,
} from 'lucide-react'
import { dashboardApi, type LocationHistoryItem } from '../api/dashboardApi'
import type { Patient, SafetyState } from '../types/dashboard'
import { EmptyState, ErrorState, LoadingState } from '../components/ui/AsyncState'
import { ContactManager } from '../components/contacts/ContactManager'

const inputTime = (value: string | null) =>
  value ? new Date(value).toISOString().slice(0, 16) : ''

// ── Current Location Panel ────────────────────────────────────────────────────
function CurrentLocationPanel({ safety }: { safety: SafetyState | null }) {
  const location  = safety?.location
  const isOnline  = location?.connectionState === 'online'

  return (
    <div style={{ borderTop: '1px solid var(--border)', marginTop: 16, paddingTop: 16 }}>
      <div
        className={isOnline ? 'online' : 'offline'}
        role="status"
        aria-label={`Device is ${location?.connectionState ?? 'not connected'}`}
        style={{ marginBottom: 10 }}
      >
        {isOnline
          ? <><Wifi size={14} aria-hidden="true" /> Online</>
          : <><WifiOff size={14} aria-hidden="true" /> {location?.connectionState ?? 'Not connected'}</>}
      </div>

      {location ? (
        <div style={{ display: 'grid', gap: 8 }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.85rem' }}>
            <MapPin size={14} style={{ color: 'var(--accent)', flexShrink: 0 }} aria-hidden="true" />
            <strong style={{ color: 'var(--text-primary)' }}>{location.label}</strong>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>{location.freshness}</span>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
            <Radar size={13} aria-hidden="true" />
            <span>±{Math.round(location.accuracyM)} m accuracy</span>
            <span style={{ color: 'var(--border-strong)' }}>·</span>
            <Navigation size={13} aria-hidden="true" />
            <span>{location.latitude.toFixed(5)}, {location.longitude.toFixed(5)}</span>
          </div>
        </div>
      ) : (
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          Location has not been shared by the patient app yet.
        </p>
      )}
    </div>
  )
}

// ── Location History Item ─────────────────────────────────────────────────────
function HistoryRow({ item }: { item: LocationHistoryItem }) {
  const isOnline = item.connectionState === 'online'
  return (
    <div className="contact-row">
      <div className={`dot ${isOnline ? '' : ''}`} style={{ background: isOnline ? 'var(--teal)' : 'var(--text-muted)' }} aria-hidden="true" />
      <div>
        <b>{item.label}</b>
        <p>
          {new Date(item.capturedAt).toLocaleString([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}
          {' · ±'}{Math.round(item.accuracyM)} m
          {' · '}<span style={{ textTransform: 'capitalize' }}>{item.connectionState}</span>
        </p>
      </div>
      <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', flexShrink: 0 }}>
        {item.latitude.toFixed(4)}, {item.longitude.toFixed(4)}
      </span>
    </div>
  )
}

// ── Location Page ─────────────────────────────────────────────────────────────
export function LocationPage({
  patient,
  safety,
  reload,
}: {
  patient: Patient | null
  safety: SafetyState | null
  reload: () => void
}) {
  const [history, setHistory]   = useState<LocationHistoryItem[]>([])
  const [name, setName]         = useState('Home safe zone')
  const [latitude, setLatitude] = useState('')
  const [longitude, setLongitude] = useState('')
  const [radius, setRadius]     = useState(250)
  const [expected, setExpected] = useState('')
  const [note, setNote]         = useState('')
  const [histLoading, setHistLoading] = useState(Boolean(patient))
  const [saving, setSaving]     = useState(false)
  const [error, setError]       = useState('')
  const [saved, setSaved]       = useState(false)

  // Sync form from current safety settings
  useEffect(() => {
    if (!safety) return
    setName(safety.settings.safeZoneName)
    setLatitude(String(safety.settings.safeZoneLatitude ?? ''))
    setLongitude(String(safety.settings.safeZoneLongitude ?? ''))
    setRadius(safety.settings.safeZoneRadiusM)
    setExpected(inputTime(safety.settings.expectedReturnAt))
    setNote(safety.settings.expectedReturnNote ?? '')
  }, [safety])

  // Load location history
  useEffect(() => {
    if (!patient) return
    let active = true
    setHistLoading(true)
    dashboardApi.locationHistory(patient.id)
      .then(items => { if (active) setHistory(items) })
      .catch(cause => { if (active) setError(cause instanceof Error ? cause.message : 'Unable to load location history.') })
      .finally(() => { if (active) setHistLoading(false) })
    return () => { active = false }
  }, [patient])

  const save = async (event: FormEvent) => {
    event.preventDefault()
    if (!patient) return
    const numLat = Number(latitude)
    const numLon = Number(longitude)
    if (
      !Number.isFinite(numLat) || numLat < -90  || numLat > 90 ||
      !Number.isFinite(numLon) || numLon < -180 || numLon > 180 ||
      radius < 50 || radius > 5000
    ) {
      setError('Enter valid coordinates and a radius between 50 and 5000 meters.')
      return
    }
    setSaving(true)
    setError('')
    setSaved(false)
    try {
      await dashboardApi.updateSafetySettings(patient.id, {
        safe_zone_name:             name,
        safe_zone_latitude:         numLat,
        safe_zone_longitude:        numLon,
        safe_zone_radius_m:         radius,
        expected_return_at:         expected ? new Date(expected).toISOString() : null,
        expected_return_note:       note,
        late_return_grace_minutes:  safety?.settings.lateReturnGraceMinutes ?? 10,
      })
      setSaved(true)
      reload()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to save safety settings.')
    } finally {
      setSaving(false)
    }
  }

  const location = safety?.location

  return (
    <div className="config-layout" aria-label="Location and safety settings">
      {/* Left — Current Location + History */}
      <article className="panel config" aria-labelledby="location-heading">
        <div className="panel-head">
          <div>
            <p className="eyebrow">LOCATION</p>
            <h2 id="location-heading">Safety location</h2>
            <p>
              {location
                ? `${location.label} · ${location.freshness} · ${Math.round(location.accuracyM)} m accuracy`
                : 'Location not shared yet.'}
            </p>
          </div>
          <LocateFixed size={22} style={{ color: 'var(--text-muted)' }} aria-hidden="true" />
        </div>

        {/* Illustrative map */}
        <div className="map" aria-label="Illustrative safe zone map" aria-hidden="true">
          <div className="roads a" />
          <div className="roads b" />
          <div className="zone">
            <span>{name}</span>
            <MapPin fill="currentColor" size={18} />
          </div>
          <div className="map-label">
            {location?.label ?? 'Waiting for location'}
            <small>{location?.connectionState ?? 'not connected'} · {location?.freshness ?? 'no timestamp'}</small>
          </div>
        </div>

        <CurrentLocationPanel safety={safety} />

        {/* Location History */}
        <div style={{ marginTop: 20 }}>
          <p className="eyebrow" style={{ marginBottom: 4 }}>Location history</p>
          {histLoading ? (
            <LoadingState label="Loading location history…" />
          ) : history.length === 0 ? (
            <EmptyState message="No location history is available." />
          ) : (
            <div className="location-history">
              {history.slice(0, 10).map(item => (
                <HistoryRow key={item.id} item={item} />
              ))}
              {history.length > 10 && (
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', padding: '8px 0' }}>
                  Showing 10 of {history.length} records.
                </p>
              )}
            </div>
          )}
        </div>
      </article>

      {/* Right — Safe Zone Configuration */}
      <article className="panel config" aria-labelledby="safe-zone-heading">
        <div className="panel-head">
          <div>
            <p className="eyebrow">SAFE ZONE</p>
            <h2 id="safe-zone-heading">Caregiver configuration</h2>
            <p>Define the area and expected schedule for this patient.</p>
          </div>
          <ShieldCheck size={22} style={{ color: 'var(--text-muted)' }} aria-hidden="true" />
        </div>

        {error && <ErrorState message={error} />}
        {saved && (
          <div className="success" role="status" style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
            <CheckCircle size={16} aria-hidden="true" />
            Safety settings saved.
          </div>
        )}

        <form className="config-form" onSubmit={save} id="safe-zone-form" aria-label="Safe zone settings">
          <label>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Compass size={13} aria-hidden="true" />
              Safe zone name
            </span>
            <input
              id="safe-zone-name"
              value={name}
              onChange={e => setName(e.target.value)}
              required
              aria-required="true"
            />
          </label>
          <label>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Navigation size={13} aria-hidden="true" />
              Latitude
            </span>
            <input
              id="safe-zone-lat"
              type="number"
              step="0.000001"
              value={latitude}
              onChange={e => setLatitude(e.target.value)}
              placeholder="-90 to 90"
              required
              aria-required="true"
            />
          </label>
          <label>
            Longitude
            <input
              id="safe-zone-lon"
              type="number"
              step="0.000001"
              value={longitude}
              onChange={e => setLongitude(e.target.value)}
              placeholder="-180 to 180"
              required
              aria-required="true"
            />
          </label>
          <label>
            Radius (meters)
            <input
              id="safe-zone-radius"
              type="number"
              min={50}
              max={5000}
              value={radius}
              onChange={e => setRadius(Number(e.target.value))}
              required
              aria-required="true"
            />
          </label>
          <label>
            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Clock size={13} aria-hidden="true" />
              Expected return
            </span>
            <input
              id="safe-zone-expected"
              type="datetime-local"
              value={expected}
              onChange={e => setExpected(e.target.value)}
            />
          </label>
          <label>
            Return note
            <input
              id="safe-zone-note"
              value={note}
              onChange={e => setNote(e.target.value)}
              placeholder="e.g. Visiting clinic"
              maxLength={160}
            />
          </label>

          <button
            id="safe-zone-submit"
            className="auth-submit"
            disabled={saving}
            aria-busy={saving}
          >
            {saving ? 'Saving…' : 'Save safety settings'}
          </button>
        </form>

        {/* Current settings summary */}
        {safety && (
          <div style={{ borderTop: '1px solid var(--border)', marginTop: 20, paddingTop: 16 }}>
            <p className="eyebrow" style={{ marginBottom: 8 }}>Current settings</p>
            {[
              { label: 'Zone', value: safety.settings.safeZoneName },
              { label: 'Radius', value: `${safety.settings.safeZoneRadiusM} m` },
              { label: 'Grace period', value: `${safety.settings.lateReturnGraceMinutes} min` },
            ].map(({ label, value }) => (
              <div
                key={label}
                style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border)', fontSize: '0.82rem' }}
              >
                <span style={{ color: 'var(--text-muted)' }}>{label}</span>
                <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{value}</span>
              </div>
            ))}
          </div>
        )}
      </article>

      {/* Emergency Contacts */}
      <ContactManager
        patient={patient}
        contacts={safety?.contacts ?? []}
        onChanged={reload}
      />
    </div>
  )
}