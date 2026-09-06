import { useState } from 'react'
import { authApi } from '../api/dashboardApi'
import { clearSession, readRefreshToken, readStoredUser, storeSession } from './authStorage'
import type { AuthResponse, AuthUser } from '../types/dashboard'

export function useAuth() {
  const [user, setUser] = useState<AuthUser | null>(() => readStoredUser())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const finish = (data: AuthResponse) => {
    storeSession(data.access_token, data.refresh_token, data.user)
    setUser(data.user)
  }

  const signIn = async (email: string, password: string) => {
    setLoading(true)
    setError('')
    try { finish(await authApi.login(email, password)) } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to sign in.')
      throw cause
    } finally { setLoading(false) }
  }

  const signOut = async () => {
    const refreshToken = readRefreshToken()
    if (refreshToken) await authApi.logout(refreshToken).catch(() => undefined)
    clearSession()
    setUser(null)
  }

  return {user, loading, error, signIn, signOut}
}
