import { describe, it, expect, beforeEach } from 'vitest'
import { storeSession, clearSession, readStoredUser, readAccessToken } from '../auth/authStorage'
import { makeAuthUser } from './helpers'

describe('memory-only browser session', () => {
  beforeEach(clearSession)
  it('keeps tokens and user data out of persistent browser storage', () => {
    const user = makeAuthUser()
    storeSession('access-123', user)
    expect(readAccessToken()).toBe('access-123')
    expect(readStoredUser()).toEqual(user)
    expect(localStorage.length).toBe(0)
    expect(sessionStorage.length).toBe(0)
  })
  it('removes legacy plaintext session data', () => {
    localStorage.setItem('neurox-token', 'old-access')
    localStorage.setItem('neurox-refresh-token', 'old-refresh')
    localStorage.setItem('neurox-user', '{"name":"Old user"}')
    storeSession('new-access', makeAuthUser())
    expect(localStorage.length).toBe(0)
  })
  it('clears memory and is safe to call repeatedly', () => {
    storeSession('access', makeAuthUser())
    clearSession()
    clearSession()
    expect(readAccessToken()).toBeNull()
    expect(readStoredUser()).toBeNull()
  })
})
