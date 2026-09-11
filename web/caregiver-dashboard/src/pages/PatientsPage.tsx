import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { ChevronRight, ShieldCheck } from 'lucide-react'
import { dashboardApi } from '../api/dashboardApi'
import type { Patient } from '../types/dashboard'
import { EmptyState, ErrorState, LoadingState } from '../components/ui/AsyncState'

function initials(name: string) {
  return name.split(' ').map(p => p[0]).join('').slice(0, 2).toUpperCase()
}

function PatientCard({ patient, onClick }: { patient: Patient; onClick: () => void }) {
  return (
    <button className="patient-card-item" onClick={onClick} aria-label={`View patient ${patient.name}`}>
      <div className="patient-card-avatar" aria-hidden="true">{initials(patient.name)}</div>
      <div className="patient-card-info">
        <h3>{patient.name}</h3>
        <p>{patient.age} years · {patient.preferredLanguage}</p>
        <p>
          <ShieldCheck size={12} style={{ marginRight: 4 }} />
          <span className="patient-status-safe">Active patient</span>
        </p>
      </div>
      <ChevronRight size={18} style={{ color: 'var(--text-muted)', flexShrink: 0 }} aria-hidden="true" />
    </button>
  )
}

export function PatientsPage() {
  const navigate = useNavigate()
  const query = useQuery<Patient[]>({
    queryKey: ['assigned-patients'],
    queryFn: dashboardApi.assignedPatients,
  })

  const patients = query.data ?? []
  const errorMessage = query.error instanceof Error
    ? query.error.message
    : 'Unable to load assigned patients.'

  return (
    <section className="panel" aria-labelledby="patients-heading">
      <div className="panel-head">
        <div>
          <p className="eyebrow">PATIENTS</p>
          <h2 id="patients-heading">Assigned patients</h2>
          <p>Choose a patient to review supportive activity and safety information.</p>
        </div>
      </div>

      {query.isPending ? (
        <LoadingState label="Loading patients…" />
      ) : query.isError ? (
        <ErrorState message={errorMessage} onRetry={() => void query.refetch()} />
      ) : patients.length === 0 ? (
        <EmptyState message="No patients are assigned to this caregiver account. Ask your administrator to assign a patient." />
      ) : (
        <div style={{ marginTop: 8 }}>
          {patients.map(patient => (
            <PatientCard
              key={patient.id}
              patient={patient}
              onClick={() => navigate(`/patients/${patient.id}`)}
            />
          ))}
        </div>
      )}
    </section>
  )
}
