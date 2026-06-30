import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import { ref } from 'vue'
import Profile from '@/views/Profile.vue'

const mockGet = vi.fn()
const mockPost = vi.fn()
const mockResendVerification = vi.fn()

vi.mock('@/services/api', () => ({
  default: {
    get: (...args) => mockGet(...args),
    post: (...args) => mockPost(...args),
  },
}))

vi.mock('@/composables/useAuth', () => ({
  useAuth: () => ({
    user: ref(null),
    logout: vi.fn(),
    isAdmin: ref(false),
    isSupplier: ref(false),
    emailVerified: ref(false),
    resendVerification: mockResendVerification,
  }),
}))

vi.mock('@/components/SkeletonProfile.vue', () => ({
  default: {
    name: 'SkeletonProfile',
    template: '<div data-testid="skeleton-profile">Loading</div>',
  },
}))

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/profile', component: Profile },
    { path: '/login', component: { template: '<div>Login</div>' } },
  ],
})

const baseProfile = {
  first_name: 'Иван',
  last_name: 'Петров',
  patronymic: 'Петрович',
  full_name: 'Старый ФИО',
  email: 'ivan@example.com',
  role: 'user',
  created_at: '2024-01-15T10:00:00Z',
}

describe('Profile.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('отображает ФИО из раздельных полей с отчеством', async () => {
    mockGet.mockResolvedValue({ data: baseProfile })

    const wrapper = mount(Profile, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.text()).toContain('Петров Иван Петрович')
    expect(wrapper.text()).not.toContain('Старый ФИО')
  })

  it('использует full_name как fallback, когда раздельные поля пусты', async () => {
    mockGet.mockResolvedValue({
      data: { ...baseProfile, first_name: '', last_name: '', patronymic: '' },
    })

    const wrapper = mount(Profile, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.text()).toContain('Старый ФИО')
  })

  it('формирует инициалы из имени и фамилии', async () => {
    mockGet.mockResolvedValue({ data: baseProfile })

    const wrapper = mount(Profile, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.find('[data-testid="profile-avatar"]').text()).toContain('ИП')
  })

  it('показывает баннер подтверждения email, когда email не подтверждён', async () => {
    mockGet.mockResolvedValue({ data: { ...baseProfile, email_verified: false } })

    const wrapper = mount(Profile, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.find('[data-testid="profile-verify-banner"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="profile-email-status"]').text()).toContain('Не подтверждён')
  })

  it('не показывает баннер, когда email подтверждён', async () => {
    mockGet.mockResolvedValue({ data: { ...baseProfile, email_verified: true } })

    const wrapper = mount(Profile, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.find('[data-testid="profile-verify-banner"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="profile-email-status"]').text()).toContain('Подтверждён')
  })

  it('отправляет повторное письмо по кнопке и показывает сообщение', async () => {
    mockGet.mockResolvedValue({ data: { ...baseProfile, email_verified: false } })
    mockResendVerification.mockResolvedValue({ message: 'If the email exists, instructions have been sent' })

    const wrapper = mount(Profile, { global: { plugins: [router] } })
    await flushPromises()

    await wrapper.find('[data-testid="profile-resend-verification"]').trigger('click')
    await flushPromises()

    expect(mockResendVerification).toHaveBeenCalled()
    expect(wrapper.find('[data-testid="profile-resend-message"]').text()).toContain('Письмо отправлено')
  })

  it('показывает ошибку, если повторная отправка не удалась', async () => {
    mockGet.mockResolvedValue({ data: { ...baseProfile, email_verified: false } })
    mockResendVerification.mockRejectedValue({
      response: { data: { detail: 'Слишком много запросов' } },
    })

    const wrapper = mount(Profile, { global: { plugins: [router] } })
    await flushPromises()

    await wrapper.find('[data-testid="profile-resend-verification"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="profile-resend-error"]').text()).toContain('Слишком много запросов')
  })
})
