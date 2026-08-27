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

  it('отображает цену с копейками', () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [{ path: '/', component: ProductCard }],
    })

    const wrapper = mount(ProductCard, {
      global: { plugins: [router] },
      props: {
        product: { id: 2, name: 'Test Product Cents', price: 4999.99, stock: 5 },
      },
    })

    expect(wrapper.text()).toMatch(/4\s999,99\s₽/)
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

  it('при stock=0 показывает бейдж и блокирует кнопку', () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [{ path: '/', component: ProductCard }],
    })

    const wrapper = mount(ProductCard, {
      global: { plugins: [router] },
      props: {
        product: { id: 3, name: 'Out Of Stock', price: 1999, stock: 0 },
      },
    })

    const badge = wrapper.find('[data-testid="out-of-stock-badge"]')
    expect(badge.exists()).toBe(true)
    expect(badge.text()).toBe('Нет в наличии')

    const button = wrapper.find('[data-testid="add-to-cart-button"]')
    expect(button.attributes('disabled')).toBeDefined()
    expect(button.text()).toContain('Нет в наличии')
  })

  it('при stock>0 не показывает бейдж и кнопка активна', () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [{ path: '/', component: ProductCard }],
    })

    const wrapper = mount(ProductCard, {
      global: { plugins: [router] },
      props: {
        product: { id: 4, name: 'In Stock', price: 1999, stock: 7 },
      },
    })

    expect(wrapper.find('[data-testid="out-of-stock-badge"]').exists()).toBe(false)

    const button = wrapper.find('[data-testid="add-to-cart-button"]')
    expect(button.attributes('disabled')).toBeUndefined()
    expect(button.text()).toContain('В корзину')
  })

  it('при отсутствии stock (undefined) не показывает бейдж и кнопка активна', () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [{ path: '/', component: ProductCard }],
    })

    const wrapper = mount(ProductCard, {
      global: { plugins: [router] },
      props: {
        product: { id: 5, name: 'No Stock Field', price: 1999 },
      },
    })

    expect(wrapper.find('[data-testid="out-of-stock-badge"]').exists()).toBe(false)

    const button = wrapper.find('[data-testid="add-to-cart-button"]')
    expect(button.attributes('disabled')).toBeUndefined()
    expect(button.text()).toContain('В корзину')
  })
})
