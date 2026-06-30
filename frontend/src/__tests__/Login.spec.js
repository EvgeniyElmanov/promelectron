import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import Login from '@/views/Login.vue'

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

import api from '@/services/api'

function createTestRouter() {
  return createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/login', component: Login },
      { path: '/register', component: { template: '<div>Register</div>' } },
      { path: '/forgot-password', component: { template: '<div>Forgot Password</div>' } },
    ],
  })
}

describe('Login.vue', () => {
  it('отображает форму входа', async () => {
    api.get.mockResolvedValue({ data: { google: true, yandex: true } })

    const router = createTestRouter()
    const wrapper = mount(Login, {
      global: {
        plugins: [router],
      },
    })

    await router.isReady()
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Вход')
    expect(wrapper.find('input[type="email"]').exists()).toBe(true)
    expect(wrapper.find('input[type="password"]').exists()).toBe(true)
  })

  it('содержит ссылку на регистрацию', async () => {
    api.get.mockResolvedValue({ data: { google: true, yandex: true } })

    const router = createTestRouter()
    const wrapper = mount(Login, {
      global: {
        plugins: [router],
      },
    })

    await router.isReady()
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Зарегистрироваться')
  })

  it('содержит ссылку "Забыли пароль?"', async () => {
    api.get.mockResolvedValue({ data: { google: false, yandex: false } })

    const router = createTestRouter()
    const wrapper = mount(Login, {
      global: {
        plugins: [router],
      },
    })

    await router.isReady()
    await wrapper.vm.$nextTick()

    const link = wrapper.find('[data-testid="login-forgot-password"]')
    expect(link.exists()).toBe(true)
    expect(link.text()).toContain('Забыли пароль?')
    expect(link.attributes('href')).toBe('/forgot-password')
  })

  it('показывает OAuth кнопки, когда провайдеры включены', async () => {
    api.get.mockResolvedValue({ data: { google: true, yandex: true } })

    const router = createTestRouter()
    const wrapper = mount(Login, {
      global: {
        plugins: [router],
      },
    })

    await router.isReady()
    await flushPromises()

    expect(wrapper.text()).toContain('Google')
    expect(wrapper.text()).toContain('Яндекс')
    expect(wrapper.find('[data-testid="login-google"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="login-yandex"]').exists()).toBe(true)
  })

  it('скрывает кнопку Google, когда Google OAuth отключён', async () => {
    api.get.mockResolvedValue({ data: { google: false, yandex: true } })

    const router = createTestRouter()
    const wrapper = mount(Login, {
      global: {
        plugins: [router],
      },
    })

    await router.isReady()
    await flushPromises()

    expect(wrapper.text()).not.toContain('Google')
    expect(wrapper.text()).toContain('Яндекс')
    expect(wrapper.find('[data-testid="login-google"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="login-yandex"]').exists()).toBe(true)
  })

  it('скрывает весь OAuth блок, если все провайдеры отключены', async () => {
    api.get.mockResolvedValue({ data: { google: false, yandex: false } })

    const router = createTestRouter()
    const wrapper = mount(Login, {
      global: {
        plugins: [router],
      },
    })

    await router.isReady()
    await flushPromises()

    expect(wrapper.text()).not.toContain('Google')
    expect(wrapper.text()).not.toContain('Яндекс')
    expect(wrapper.text()).not.toContain('или')
  })
})
