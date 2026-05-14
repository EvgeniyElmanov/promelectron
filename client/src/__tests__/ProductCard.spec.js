import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import ProductCard from '@/components/ProductCard.vue'

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}))

vi.mock('@/composables/useAuth', () => ({
  useAuth: () => ({
    isAuthenticated: { value: true },
  }),
}))

describe('ProductCard.vue', () => {
  it('отображает название и цену', () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [{ path: '/', component: ProductCard }],
    })

    const wrapper = mount(ProductCard, {
      global: { plugins: [router] },
      props: {
        product: { id: 1, name: 'Test Product', price: 4999, stock: 5 },
      },
    })

    expect(wrapper.text()).toContain('Test Product')
    expect(wrapper.text()).toMatch(/4\s999\s₽/)
  })

  it('содержит кнопку избранного', () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [{ path: '/', component: ProductCard }],
    })

    const wrapper = mount(ProductCard, {
      global: { plugins: [router] },
      props: {
        product: { id: 1, name: 'Test Product', price: 4999, stock: 5 },
      },
    })

    expect(wrapper.find('[data-testid="favorite-button"]').exists()).toBe(true)
  })

  it('содержит кнопку добавления в корзину', () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [{ path: '/', component: ProductCard }],
    })

    const wrapper = mount(ProductCard, {
      global: { plugins: [router] },
      props: {
        product: { id: 1, name: 'Test Product', price: 4999, stock: 5 },
      },
    })

    expect(wrapper.find('[data-testid="add-to-cart-button"]').exists()).toBe(true)
  })
})
