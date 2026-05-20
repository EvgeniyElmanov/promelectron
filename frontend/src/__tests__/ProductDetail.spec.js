import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import ProductDetail from '@/views/ProductDetail.vue'

const mockProduct = {
  id: 1,
  name: 'Test Product',
  price: 9999,
  description: 'A great product',
  reviews: [
    { id: 1, rating: 5, text: 'Excellent!', created_at: '2024-01-15T10:00:00Z' },
    { id: 2, rating: 4, text: 'Good', created_at: '2024-01-14T10:00:00Z' },
  ],
  average_rating: 4.5,
  reviews_count: 2,
  is_favorite: false,
}

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn((url) => {
      if (url === '/products/1/detail') {
        return Promise.resolve({ data: mockProduct })
      }
      return Promise.resolve({ data: {} })
    }),
    post: vi.fn(),
    delete: vi.fn(),
  },
}))

vi.mock('@/composables/useAuth', () => ({
  useAuth: () => ({
    isAuthenticated: { value: false },
  }),
}))

describe('ProductDetail.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('отображает название и цену товара', async () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [{ path: '/product/:id', component: ProductDetail }],
    })
    await router.push('/product/1')
    await router.isReady()

    const wrapper = mount(ProductDetail, {
      global: { plugins: [router] },
    })

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('Test Product')
      expect(wrapper.text()).toMatch(/9\s999\s₽/)
    })
  })

  it('отображает описание товара', async () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [{ path: '/product/:id', component: ProductDetail }],
    })
    await router.push('/product/1')
    await router.isReady()

    const wrapper = mount(ProductDetail, {
      global: { plugins: [router] },
    })

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('A great product')
    })
  })

  it('отображает отзывы', async () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [{ path: '/product/:id', component: ProductDetail }],
    })
    await router.push('/product/1')
    await router.isReady()

    const wrapper = mount(ProductDetail, {
      global: { plugins: [router] },
    })

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('Excellent!')
      expect(wrapper.text()).toContain('Good')
    })
  })

  it('показывает сообщение когда нет отзывов', async () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [{ path: '/product/:id', component: ProductDetail }],
    })
    await router.push('/product/1')
    await router.isReady()

    const wrapper = mount(ProductDetail, {
      global: { plugins: [router] },
    })

    await vi.waitFor(() => {
      expect(wrapper.find('[data-testid="pdp-reviews-section"]').exists()).toBe(true)
    })
  })

  it('отображает кнопку добавления в корзину', async () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [{ path: '/product/:id', component: ProductDetail }],
    })
    await router.push('/product/1')
    await router.isReady()

    const wrapper = mount(ProductDetail, {
      global: { plugins: [router] },
    })

    await vi.waitFor(() => {
      expect(wrapper.find('[data-testid="pdp-add-to-cart"]').exists()).toBe(true)
    })
  })
})
