import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import Products from '@/views/Products.vue'

const mockProducts = [
  { id: 1, name: 'Product 1', price: 9999, stock: 10 },
  { id: 2, name: 'Product 2', price: 14999, stock: 5 },
]

const mockCategories = [
  { id: 1, name: 'Электроника', description: null, parent_id: null },
  { id: 2, name: 'Одежда', description: null, parent_id: null },
]

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn((url) => {
      if (url === '/products/') {
        return Promise.resolve({ data: mockProducts })
      }
      if (url === '/categories/') {
        return Promise.resolve({ data: mockCategories })
      }
      return Promise.resolve({ data: [] })
    }),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

describe('Products.vue', () => {
  it('отображает заголовок "Популярные товары"', async () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [{ path: '/', component: Products }],
    })

    const wrapper = mount(Products, {
      global: {
        plugins: [router],
      },
    })

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('Популярные товары')
    })
  })

  it('отображает строку поиска', async () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [{ path: '/', component: Products }],
    })

    const wrapper = mount(Products, {
      global: {
        plugins: [router],
      },
    })

    const input = wrapper.find('input[type="text"]')
    expect(input.exists()).toBe(true)
    expect(input.attributes('placeholder')).toBe('Поиск товаров...')
  })

  it('отображает карточки товаров', async () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [{ path: '/', component: Products }],
    })

    const wrapper = mount(Products, {
      global: {
        plugins: [router],
      },
    })

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('Product 1')
      expect(wrapper.text()).toContain('Product 2')
    })
  })
})
