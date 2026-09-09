import type { AuthUser } from '../types/dashboard'

// Access tokens and user data live only in memory. Refresh tokens are HttpOnly cookies.
let token: string | null = null
let user: AuthUser | null = null
let version = 0
const listeners = new Set<() => void>()

const removeLegacySession = () => {
  try {
    for (const key of ['neurox-token', 'neurox-refresh-token', 'neurox-user']) localStorage.removeItem(key)
  } catch { /* Cookie sessions also work when browser storage is unavailable. */ }
}
removeLegacySession()

export const readStoredUser = () => user
export const readAccessToken = () => token
export const sessionVersion = () => version
export const subscribeSession = (listener: () => void) => {
  listeners.add(listener)
  return () => { listeners.delete(listener) }
}
export const storeSession = (accessToken: string, nextUser: AuthUser) => {
  token = accessToken
  user = nextUser
  version += 1
  removeLegacySession()
  listeners.forEach(listener => listener())
}
export const clearSession = () => {
  token = null
  user = null
  version += 1
  removeLegacySession()
  listeners.forEach(listener => listener())
}
