import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import ProductCard from '@/components/ProductCard.vue'
import api from '@/services/api'

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
  beforeEach(() => {
    vi.clearAllMocks()
  })

  function mountCard(product) {
    const router = createRouter({
      history: createWebHistory(),
      routes: [{ path: '/', component: ProductCard }],
    })
    return mount(ProductCard, {
      global: { plugins: [router] },
      props: { product },
    })
  }

  it('клик по активному сердечку шлёт DELETE и эмитит removed', async () => {
    api.delete.mockResolvedValue({})
    const wrapper = mountCard({ id: 1, name: 'Fav Product', price: 4999, stock: 5, is_favorite: true })

    await wrapper.find('[data-testid="favorite-button"]').trigger('click')
    await flushPromises()

    expect(api.delete).toHaveBeenCalledWith('/favorites/remove/1')
    expect(api.post).not.toHaveBeenCalled()
    expect(wrapper.emitted('removed')).toEqual([[1]])
  })

  it('клик по неактивному сердечку шлёт POST и не эмитит removed', async () => {
    api.post.mockResolvedValue({})
    const wrapper = mountCard({ id: 2, name: 'Plain Product', price: 4999, stock: 5 })

    await wrapper.find('[data-testid="favorite-button"]').trigger('click')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/favorites/add/2')
    expect(api.delete).not.toHaveBeenCalled()
    expect(wrapper.emitted('removed')).toBeUndefined()
  })

  it('активное сердечко закрашено (fill currentColor), неактивное — без заливки', () => {
    const active = mountCard({ id: 1, name: 'Fav', price: 100, stock: 1, is_favorite: true })
    const activeBtn = active.find('[data-testid="favorite-button"]')
    expect(activeBtn.classes()).toContain('product-card__heart--active')
    expect(activeBtn.find('svg').attributes('fill')).toBe('currentColor')

    const inactive = mountCard({ id: 2, name: 'Plain', price: 100, stock: 1 })
    const inactiveBtn = inactive.find('[data-testid="favorite-button"]')
    expect(inactiveBtn.classes()).not.toContain('product-card__heart--active')
    expect(inactiveBtn.find('svg').attributes('fill')).toBe('none')
  })

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
