import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import ProfileEdit from '@/views/ProfileEdit.vue'

const mockProfile = {
  full_name: 'Иван Петров',
  email: 'ivan@example.com',
}

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn((url) => {
      if (url === '/auth/profile') {
        return Promise.resolve({ data: mockProfile })
      }
      return Promise.resolve({ data: {} })
    }),
    patch: vi.fn(() => Promise.resolve({ data: { ...mockProfile, full_name: 'Иван Обновлённый' } })),
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
      const nameInput = wrapper.find('[data-testid="edit-profile-name"]')
      expect(nameInput.exists()).toBe(true)
      expect(nameInput.element.value).toBe('Иван Петров')
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
