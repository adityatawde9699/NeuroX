import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { dashboardApi } from '../api/dashboardApi'
import type { Patient } from '../types/dashboard'
import { EmptyState, ErrorState, LoadingState } from '../components/ui/AsyncState'

export function PatientsPage() {
  const navigate = useNavigate()
  const query = useQuery<Patient[]>({queryKey: ['assigned-patients'], queryFn: dashboardApi.assignedPatients})
  const patients = query.data ?? []
  const message = query.error instanceof Error ? query.error.message : 'Unable to load assigned patients.'
  return <section className="panel" aria-labelledby="patients-heading"><div className="panel-head"><div><p className="eyebrow">PATIENTS</p><h2 id="patients-heading">Assigned patients</h2><p>Choose a patient to review supportive activity and safety information.</p></div></div>{query.isPending ? <LoadingState/> : query.isError ? <ErrorState message={message} onRetry={() => void query.refetch()}/> : patients.length === 0 ? <EmptyState message="No patients are assigned to this caregiver."/> : patients.map(patient => <button className="contact-row" key={patient.id} onClick={() => navigate(`/patients/${patient.id}`)}><div><b>{patient.name}</b><p>{patient.age} years · {patient.preferredLanguage}</p></div></button>)}</section>
}
