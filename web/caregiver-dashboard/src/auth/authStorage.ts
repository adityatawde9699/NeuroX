import type { AuthUser } from '../types/dashboard'

const keys = {token: 'neurox-token', refresh: 'neurox-refresh-token', user: 'neurox-user'} as const

export const readStoredUser = (): AuthUser | null => {
  const value = localStorage.getItem(keys.user)
  if (!value) return null
  try { return JSON.parse(value) as AuthUser } catch { return null }
}

export const storeSession = (accessToken: string, refreshToken: string, user: AuthUser) => {
  localStorage.setItem(keys.token, accessToken)
  localStorage.setItem(keys.refresh, refreshToken)
  localStorage.setItem(keys.user, JSON.stringify(user))
}

export const readRefreshToken = () => localStorage.getItem(keys.refresh)

export const clearSession = () => {
  localStorage.removeItem(keys.token)
  localStorage.removeItem(keys.refresh)
  localStorage.removeItem(keys.user)
}
