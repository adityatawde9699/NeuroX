import { UserRound } from 'lucide-react'
import type { Patient, SafetyState } from '../types/dashboard'
import { EmptyState } from '../components/ui/AsyncState'

export function PatientProfilePage({patient, safety}: {patient: Patient | null; safety: SafetyState | null}) {
  if (!patient) return <section className="panel"><EmptyState message="Patient profile is unavailable."/></section>
  return <section className="grid"><article className="panel patient"><div className="panel-head"><div><p className="eyebrow">PATIENT PROFILE</p><h2>{patient.name}</h2><p>{patient.age} years · Preferred language: {patient.preferredLanguage}</p></div><UserRound size={28}/></div><div className="patient-body"><div className="maya-avatar">{patient.name.split(' ').map(part => part[0]).join('').slice(0, 2).toUpperCase()}</div><div className="patient-info"><div className="safe">{safety?.status ?? 'Safety status unavailable'}</div><p>{patient.email}</p><p>{safety?.contacts.length ?? 0} emergency contacts configured</p></div></div></article><article className="panel"><div className="panel-head"><div><p className="eyebrow">SAFETY SUMMARY</p><h2>Caregiver coordination</h2></div></div><p>{safety?.workflowNote ?? 'Safety information is not available yet.'}</p><p className="empty">Use Activities, Alerts, Location, and Reports to review this patient’s support information.</p></article></section>
}
