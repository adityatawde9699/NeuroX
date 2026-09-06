import { useCallback, useEffect, useState } from 'react'
import { dashboardApi } from '../api/dashboardApi'
import type { AuthUser, LanguageConfig, Patient, SafetyState, TrendPoint } from '../types/dashboard'

export function useDashboardBootstrap(user: AuthUser | null, selectedPatientId?: string) {
  const [patient, setPatient] = useState<Patient | null>(null)
  const [safety, setSafety] = useState<SafetyState | null>(null)
  const [trend, setTrend] = useState<TrendPoint[]>([])
  const [performanceLoaded, setPerformanceLoaded] = useState(false)
  const [activityCount, setActivityCount] = useState<number | null>(null)
  const [patientLang, setPatientLang] = useState<LanguageConfig | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const loadSafety = useCallback(async (patientId: string) => {
    const value = await dashboardApi.safety(patientId)
    setSafety(value)
    return value
  }, [])

  useEffect(() => {
    if (!user) return
    let cancelled = false
    const load = async () => {
      setLoading(true)
      setError('')
      try {
        const selected = user.role === 'PATIENT' ? await dashboardApi.patientMe() : selectedPatientId ? await dashboardApi.patient(selectedPatientId) : (await dashboardApi.assignedPatients())[0]
        if (cancelled) return
        if (!selected) { setPatient(null); setSafety(null); return }
        setPatient(selected)
        await loadSafety(selected.id)
        try {
          const data = await dashboardApi.performance(selected.id)
          if (!cancelled) {
            setTrend(data.completion.map((value, index) => ({day: `Session ${index + 1}`, value, accuracy: data.accuracyScores[index] ?? value, response: data.responseTimes[index] ?? 0, difficulty: data.difficultyProgression[index] ?? data.difficulty})))
            setActivityCount(data.completion.length)
            setPerformanceLoaded(true)
          }
        } catch { if (!cancelled) setPerformanceLoaded(false) }
        try {
          const configs = await dashboardApi.languages()
          const assamese = configs.find(config => config.languageCode === 'as-IN')
          if (!cancelled) setPatientLang(assamese ?? null)
        } catch { if (!cancelled) setPatientLang(null) }
      } catch (cause) {
        if (!cancelled) { setError(cause instanceof Error ? cause.message : 'Unable to load dashboard data.'); setPerformanceLoaded(false); setActivityCount(null); setTrend([]) }
      } finally { if (!cancelled) setLoading(false) }
    }
    void load()
    return () => { cancelled = true }
  }, [loadSafety, selectedPatientId, user])

  return {patient, safety, trend, performanceLoaded, activityCount, patientLang, loading, error, loadSafety}
}
