/**
 * Shared mock factories for NeuroX dashboard tests.
 * Keep these in sync with the types in src/types/dashboard.ts.
 */
import type { AuthUser } from '../types/dashboard'
import type { DashboardAlert, ActivityReport } from '../api/dashboardApi'

export function makeAlert(overrides: Partial<DashboardAlert> = {}): DashboardAlert {
  return {
    id: 'alert-test-1',
    kind: 'alert',
    type: 'safe_zone_exit',
    severity: 'high',
    status: 'open',
    message: 'Patient may have left the safe zone.',
    createdAt: new Date().toISOString(),
    escalatedToPriority: 1,
    workflowNote: undefined,
    ...overrides,
  }
}

export function makeSosAlert(overrides: Partial<DashboardAlert> = {}): DashboardAlert {
  return {
    id: 'sos-test-1',
    kind: 'sos',
    type: undefined,
    severity: 'high',
    status: 'open',
    message: 'I need help. Please check on me.',
    createdAt: new Date().toISOString(),
    escalatedToPriority: 1,
    workflowNote: undefined,
    ...overrides,
  }
}

export function makeActivityReport(overrides: Partial<ActivityReport> = {}): ActivityReport {
  return {
    patientId: 'maya-demo',
    summary: {
      sessions: 5,
      completionRate: 0.8,
      averageAccuracy: 0.78,
      averageResponseTime: 9.4,
      averageDifficulty: 2.2,
    },
    series: [
      { date: new Date().toISOString(), completionRate: 1.0, accuracy: 0.9, responseTime: 8.0, difficulty: 2 },
    ],
    note: 'Supportive activity performance, not a medical assessment.',
    ...overrides,
  }
}

export function makeAuthUser(overrides: Partial<AuthUser> = {}): AuthUser {
  return {
    id: 'caregiver-test',
    name: 'Test Caregiver',
    email: 'test@neurox.demo',
    role: 'CAREGIVER',
    ...overrides,
  }
}
