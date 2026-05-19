import { describe, it, expect, beforeEach } from 'vitest'
import { useAuth } from '@/composables/useAuth.js'

// Reset module-level state between tests
beforeEach(() => {
  const { logout } = useAuth()
  logout()
})

describe('useAuth', () => {
  it('isAuthenticated возвращает false без токена', () => {
    const { isAuthenticated } = useAuth()
    expect(isAuthenticated.value).toBe(false)
  })

  it('isAuthenticated возвращает true после setAuth', () => {
    const { isAuthenticated, setAuth } = useAuth()
    setAuth('test-token-123', { id: 1, email: 'test@test.com', role: 'user' })
    expect(isAuthenticated.value).toBe(true)
  })

  it('logout сбрасывает состояние', () => {
    const { isAuthenticated, setAuth, logout } = useAuth()
    setAuth('test-token-123', { id: 1, email: 'test@test.com', role: 'user' })
    expect(isAuthenticated.value).toBe(true)

    logout()
    expect(isAuthenticated.value).toBe(false)
    expect(localStorage.getItem('access_token')).toBeNull()
  })

  it('setAuth сохраняет токен в localStorage', () => {
    const { setAuth } = useAuth()
    setAuth('test-token-abc')
    expect(localStorage.getItem('access_token')).toBe('test-token-abc')
  })

  it('user содержит данные пользователя', () => {
    const { user, setAuth } = useAuth()
    const userData = { id: 1, email: 'test@test.com', role: 'user' }
    setAuth('token', userData)
    expect(user.value).toEqual(userData)
  })

  it('isAdmin возвращает false для обычного пользователя', () => {
    const { isAdmin, setAuth } = useAuth()
    setAuth('token')
    expect(isAdmin.value).toBe(false)
  })
})
