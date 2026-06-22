import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import ResetPassword from '@/views/ResetPassword.vue'

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
      { path: '/reset-password', component: ResetPassword },
      { path: '/login', component: { template: '<div>Login</div>' } },
    ],
  })
}

function mountWithQuery(query) {
  const router = createTestRouter()
  router.push({ path: '/reset-password', query })
  return router.isReady().then(() => ({
    wrapper: mount(ResetPassword, {
      global: {
        plugins: [router],
      },
    }),
    router,
  }))
}

describe('ResetPassword.vue', () => {
  it('отображает форму сброса пароля', async () => {
    const { wrapper } = await mountWithQuery({ token: 'abc123' })
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Новый пароль')
    expect(wrapper.findAll('input[type="password"]').length).toBe(2)
    expect(wrapper.find('[data-testid="reset-password-submit"]').exists()).toBe(true)
  })

  it('показывает ошибку при отсутствии токена', async () => {
    const { wrapper } = await mountWithQuery({})
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('недействительна или устарела')
  })

  it('валидирует минимальную длину пароля', async () => {
    const { wrapper } = await mountWithQuery({ token: 'abc123' })
    await wrapper.vm.$nextTick()

    const inputs = wrapper.findAll('input[type="password"]')
    await inputs[0].setValue('short')
    await inputs[1].setValue('short')
    await wrapper.find('form').trigger('submit')
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('минимум 8 символов')
  })

  it('валидирует совпадение паролей', async () => {
    const { wrapper } = await mountWithQuery({ token: 'abc123' })
    await wrapper.vm.$nextTick()

    const inputs = wrapper.findAll('input[type="password"]')
    await inputs[0].setValue('Password123!')
    await inputs[1].setValue('Different123!')
    await wrapper.find('form').trigger('submit')
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('не совпадают')
  })

  it('отправляет запрос и показывает успех', async () => {
    api.post.mockResolvedValue({ data: { message: 'ok' } })

    const { wrapper } = await mountWithQuery({ token: 'abc123' })
    await wrapper.vm.$nextTick()

    const inputs = wrapper.findAll('input[type="password"]')
    await inputs[0].setValue('Password123!')
    await inputs[1].setValue('Password123!')
    await wrapper.find('form').trigger('submit')

    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 0))

    expect(api.post).toHaveBeenCalledWith('/auth/password-reset/', {
      token: 'abc123',
      new_password: 'Password123!',
    })
    expect(wrapper.find('[data-testid="reset-password-success"]').exists()).toBe(true)
  })
})
