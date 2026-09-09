import { api, endSession } from './client'
import type { AuthResponse, AuthUser, Contact, LanguageConfig, Patient, PerformanceData, SafetyState } from '../types/dashboard'

export type ActivityReport = { patientId: string; summary: { sessions: number; completionRate: number; averageAccuracy: number; averageResponseTime: number; averageDifficulty: number }; series: Array<{date: string; completionRate: number; accuracy: number; responseTime: number; difficulty: number}>; note: string }
export type ActivityHistory = { id: string; activityId: string; startedAt: string; completedAt: string | null; accuracy: number | null; responseTime: number | null; attempts: number; status: string; difficulty: number }
export type DashboardAlert = { id: string; kind: string; type?: string; severity?: string; status: string; message: string; createdAt: string; escalatedToPriority: number; workflowNote?: string }
export type LocationHistoryItem = { id: string; latitude: number; longitude: number; accuracyM: number; connectionState: string; capturedAt: string; freshness: string; label: string }

export const authApi = {
  login: (email: string, password: string) => api.post<AuthResponse>('/auth/browser/login', {email, password}),
  register: (name: string, email: string, password: string) => api.post<AuthResponse>('/auth/browser/register', {name, email, password, role: 'CAREGIVER'}),
  google: (credential: string) => api.post<AuthResponse>('/auth/browser/google', {credential}),
  me: () => api.get<AuthUser>('/auth/me'),
  logout: endSession,
  updateProfile: (name: string) => api.put<AuthUser>('/auth/me', {name}),
  changePassword: (currentPassword: string, newPassword: string) => api.put<{updated: boolean}>('/auth/me/password', {current_password: currentPassword, new_password: newPassword}),
  privacy: () => api.get<{locationSharingEnabled: boolean}>('/patients/me/privacy'),
  setLocationSharing: (enabled: boolean) => api.put<{enabled: boolean; message: string}>('/patients/me/privacy/location-sharing', {enabled}),
  caregivers: () => api.get<Array<{id: string; name: string; email: string}>>('/patients/me/caregivers'),
  revokeCaregiver: (id: string) => api.delete(`/patients/me/caregivers/${id}`),
  exportData: () => api.get('/patients/me/privacy/export'),
  requestDeletion: () => api.post<{message: string}>('/patients/me/privacy/deletion-request', {}),
}

export const dashboardApi = {
  assignedPatients: () => api.get<Patient[]>('/caregivers/me/patients'),
  patientMe: () => api.get<Patient>('/patients/me'),
  patient: (patientId: string) => api.get<Patient>(`/patients/${patientId}`),
  safety: (patientId: string) => api.get<SafetyState>(`/patients/${patientId}/safety`),
  locationHistory: (patientId: string) => api.get<LocationHistoryItem[]>(`/patients/${patientId}/location-updates`),
  performance: (patientId: string) => api.get<PerformanceData>(`/patients/${patientId}/performance`),
  report: (patientId: string, filters: {from?: string; to?: string; activityId?: string} = {}) => {
    const params = new URLSearchParams()
    if (filters.from) params.set('from', new Date(filters.from).toISOString())
    if (filters.to) params.set('to', new Date(filters.to).toISOString())
    if (filters.activityId) params.set('activity_id', filters.activityId)
    const query = params.toString()
    return api.get<ActivityReport>(`/patients/${patientId}/reports/activity${query ? `?${query}` : ''}`)
  },
  history: (patientId: string) => api.get<ActivityHistory[]>(`/patients/${patientId}/activity-sessions`),
  alerts: (patientId: string) => api.get<DashboardAlert[]>(`/patients/${patientId}/alerts?status=all`),
  acknowledge: (patientId: string, kind: 'alert' | 'sos', id: string) => api.post(`/patients/${patientId}/${kind === 'sos' ? 'sos-events' : 'safety-alerts'}/${id}/acknowledge`, {note: 'Acknowledged from caregiver dashboard'}),
  languages: () => api.get<LanguageConfig[]>('/language-config'),
  updateSafetySettings: (patientId: string, payload: unknown) => api.put(`/patients/${patientId}/safety/settings`, payload),
  contacts: (patientId: string) => api.get<Contact[]>(`/patients/${patientId}/emergency-contacts`),
  createContact: (patientId: string, payload: unknown) => api.post<Contact>(`/patients/${patientId}/emergency-contacts`, payload),
  updateContact: (patientId: string, contactId: string, payload: unknown) => api.put<Contact>(`/patients/${patientId}/emergency-contacts/${contactId}`, payload),
}
