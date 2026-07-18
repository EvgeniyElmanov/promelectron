import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import Register from '@/views/Register.vue'

const mockPost = vi.fn()
const mockGet = vi.fn()

vi.mock('@/services/api', () => ({
  default: {
    get: (...args) => mockGet(...args),
    post: (...args) => mockPost(...args),
  },
}))

const mockMergeCartOnLogin = vi.hoisted(() => vi.fn())

vi.mock('@/composables/useAuth', () => ({
  useAuth: () => ({
    setAuth: vi.fn(),
  }),
}))

vi.mock('@/composables/useCart', () => ({
  useCart: () => ({
    mergeCartOnLogin: mockMergeCartOnLogin,
  }),
}))

function createTestRouter() {
  return createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/register', component: Register },
      { path: '/', component: { template: '<div>Home</div>' } },
    ],
  })
}

describe('Register.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('отображает форму регистрации', async () => {
    mockGet.mockResolvedValue({ data: { google: false, yandex: false } })

    const router = createTestRouter()
    const wrapper = mount(Register, {
      global: { plugins: [router] },
    })
    await router.isReady()
    await flushPromises()

    expect(wrapper.find('[data-testid="register-form"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="register-email"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="register-password"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="register-submit"]').exists()).toBe(true)
  })

  it('отправляет запрос на /register/ и показывает сообщение об успехе', async () => {
    mockGet.mockResolvedValue({ data: { google: false, yandex: false } })
    mockPost.mockResolvedValue({
      data: {
        access_token: 'token123',
        user: {
          id: 1,
          email: 'test@example.com',
          email_verified: false,
        },
      },
    })

    const router = createTestRouter()
    const wrapper = mount(Register, {
      global: { plugins: [router] },
    })
    await router.isReady()
    await flushPromises()

    await wrapper.find('[data-testid="register-email"]').setValue('test@example.com')
    await wrapper.find('[data-testid="register-password"]').setValue('password123')
    await wrapper.find('[data-testid="register-password-confirm"]').setValue('password123')
    await wrapper.find('[data-testid="register-form"]').trigger('submit')
    await flushPromises()

    expect(mockPost).toHaveBeenCalledWith('/register/', {
      email: 'test@example.com',
      password: 'password123',
      full_name: null,
      role: 'user',
    })

    expect(mockMergeCartOnLogin).toHaveBeenCalled()
    expect(wrapper.find('[data-testid="register-success"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('test@example.com')
  })

  it('показывает ошибку при неудачной регистрации', async () => {
    mockGet.mockResolvedValue({ data: { google: false, yandex: false } })
    mockPost.mockRejectedValue({
      response: { data: { detail: 'Email уже зарегистрирован' } },
    })

    const router = createTestRouter()
    const wrapper = mount(Register, {
      global: { plugins: [router] },
    })
    await router.isReady()
    await flushPromises()

    await wrapper.find('[data-testid="register-email"]').setValue('test@example.com')
    await wrapper.find('[data-testid="register-password"]').setValue('password123')
    await wrapper.find('[data-testid="register-password-confirm"]').setValue('password123')
    await wrapper.find('[data-testid="register-form"]').trigger('submit')
    await flushPromises()

    expect(wrapper.find('[data-testid="register-error"]').text()).toBe('Email уже зарегистрирован')
  })

  it('валидирует обязательные поля', async () => {
    mockGet.mockResolvedValue({ data: { google: false, yandex: false } })

    const router = createTestRouter()
    const wrapper = mount(Register, {
      global: { plugins: [router] },
    })
    await router.isReady()
    await flushPromises()

    await wrapper.find('[data-testid="register-form"]').trigger('submit')
    await flushPromises()

    expect(mockPost).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Введите email')
  })
})
