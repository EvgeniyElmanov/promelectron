import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import VerifyEmail from '@/views/VerifyEmail.vue'

const mockGet = vi.fn()

vi.mock('@/services/api', () => ({
  default: {
    get: (...args) => mockGet(...args),
  },
}))

function createTestRouter() {
  return createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/verify-email', component: VerifyEmail },
      { path: '/verify-email/success', component: { template: '<div>Success</div>' } },
      { path: '/verify-email/error', component: { template: '<div>Error</div>' } },
    ],
  })
}

describe('VerifyEmail.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('показывает индикатор загрузки', async () => {
    mockGet.mockImplementation(() => new Promise(() => {}))

    const router = createTestRouter()
    await router.push('/verify-email?token=abc123')
    await router.isReady()

    const wrapper = mount(VerifyEmail, {
      global: { plugins: [router] },
    })
    await flushPromises()

    expect(wrapper.find('[data-testid="verify-email-loading"]').exists()).toBe(true)
  })

  it('перенаправляет на success при успешном подтверждении', async () => {
    mockGet.mockResolvedValue({ status: 200 })

    const router = createTestRouter()
    const pushSpy = vi.spyOn(router, 'replace')
    await router.push('/verify-email?token=valid-token')
    await router.isReady()

    mount(VerifyEmail, {
      global: { plugins: [router] },
    })
    await flushPromises()

    expect(mockGet).toHaveBeenCalledWith('/auth/verify-email/', {
      params: { token: 'valid-token' },
      maxRedirects: 0,
    })
    expect(pushSpy).toHaveBeenCalledWith('/verify-email/success')
  })

  it('обрабатывает прозрачный 302-редирект на success через responseURL', async () => {
    mockGet.mockResolvedValue({
      status: 200,
      request: {
        responseURL: 'https://example.com/verify-email/success',
      },
    })

    const router = createTestRouter()
    const pushSpy = vi.spyOn(router, 'replace')
    await router.push('/verify-email?token=valid-token')
    await router.isReady()

    mount(VerifyEmail, {
      global: { plugins: [router] },
    })
    await flushPromises()

    expect(pushSpy).toHaveBeenCalledWith('/verify-email/success')
  })

  it('обрабатывает прозрачный 302-редирект на error через responseURL', async () => {
    mockGet.mockResolvedValue({
      status: 200,
      request: {
        responseURL: 'https://example.com/verify-email/error?reason=expired',
      },
    })

    const router = createTestRouter()
    const pushSpy = vi.spyOn(router, 'replace')
    await router.push('/verify-email?token=expired-token')
    await router.isReady()

    mount(VerifyEmail, {
      global: { plugins: [router] },
    })
    await flushPromises()

    expect(pushSpy).toHaveBeenCalledWith('/verify-email/error?reason=expired')
  })

  it('перенаправляет на error при 302 с location ошибки', async () => {
    mockGet.mockRejectedValue({
      response: {
        status: 302,
        headers: {
          location: 'https://example.com/verify-email/error?reason=expired',
        },
      },
    })

    const router = createTestRouter()
    const pushSpy = vi.spyOn(router, 'replace')
    await router.push('/verify-email?token=expired-token')
    await router.isReady()

    mount(VerifyEmail, {
      global: { plugins: [router] },
    })
    await flushPromises()

    expect(pushSpy).toHaveBeenCalledWith('/verify-email/error?reason=expired')
  })

  it('перенаправляет на error при отсутствии токена', async () => {
    const router = createTestRouter()
    const pushSpy = vi.spyOn(router, 'replace')
    await router.push('/verify-email')
    await router.isReady()

    mount(VerifyEmail, {
      global: { plugins: [router] },
    })
    await flushPromises()

    expect(pushSpy).toHaveBeenCalledWith('/verify-email/error?reason=invalid')
  })
})
