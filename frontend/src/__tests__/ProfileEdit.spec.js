import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import ProfileEdit from '@/views/ProfileEdit.vue'

const mockProfile = {
  first_name: 'Иван',
  last_name: 'Петров',
  patronymic: 'Петрович',
  country_code: 'RU',
  email: 'ivan@example.com',
  phone: '+79990001122',
}

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn((url) => {
      if (url === '/auth/profile') {
        return Promise.resolve({ data: mockProfile })
      }
      return Promise.resolve({ data: {} })
    }),
    patch: vi.fn(() => Promise.resolve({ data: { ...mockProfile, first_name: 'Пётр' } })),
    post: vi.fn(() => Promise.resolve({ data: {} })),
  },
}))

vi.mock('@/composables/useAuth', () => ({
  useAuth: () => ({
    user: { value: mockProfile },
    setAuth: vi.fn(),
  }),
}))

describe('ProfileEdit.vue', () => {
  it('отображает заголовок страницы', async () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [{ path: '/profile/edit', component: ProfileEdit }],
    })
    await router.push('/profile/edit')
    await router.isReady()

    const wrapper = mount(ProfileEdit, {
      global: { plugins: [router] },
    })

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('Редактирование профиля')
    })
  })

  it('загружает и отображает данные пользователя', async () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [{ path: '/profile/edit', component: ProfileEdit }],
    })
    await router.push('/profile/edit')
    await router.isReady()

    const wrapper = mount(ProfileEdit, {
      global: { plugins: [router] },
    })

    await vi.waitFor(() => {
      expect(wrapper.find('[data-testid="edit-profile-first-name"]').element.value).toBe('Иван')
      expect(wrapper.find('[data-testid="edit-profile-last-name"]').element.value).toBe('Петров')
      expect(wrapper.find('[data-testid="edit-profile-patronymic"]').element.value).toBe('Петрович')
      expect(wrapper.find('[data-testid="edit-profile-country-code"]').element.value).toBe('RU')
      expect(wrapper.find('[data-testid="edit-profile-email"]').element.value).toBe('ivan@example.com')
      expect(wrapper.find('[data-testid="edit-profile-phone"]').element.value).toBe('+79990001122')
    })
  })

  it('содержит форму смены пароля', async () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [{ path: '/profile/edit', component: ProfileEdit }],
    })
    await router.push('/profile/edit')
    await router.isReady()

    const wrapper = mount(ProfileEdit, {
      global: { plugins: [router] },
    })

    await vi.waitFor(() => {
      expect(wrapper.find('[data-testid="edit-profile-old-password"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="edit-profile-new-password"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="edit-profile-confirm-password"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="edit-profile-password-save"]').exists()).toBe(true)
    })
  })
})
