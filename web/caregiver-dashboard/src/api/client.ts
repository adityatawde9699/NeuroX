import type { AuthResponse } from '../types/dashboard'

const apiUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

export const getStoredToken = () => localStorage.getItem('neurox-token')
export const getStoredRefreshToken = () => localStorage.getItem('neurox-refresh-token')

const parseResponse = async <T>(response: Response): Promise<T> => {
  if (response.status === 204) return undefined as T
  const body = await response.json().catch(() => null) as { detail?: string } | T | null
  if (!response.ok) {
    const message = body && typeof body === 'object' && 'detail' in body ? body.detail : 'The request could not be completed.'
    throw new ApiError(response.status, typeof message === 'string' ? message : 'The request could not be completed.')
  }
  return body as T
}

export async function request<T>(path: string, options: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(options.headers)
  if (!headers.has('Accept')) headers.set('Accept', 'application/json')
  if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const token = getStoredToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(`${apiUrl}${path}`, {...options, headers})
  if (response.status === 401 && retry) {
    const refreshToken = getStoredRefreshToken()
    if (refreshToken) {
      const refreshed = await fetch(`${apiUrl}/auth/refresh`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({refresh_token: refreshToken})})
      if (refreshed.ok) {
        const data = await refreshed.json() as AuthResponse
        localStorage.setItem('neurox-token', data.access_token)
        localStorage.setItem('neurox-refresh-token', data.refresh_token)
        return request<T>(path, options, false)
      }
    }
    localStorage.removeItem('neurox-token')
    localStorage.removeItem('neurox-refresh-token')
    localStorage.removeItem('neurox-user')
  }
  return parseResponse<T>(response)
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) => request<T>(path, {method: 'POST', body: JSON.stringify(body)}),
  put: <T>(path: string, body: unknown) => request<T>(path, {method: 'PUT', body: JSON.stringify(body)}),
  delete: (path: string) => request<void>(path, {method: 'DELETE'}),
}
