import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import AuthCallback from '@/views/AuthCallback.vue'

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
  },
}))

const setAuth = vi.fn()
const mergeCartOnLogin = vi.fn()
vi.mock('@/composables/useAuth', () => ({ useAuth: () => ({ setAuth }) }))
vi.mock('@/composables/useCart', () => ({ useCart: () => ({ mergeCartOnLogin }) }))

import api from '@/services/api'

function createTestRouter() {
  return createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/auth/callback', component: AuthCallback },
      { path: '/', component: { template: '<div>Home</div>' } },
    ],
  })
}

describe('AuthCallback.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('отправляет code и state на provider-agnostic /auth/callback и логинит', async () => {
    api.get.mockResolvedValue({
      data: { access_token: 'jwt-token', user: { id: 1, email: 'a@b.c' } },
    })

    const router = createTestRouter()
    router.push({ path: '/auth/callback', query: { code: 'the-code', state: 'the-state' } })
    await router.isReady()

    mount(AuthCallback, { global: { plugins: [router] } })
    await flushPromises()

    expect(api.get).toHaveBeenCalledWith('/auth/callback', {
      params: { code: 'the-code', state: 'the-state' },
    })
    expect(setAuth).toHaveBeenCalledWith('jwt-token', { id: 1, email: 'a@b.c' })
  })

  it('показывает ошибку и не вызывает API, если state отсутствует', async () => {
    const router = createTestRouter()
    router.push({ path: '/auth/callback', query: { code: 'the-code' } })
    await router.isReady()

    const wrapper = mount(AuthCallback, { global: { plugins: [router] } })
    await flushPromises()

    expect(api.get).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('отсутствуют параметры')
  })
})
