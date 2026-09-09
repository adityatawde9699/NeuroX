import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { endSession, request, restoreSession } from '../api/client'
import { clearSession, readAccessToken, storeSession } from '../auth/authStorage'
import { makeAuthUser } from './helpers'

const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), {status})
describe('cookie session client', () => {
  beforeEach(clearSession)
  afterEach(() => vi.unstubAllGlobals())

  it('shares one refresh among concurrent expired requests', async () => {
    storeSession('expired', makeAuthUser())
    const fetchMock = vi.fn(async (url: string, init: RequestInit) => {
      if (url.endsWith('/auth/browser/refresh')) return json({access_token: 'fresh', user: makeAuthUser()})
      return new Headers(init.headers).get('Authorization') === 'Bearer fresh'
        ? json({ok: true}) : json({detail: 'Expired'}, 401)
    })
    vi.stubGlobal('fetch', fetchMock)
    expect(await Promise.all([request('/first'), request('/second')])).toEqual([{ok: true}, {ok: true}])
    expect(fetchMock.mock.calls.filter(([url]) => url.endsWith('/auth/browser/refresh'))).toHaveLength(1)
    expect(fetchMock.mock.calls.every(([, init]) => init.credentials === 'include')).toBe(true)
    expect(localStorage.length).toBe(0)
  })

  it('clears the in-memory identity when refresh is revoked', async () => {
    storeSession('expired', makeAuthUser())
    vi.stubGlobal('fetch', vi.fn(async () => json({detail: 'Revoked'}, 401)))
    await expect(request('/patients')).rejects.toMatchObject({status: 401})
    expect(readAccessToken()).toBeNull()
  })

  it('does not refresh on incorrect login credentials', async () => {
    const fetchMock = vi.fn(async () => json({detail: 'Incorrect password'}, 401))
    vi.stubGlobal('fetch', fetchMock)
    await expect(request('/auth/browser/login', {method: 'POST'})).rejects.toMatchObject({status: 401})
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('does not restore a session after it was cleared while refreshing', async () => {
    let resolve!: (response: Response) => void
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(done => { resolve = done })))
    const pending = restoreSession()
    clearSession()
    resolve(json({access_token: 'late-token', user: makeAuthUser()}))
    await expect(pending).rejects.toMatchObject({status: 401})
    expect(readAccessToken()).toBeNull()
  })

  it('waits for cookie rotation before logout', async () => {
    let resolve!: (response: Response) => void
    const fetchMock = vi.fn((url: string) => url.endsWith('/refresh')
      ? new Promise<Response>(done => { resolve = done }) : Promise.resolve(json({loggedOut: true})))
    vi.stubGlobal('fetch', fetchMock)
    const refresh = restoreSession()
    const logout = endSession()
    expect(fetchMock).toHaveBeenCalledTimes(1)
    resolve(json({access_token: 'fresh', user: makeAuthUser()}))
    await Promise.all([refresh, logout])
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(readAccessToken()).toBeNull()
  })
})
