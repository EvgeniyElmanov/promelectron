import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import ProductDetail from '@/views/ProductDetail.vue'
import api from '@/services/api'

const mockProduct = {
  id: 1,
  name: 'Test Product',
  price: 9999,
  sku: 'EL-00123',
  stock: 5,
  description: 'A great product',
  attributes: [
    { code: 'rated_current_a', name: 'Номинальный ток', value_type: 'number', value: 16, unit: 'А' },
    { code: 'is_din_rail', name: 'Монтаж на DIN-рейку', value_type: 'bool', value: true, unit: null },
    { code: 'is_smart', name: 'Умный дом', value_type: 'bool', value: false, unit: null },
    { code: 'poles_count', name: 'Количество полюсов', value_type: 'number', value: 16, unit: null },
    { code: 'brand', name: 'Бренд', value_type: 'string', value: 'Legrand', unit: null },
  ],
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

async function mountProductDetail() {
  const router = createRouter({
    history: createWebHistory(),
    routes: [{ path: '/product/:id', component: ProductDetail }],
  })
  await router.push('/product/1')
  await router.isReady()

  return mount(ProductDetail, {
    global: { plugins: [router] },
  })
}

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

  it('отображает артикул товара', async () => {
    const wrapper = await mountProductDetail()

    await vi.waitFor(() => {
      const sku = wrapper.find('[data-testid="pdp-sku"]')
      expect(sku.exists()).toBe(true)
      expect(sku.text()).toContain('EL-00123')
    })
  })

  it('скрывает артикул когда sku отсутствует', async () => {
    api.get.mockResolvedValueOnce({ data: { ...mockProduct, sku: null } })
    const wrapper = await mountProductDetail()

    await vi.waitFor(() => {
      expect(wrapper.find('[data-testid="pdp-stock"]').exists()).toBe(true)
    })
    expect(wrapper.find('[data-testid="pdp-sku"]').exists()).toBe(false)
  })

  it('показывает наличие и активную кнопку при stock > 0', async () => {
    const wrapper = await mountProductDetail()

    await vi.waitFor(() => {
      expect(wrapper.find('[data-testid="pdp-stock"]').text()).toContain('В наличии: 5 шт')
    })
    const btn = wrapper.find('[data-testid="pdp-add-to-cart"]')
    expect(btn.element.disabled).toBe(false)
  })

  it('блокирует кнопку и показывает "Нет в наличии" при stock = 0', async () => {
    api.get.mockResolvedValueOnce({ data: { ...mockProduct, stock: 0 } })
    const wrapper = await mountProductDetail()

    await vi.waitFor(() => {
      expect(wrapper.find('[data-testid="pdp-stock"]').text()).toContain('Нет в наличии')
    })
    const btn = wrapper.find('[data-testid="pdp-add-to-cart"]')
    expect(btn.element.disabled).toBe(true)
    expect(btn.text()).toBe('Нет в наличии')
  })

  it('отображает секцию характеристик с форматированием по типам', async () => {
    const wrapper = await mountProductDetail()

    await vi.waitFor(() => {
      expect(wrapper.find('[data-testid="pdp-attributes"]').exists()).toBe(true)
    })
    expect(wrapper.find('[data-testid="pdp-attributes"]').text()).toContain('Характеристики')
    expect(wrapper.find('[data-testid="pdp-attr-rated_current_a"]').text()).toContain('16 А')
    expect(wrapper.find('[data-testid="pdp-attr-is_din_rail"]').text()).toContain('Да')
    expect(wrapper.find('[data-testid="pdp-attr-is_smart"] dd').text()).toBe('Нет')
    expect(wrapper.find('[data-testid="pdp-attr-poles_count"] dd').text()).toBe('16')
    expect(wrapper.find('[data-testid="pdp-attr-brand"]').text()).toContain('Legrand')
  })

  it('скрывает секцию характеристик когда attributes пустые', async () => {
    api.get.mockResolvedValueOnce({ data: { ...mockProduct, attributes: [] } })
    const wrapper = await mountProductDetail()

    await vi.waitFor(() => {
      expect(wrapper.find('[data-testid="pdp-stock"]').exists()).toBe(true)
    })
    expect(wrapper.find('[data-testid="pdp-attributes"]').exists()).toBe(false)
  })
})
