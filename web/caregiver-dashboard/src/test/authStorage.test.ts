import { describe, it, expect, vi, beforeEach } from 'vitest'
import { storeSession, clearSession, readStoredUser, readRefreshToken } from '../auth/authStorage'
import { makeAuthUser } from './helpers'

describe('authStorage', () => {
  const user = makeAuthUser()

  describe('storeSession', () => {
    it('stores access token, refresh token, and user', () => {
      storeSession('access-123', 'refresh-456', user)
      expect(localStorage.getItem('neurox-token')).toBe('access-123')
      expect(localStorage.getItem('neurox-refresh-token')).toBe('refresh-456')
    })

    it('stores user as serialised JSON', () => {
      storeSession('access-123', 'refresh-456', user)
      const stored = localStorage.getItem('neurox-user')
      expect(stored).not.toBeNull()
      expect(JSON.parse(stored!)).toEqual(user)
    })
  })

  describe('readStoredUser', () => {
    it('returns null when nothing is stored', () => {
      expect(readStoredUser()).toBeNull()
    })

    it('returns the parsed user after storeSession', () => {
      storeSession('tok', 'ref', user)
      expect(readStoredUser()).toEqual(user)
    })

    it('returns null when the stored JSON is corrupt', () => {
      localStorage.setItem('neurox-user', '{{not valid json}}')
      expect(readStoredUser()).toBeNull()
    })
  })

  describe('readRefreshToken', () => {
    it('returns null when not stored', () => {
      expect(readRefreshToken()).toBeNull()
    })

    it('returns the stored refresh token', () => {
      storeSession('a', 'my-refresh', user)
      expect(readRefreshToken()).toBe('my-refresh')
    })
  })

  describe('clearSession', () => {
    it('removes all session keys', () => {
      storeSession('tok', 'ref', user)
      clearSession()
      expect(localStorage.getItem('neurox-token')).toBeNull()
      expect(localStorage.getItem('neurox-refresh-token')).toBeNull()
      expect(localStorage.getItem('neurox-user')).toBeNull()
    })

    it('is idempotent — calling twice does not throw', () => {
      expect(() => { clearSession(); clearSession() }).not.toThrow()
    })
  })
})
