import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { dashboardApi } from '../api/dashboardApi'
import type { Patient } from '../types/dashboard'
import { EmptyState, ErrorState, LoadingState } from '../components/ui/AsyncState'

export function PatientsPage() {
  const [patients, setPatients] = useState<Patient[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const load = async () => { setLoading(true); setError(''); try { setPatients(await dashboardApi.assignedPatients()) } catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to load assigned patients.') } finally { setLoading(false) } }
  useEffect(() => { void load() }, [])
  return <section className="panel" aria-labelledby="patients-heading"><div className="panel-head"><div><p className="eyebrow">PATIENTS</p><h2 id="patients-heading">Assigned patients</h2><p>Choose a patient to review supportive activity and safety information.</p></div></div>{loading ? <LoadingState/> : error ? <ErrorState message={error} onRetry={() => void load()}/> : patients.length === 0 ? <EmptyState message="No patients are assigned to this caregiver."/> : patients.map(patient => <button className="contact-row" key={patient.id} onClick={() => navigate(`/patients/${patient.id}`)}><div><b>{patient.name}</b><p>{patient.age} years · {patient.preferredLanguage}</p></div></button>)}</section>
}