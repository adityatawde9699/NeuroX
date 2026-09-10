import type { AuthResponse } from '../types/dashboard'
import { clearSession, readAccessToken, sessionVersion, storeSession } from '../auth/authStorage'

const apiUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

const parseResponse = async <T>(response: Response): Promise<T> => {
  if (response.status === 204) return undefined as T
  const body = await response.json().catch(() => null) as {
    detail?: unknown
    error?: { message?: string }
  } | T | null
  if (!response.ok) {
    const detail = body && typeof body === 'object' && 'detail' in body ? body.detail : null
    const message = typeof detail === 'string'
      ? detail
      : Array.isArray(detail)
        ? detail.map(item => {
          if (!item || typeof item !== 'object') return 'Invalid value'
          const field = 'loc' in item && Array.isArray(item.loc) ? item.loc.slice(-1)[0] : 'field'
          const reason = 'msg' in item && typeof item.msg === 'string' ? item.msg : 'is invalid'
          return `${String(field)}: ${reason}`
        }).join('; ')
        : body && typeof body === 'object' && 'error' in body && body.error?.message
          ? body.error.message
          : 'The request could not be completed.'
    throw new ApiError(response.status, message || 'The request could not be completed.')
  }
  return body as T
}

let refreshFlight: Promise<AuthResponse> | null = null
export function restoreSession(): Promise<AuthResponse> {
  if (refreshFlight) return refreshFlight
  const version = sessionVersion()
  refreshFlight = fetch(`${apiUrl}/auth/browser/refresh`, {
    method: 'POST', credentials: 'include', headers: {Accept: 'application/json'},
  }).then(parseResponse<AuthResponse>).then(data => {
    if (sessionVersion() !== version) throw new ApiError(401, 'The session changed. Please sign in again.')
    storeSession(data.access_token, data.user)
    return data
  }).catch(error => {
    if (error instanceof ApiError && error.status === 401 && sessionVersion() === version) clearSession()
    throw error
  }).finally(() => { refreshFlight = null })
  return refreshFlight
}

export async function endSession(): Promise<void> {
  // Wait for a rotating cookie response before deleting/revoking that cookie.
  if (refreshFlight) await refreshFlight.catch(() => undefined)
  await request('/auth/browser/logout', {method: 'POST'}, false)
  clearSession()
}

export async function request<T>(path: string, options: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(options.headers)
  headers.set('Accept', 'application/json')
  headers.set('X-Client-Name', 'NeuroX Web')
  if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const token = readAccessToken()
  if (token && !path.startsWith('/auth/browser/')) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(`${apiUrl}${path}`, {...options, credentials: 'include', headers})
  if (response.status === 401 && retry && !path.startsWith('/auth/browser/')) {
    // Concurrent requests may have been sent with the same expired token.
    if (!readAccessToken() || readAccessToken() === token) await restoreSession()
    return request<T>(path, options, false)
  }
  if (response.status === 401 && !path.startsWith('/auth/browser/')) clearSession()
  return parseResponse<T>(response)
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) => request<T>(path, {method: 'POST', body: JSON.stringify(body)}),
  put: <T>(path: string, body: unknown) => request<T>(path, {method: 'PUT', body: JSON.stringify(body)}),
  delete: <T = void>(path: string) => request<T>(path, {method: 'DELETE'}),
}
