import { useEffect, useState } from 'react'
import { authApi } from '../api/dashboardApi'
import { ApiError, restoreSession } from '../api/client'
import { readStoredUser, storeSession, subscribeSession } from './authStorage'
import type { AuthUser } from '../types/dashboard'

export function useAuth() {
  const [user, setUser] = useState<AuthUser | null>(() => readStoredUser())
  const [checking, setChecking] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    const unsubscribe = subscribeSession(() => setUser(readStoredUser()))
    const restore = readStoredUser() ? Promise.resolve() : restoreSession()
    void restore.catch(cause => {
      if (active && !(cause instanceof ApiError && cause.status === 401)) {
        setError('Could not reconnect to your session. Check your connection and try again.')
      }
    }).finally(() => { if (active) setChecking(false) })
    return () => { active = false; unsubscribe() }
  }, [])

  const signIn = async (email: string, password: string) => {
    setLoading(true)
    setError('')
    try {
      const data = await authApi.login(email, password)
      storeSession(data.access_token, data.user)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to sign in.')
      throw cause
    } finally { setLoading(false) }
  }

  const signOut = async () => {
    setLoading(true)
    setError('')
    try { await authApi.logout() } catch {
      setError('Sign-out could not reach the server. Please reconnect and try again.')
    } finally { setLoading(false) }
  }
  return {user, setUser, checking, loading, error, signIn, signOut}
}
