import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import ForgotPassword from '@/views/ForgotPassword.vue'

vi.mock('@/services/api', () => ({
  default: {
    post: vi.fn(),
  },
}))

import api from '@/services/api'

function createTestRouter() {
  return createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/forgot-password', component: ForgotPassword },
      { path: '/login', component: { template: '<div>Login</div>' } },
    ],
  })
}

describe('ForgotPassword.vue', () => {
  it('отображает форму восстановления пароля', async () => {
    const router = createTestRouter()
    const wrapper = mount(ForgotPassword, {
      global: {
        plugins: [router],
      },
    })

    await router.isReady()
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Восстановление пароля')
    expect(wrapper.find('input[type="email"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="forgot-password-submit"]').exists()).toBe(true)
  })

  it('показывает ошибку при пустом email', async () => {
    const router = createTestRouter()
    const wrapper = mount(ForgotPassword, {
      global: {
        plugins: [router],
      },
    })

    await router.isReady()
    await wrapper.vm.$nextTick()

    await wrapper.find('form').trigger('submit')
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Введите email')
  })

  it('отправляет запрос и показывает успех', async () => {
    api.post.mockResolvedValue({ data: { message: 'ok' } })

    const router = createTestRouter()
    const wrapper = mount(ForgotPassword, {
      global: {
        plugins: [router],
      },
    })

    await router.isReady()
    await wrapper.vm.$nextTick()

    await wrapper.find('input[type="email"]').setValue('test@example.com')
    await wrapper.find('form').trigger('submit')

    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(api.post).toHaveBeenCalledWith('/auth/password-reset-request/', {
      email: 'test@example.com',
    })
    expect(wrapper.find('[data-testid="forgot-password-success"]').exists()).toBe(true)
  })

  it('не раскрывает отсутствие email при ошибке сервера', async () => {
    api.post.mockRejectedValue(new Error('Network error'))

    const router = createTestRouter()
    const wrapper = mount(ForgotPassword, {
      global: {
        plugins: [router],
      },
    })

    await router.isReady()
    await wrapper.vm.$nextTick()

    await wrapper.find('input[type="email"]').setValue('unknown@example.com')
    await wrapper.find('form').trigger('submit')

    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(wrapper.find('[data-testid="forgot-password-success"]').exists()).toBe(true)
  })
})
