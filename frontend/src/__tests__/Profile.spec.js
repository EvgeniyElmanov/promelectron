import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import { ref } from 'vue'
import Profile from '@/views/Profile.vue'

const mockGet = vi.fn()

vi.mock('@/services/api', () => ({
  default: {
    get: (...args) => mockGet(...args),
  },
}))

vi.mock('@/composables/useAuth', () => ({
  useAuth: () => ({
    user: ref(null),
    logout: vi.fn(),
    isAdmin: ref(false),
    isSupplier: ref(false),
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

describe('Profile.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('отображает ФИО из раздельных полей с отчеством', async () => {
    mockGet.mockResolvedValue({
      data: {
        first_name: 'Иван',
        last_name: 'Петров',
        patronymic: 'Петрович',
        full_name: 'Старый ФИО',
        email: 'ivan@example.com',
        role: 'user',
        created_at: '2024-01-15T10:00:00Z',
      },
    })

    const wrapper = mount(Profile, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.text()).toContain('Петров Иван Петрович')
    expect(wrapper.text()).not.toContain('Старый ФИО')
  })

  it('использует full_name как fallback, когда раздельные поля пусты', async () => {
    mockGet.mockResolvedValue({
      data: {
        first_name: '',
        last_name: '',
        patronymic: '',
        full_name: 'Старый ФИО',
        email: 'ivan@example.com',
        role: 'user',
        created_at: '2024-01-15T10:00:00Z',
      },
    })

    const wrapper = mount(Profile, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.text()).toContain('Старый ФИО')
  })

  it('формирует инициалы из имени и фамилии', async () => {
    mockGet.mockResolvedValue({
      data: {
        first_name: 'Иван',
        last_name: 'Петров',
        patronymic: 'Петрович',
        full_name: '',
        email: 'ivan@example.com',
        role: 'user',
        created_at: '2024-01-15T10:00:00Z',
      },
    })

    const wrapper = mount(Profile, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.find('[data-testid="profile-avatar"]').text()).toContain('ИП')
  })
})
