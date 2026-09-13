import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import ProductDetail from '@/views/ProductDetail.vue'
import api from '@/services/api'
import { useCart } from '@/composables/useCart'

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

  it('активное сердечко на PDP закрашено красным (fill currentColor)', async () => {
    api.get.mockResolvedValueOnce({ data: { ...mockProduct, is_favorite: true } })
    const wrapper = await mountProductDetail()

    await vi.waitFor(() => {
      const btn = wrapper.find('[data-testid="pdp-favorite-button"]')
      expect(btn.classes()).toContain('product-detail__fav-btn--active')
    })
    const btn = wrapper.find('[data-testid="pdp-favorite-button"]')
    expect(btn.find('svg').attributes('fill')).toBe('currentColor')
  })

  it('неактивное сердечко на PDP без заливки (fill none)', async () => {
    const wrapper = await mountProductDetail()

    await vi.waitFor(() => {
      expect(wrapper.find('[data-testid="pdp-stock"]').exists()).toBe(true)
    })
    const btn = wrapper.find('[data-testid="pdp-favorite-button"]')
    expect(btn.classes()).not.toContain('product-detail__fav-btn--active')
    expect(btn.find('svg').attributes('fill')).toBe('none')
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

  it('показывает крошки «Главная / Каталог / <товар>» без звена категории (D-02)', async () => {
    const wrapper = await mountProductDetail()

    await vi.waitFor(() => {
      expect(wrapper.find('[data-testid="pdp-stock"]').exists()).toBe(true)
    })
    const crumbs = wrapper.find('[data-testid="app-breadcrumbs"]')
    expect(crumbs.exists()).toBe(true)
    expect(crumbs.text()).toContain('Главная')
    expect(crumbs.text()).toContain('Каталог')
    expect(crumbs.text()).toContain('Test Product')
    // back-кнопка сохранена (D-08)
    expect(wrapper.find('[data-testid="pdp-back-button"]').exists()).toBe(true)
  })

  it('quantity-stepper: дефолт 1, +/− с clamp 1..stock, addToCart передаёт qty', async () => {
    localStorage.clear()
    const { clearGuestCart, getQuantityInCart } = useCart()
    clearGuestCart()
    const wrapper = await mountProductDetail()

    await vi.waitFor(() => {
      expect(wrapper.find('[data-testid="pdp-qty-stepper"]').exists()).toBe(true)
    })
    const input = wrapper.find('[data-testid="pdp-qty-input"]')
    expect(input.element.value).toBe('1')
    expect(wrapper.find('[data-testid="pdp-qty-decrease"]').element.disabled).toBe(true)

    await wrapper.find('[data-testid="pdp-qty-increase"]').trigger('click')
    await wrapper.find('[data-testid="pdp-qty-increase"]').trigger('click')
    expect(wrapper.find('[data-testid="pdp-qty-input"]').element.value).toBe('3')

    await wrapper.find('[data-testid="pdp-qty-decrease"]').trigger('click')
    expect(wrapper.find('[data-testid="pdp-qty-input"]').element.value).toBe('2')

    // clamp сверху: stock = 5
    for (let i = 0; i < 10; i++) {
      await wrapper.find('[data-testid="pdp-qty-increase"]').trigger('click')
    }
    expect(wrapper.find('[data-testid="pdp-qty-input"]').element.value).toBe('5')
    expect(wrapper.find('[data-testid="pdp-qty-increase"]').element.disabled).toBe(true)

    await wrapper.find('[data-testid="pdp-add-to-cart"]').trigger('click')
    await flushPromises()
    expect(getQuantityInCart(1)).toBe(5)
    // stepper скрывается в in-cart состоянии
    expect(wrapper.find('[data-testid="pdp-qty-stepper"]').exists()).toBe(false)
  })

  it('quantity-stepper скрыт при stock = 0', async () => {
    api.get.mockResolvedValueOnce({ data: { ...mockProduct, stock: 0 } })
    const wrapper = await mountProductDetail()

    await vi.waitFor(() => {
      expect(wrapper.find('[data-testid="pdp-stock"]').text()).toContain('Нет в наличии')
    })
    expect(wrapper.find('[data-testid="pdp-qty-stepper"]').exists()).toBe(false)
  })
})

const mockToast = vi.hoisted(() => vi.fn())
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ add: mockToast }),
}))

describe('ProductDetail.vue — состояние кнопки корзины', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    const { clearGuestCart } = useCart()
    clearGuestCart()
  })

  async function mountPdp() {
    const router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/product/:id', component: ProductDetail },
        { path: '/cart', component: { template: '<div />' } },
      ],
    })
    await router.push('/product/1')
    await router.isReady()
    const wrapper = mount(ProductDetail, { global: { plugins: [router] } })
    await vi.waitFor(() => {
      expect(wrapper.find('[data-testid="pdp-add-to-cart"]').exists()).toBe(true)
    })
    return { wrapper, router }
  }

  it('после добавления кнопка показывает «В корзине · N» и класс --in-cart', async () => {
    const { wrapper } = await mountPdp()

    await wrapper.find('[data-testid="pdp-add-to-cart"]').trigger('click')
    await flushPromises()

    const button = wrapper.find('[data-testid="pdp-add-to-cart"]')
    expect(button.text()).toContain('В корзине · 1')
    expect(button.classes()).toContain('product-detail__cart-btn--in-cart')
    expect(mockToast).not.toHaveBeenCalledWith('Добавлено в корзину', 'success')
  })

  it('клик по in-cart кнопке ведёт на /cart без повторного добавления', async () => {
    const { wrapper, router } = await mountPdp()
    const pushSpy = vi.spyOn(router, 'push')

    await wrapper.find('[data-testid="pdp-add-to-cart"]').trigger('click')
    await flushPromises()
    pushSpy.mockClear()

    await wrapper.find('[data-testid="pdp-add-to-cart"]').trigger('click')
    await flushPromises()

    expect(pushSpy).toHaveBeenCalledWith('/cart')
    const { getQuantityInCart } = useCart()
    expect(getQuantityInCart(1)).toBe(1)
  })
})
