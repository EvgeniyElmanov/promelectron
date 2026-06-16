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
        return Promise.resolve({ data: { items: mockProducts, total: mockProducts.length } })
      }
      if (url === '/categories/') {
        return Promise.resolve({ data: { items: mockCategories, total: mockCategories.length } })
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

  it('отображает количество товаров', async () => {
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
      expect(wrapper.text()).toContain('2 товаров')
    })
  })

  it('отображает фильтр по рейтингу', async () => {
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
      expect(wrapper.text()).toContain('Рейтинг:')
    })

    for (let i = 1; i <= 5; i++) {
      expect(wrapper.find(`[data-testid="rating-filter-${i}"]`).exists()).toBe(true)
    }
  })

  it('отображает селектор сортировки с новыми опциями', async () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [{ path: '/', component: Products }],
    })

    const wrapper = mount(Products, {
      global: {
        plugins: [router],
      },
    })

    const select = wrapper.find('[data-testid="sort-select"]')
    expect(select.exists()).toBe(true)

    const options = select.findAll('option')
    const values = options.map(o => o.attributes('value'))
    expect(values).toContain('rating_desc')
    expect(values).toContain('name_asc')
  })
})
