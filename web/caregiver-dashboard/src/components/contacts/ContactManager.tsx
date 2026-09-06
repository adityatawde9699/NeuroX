import { FormEvent, useState } from 'react'
import { Phone, UserPlus } from 'lucide-react'
import { dashboardApi } from '../../api/dashboardApi'
import type { Contact, Patient } from '../../types/dashboard'
import { EmptyState, ErrorState } from '../ui/AsyncState'

type Draft = {name: string; phone: string; relationship: string; priority: number}
const emptyDraft: Draft = {name: '', phone: '', relationship: '', priority: 1}

export function ContactManager({patient, contacts, onChanged}: {patient: Patient | null; contacts: Contact[]; onChanged: () => void}) {
  const [draft, setDraft] = useState<Draft>(emptyDraft)
  const [editing, setEditing] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  if (!patient) return <EmptyState message="Select a patient before managing contacts."/>
  const submit = async (event: FormEvent) => {
    event.preventDefault(); setSaving(true); setError('')
    try {
      if (editing) await dashboardApi.updateContact(patient.id, editing, draft)
      else await dashboardApi.createContact(patient.id, draft)
      setDraft(emptyDraft); setEditing(null); onChanged()
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to save emergency contact.') } finally { setSaving(false) }
  }
  const edit = (contact: Contact) => { setEditing(contact.id); setDraft({name: contact.name, phone: contact.phone, relationship: contact.relationship, priority: contact.priority}); setError('') }
  const deactivate = async (contact: Contact) => { setSaving(true); setError(''); try { await dashboardApi.updateContact(patient.id, contact.id, {active: false}); onChanged() } catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to deactivate emergency contact.') } finally { setSaving(false) } }
  return <article className="panel contacts"><div className="panel-head"><div><p className="eyebrow">EMERGENCY CONTACTS</p><h2>Caregiver escalation contacts</h2></div><UserPlus size={22}/></div>{error && <ErrorState message={error}/>} {contacts.length === 0 ? <EmptyState message="No emergency contacts configured."/> : contacts.map(contact => <div className="contact-row" key={contact.id}><Phone size={17}/><div><b>{contact.name}</b><p>{contact.relationship} · {contact.phone} · Priority {contact.priority}</p></div><button className="quiet" onClick={() => edit(contact)}>Edit</button><button className="quiet" disabled={saving} onClick={() => void deactivate(contact)}>Deactivate</button></div>)}<form className="config-form" onSubmit={submit}><h3>{editing ? 'Edit contact' : 'Add contact'}</h3><label>Name<input value={draft.name} onChange={event => setDraft({...draft, name: event.target.value})} minLength={2} required/></label><label>Phone<input value={draft.phone} onChange={event => setDraft({...draft, phone: event.target.value})} minLength={7} required/></label><label>Relationship<input value={draft.relationship} onChange={event => setDraft({...draft, relationship: event.target.value})} minLength={2} required/></label><label>Priority<input type="number" min={1} max={10} value={draft.priority} onChange={event => setDraft({...draft, priority: Number(event.target.value)})} required/></label><button className="auth-submit" disabled={saving}>{saving ? 'Saving…' : editing ? 'Save contact' : 'Add contact'}</button>{editing && <button type="button" className="quiet" onClick={() => { setEditing(null); setDraft(emptyDraft) }}>Cancel</button>}</form></article>
}