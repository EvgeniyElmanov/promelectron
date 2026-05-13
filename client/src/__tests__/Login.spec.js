import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
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

describe('Login.vue', () => {
  it('отображает форму входа', () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [{ path: '/login', component: Login }],
    })

    const wrapper = mount(Login, {
      global: {
        plugins: [router],
      },
    })

    expect(wrapper.text()).toContain('Вход')
    expect(wrapper.find('input[type="email"]').exists()).toBe(true)
    expect(wrapper.find('input[type="password"]').exists()).toBe(true)
  })

  it('содержит ссылку на регистрацию', () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/login', component: Login },
        { path: '/register', component: { template: '<div>Register</div>' } },
      ],
    })

    const wrapper = mount(Login, {
      global: {
        plugins: [router],
      },
    })

    expect(wrapper.text()).toContain('Зарегистрироваться')
  })

  it('показывает OAuth кнопки', () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [{ path: '/login', component: Login }],
    })

    const wrapper = mount(Login, {
      global: {
        plugins: [router],
      },
    })

    expect(wrapper.text()).toContain('Google')
    expect(wrapper.text()).toContain('Яндекс')
  })
})
