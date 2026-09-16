import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import ProductCard from '@/components/ProductCard.vue'
import api from '@/services/api'
import { useCart } from '@/composables/useCart'

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

const mockToast = vi.hoisted(() => vi.fn())
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ add: mockToast }),
}))

describe('ProductCard.vue', () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    localStorage.clear()
    api.get.mockResolvedValue({ data: { items: [] } })
    const { clearGuestCart, syncCartCount } = useCart()
    clearGuestCart()
    await syncCartCount()
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

describe('ProductCard.vue — состояние кнопки корзины', () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    localStorage.clear()
    api.get.mockResolvedValue({ data: { items: [] } })
    const { clearGuestCart, syncCartCount } = useCart()
    clearGuestCart()
    await syncCartCount()
  })

  function mountCard(product) {
    const router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/', component: ProductCard },
        { path: '/cart', component: { template: '<div />' } },
      ],
    })
    return mount(ProductCard, {
      global: { plugins: [router] },
      props: { product },
    })
  }

  it('после добавления кнопка показывает «В корзине · N» и класс --in-cart', async () => {
    api.post.mockResolvedValue({})
    api.get.mockResolvedValue({ data: { items: [{ product_id: 1, quantity: 2 }] } })
    const wrapper = mountCard({ id: 1, name: 'P', price: 100, stock: 5 })

    await wrapper.find('[data-testid="add-to-cart-button"]').trigger('click')
    await flushPromises()

    const button = wrapper.find('[data-testid="add-to-cart-button"]')
    expect(button.text()).toContain('В корзине · 2')
    expect(button.classes()).toContain('product-card__cart-btn--in-cart')
    expect(button.attributes('disabled')).toBeUndefined()
  })

  it('клик по in-cart кнопке ведёт на /cart без повторного добавления', async () => {
    api.get.mockResolvedValue({ data: { items: [{ product_id: 1, quantity: 1 }] } })
    const { syncCartCount } = useCart()
    await syncCartCount()

    const router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/', component: ProductCard },
        { path: '/cart', component: { template: '<div />' } },
      ],
    })
    const pushSpy = vi.spyOn(router, 'push')
    const wrapper = mount(ProductCard, {
      global: { plugins: [router] },
      props: { product: { id: 1, name: 'P', price: 100, stock: 5 } },
    })

    await wrapper.find('[data-testid="add-to-cart-button"]').trigger('click')
    await flushPromises()

    expect(pushSpy).toHaveBeenCalledWith('/cart')
    expect(api.post).not.toHaveBeenCalled()
  })

  it('success-тост «Добавлено в корзину» не показывается', async () => {
    api.post.mockResolvedValue({})
    const wrapper = mountCard({ id: 1, name: 'P', price: 100, stock: 5 })

    await wrapper.find('[data-testid="add-to-cart-button"]').trigger('click')
    await flushPromises()

    expect(mockToast).not.toHaveBeenCalledWith('Добавлено в корзину', 'success')
  })

  it('error-тост корзины остался при ошибке добавления', async () => {
    api.post.mockRejectedValue(new Error('fail'))
    const wrapper = mountCard({ id: 1, name: 'P', price: 100, stock: 5 })

    await wrapper.find('[data-testid="add-to-cart-button"]').trigger('click')
    await flushPromises()

    expect(mockToast).toHaveBeenCalledWith('Не удалось добавить в корзину', 'error')
  })

  it('тосты успеха избранного не показываются, error-тост остался', async () => {
    api.post.mockResolvedValue({})
    api.delete.mockResolvedValue({})
    const wrapper = mountCard({ id: 1, name: 'P', price: 100, stock: 5, is_favorite: true })

    await wrapper.find('[data-testid="favorite-button"]').trigger('click')
    await flushPromises()
    expect(mockToast).not.toHaveBeenCalledWith('Удалено из избранного', 'info')
    expect(mockToast).not.toHaveBeenCalledWith('Добавлено в избранное', 'success')

    api.post.mockRejectedValue(new Error('fail'))
    await wrapper.find('[data-testid="favorite-button"]').trigger('click')
    await flushPromises()
    expect(mockToast).toHaveBeenCalledWith('Не удалось обновить избранное', 'error')
  })
})

describe('ProductCard.vue (§13, D-03/D-04/D-09)', () => {
  function mountCard2(product) {
    const router = createRouter({
      history: createWebHistory(),
      routes: [{ path: '/', component: ProductCard }],
    })
    return mount(ProductCard, {
      global: { plugins: [router] },
      props: { product },
    })
  }

  it('рендерит бренд, рейтинг и «В наличии» только при наличии данных', () => {
    const full = mountCard2({ id: 1, name: 'P', price: 1000, stock: 3, brand: 'Samsung', average_rating: 4.7, reviews_count: 128 })
    expect(full.find('[data-testid="product-brand"]').text()).toBe('Samsung')
    expect(full.find('[data-testid="product-rating"]').text()).toContain('4.7')
    expect(full.find('[data-testid="product-rating"]').text()).toContain('(128)')
    expect(full.find('[data-testid="stock-status"]').text()).toBe('В наличии')

    const bare = mountCard2({ id: 2, name: 'P2', price: 1000, stock: 3 })
    expect(bare.find('[data-testid="product-brand"]').exists()).toBe(false)
    expect(bare.find('[data-testid="product-rating"]').exists()).toBe(false)
    expect(bare.find('[data-testid="stock-status"]').text()).toBe('В наличии')
  })

  it('бейджи ХИТ/НОВИНКА/−N% — только по данным (макс. приоритет: sale, hit, new)', () => {
    const hit = mountCard2({ id: 1, name: 'P', price: 1000, stock: 3, is_hit: true })
    expect(hit.find('[data-testid="hit-badge"]').text()).toBe('ХИТ')

    const isNew = mountCard2({ id: 2, name: 'P', price: 1000, stock: 3, is_new: true })
    expect(isNew.find('[data-testid="new-badge"]').text()).toBe('НОВИНКА')

    const sale = mountCard2({ id: 3, name: 'P', price: 1000, old_price: 1250, stock: 3 })
    expect(sale.find('[data-testid="sale-badge"]').text()).toBe('−20%')
    expect(sale.find('[data-testid="product-old-price"]').exists()).toBe(true)

    const bare = mountCard2({ id: 4, name: 'P', price: 1000, stock: 3 })
    expect(bare.find('[data-testid="hit-badge"]').exists()).toBe(false)
    expect(bare.find('[data-testid="new-badge"]').exists()).toBe(false)
    expect(bare.find('[data-testid="sale-badge"]').exists()).toBe(false)
    expect(bare.find('[data-testid="product-old-price"]').exists()).toBe(false)
  })

  it('«Нет в наличии» текстом при stock=0', () => {
    const wrapper = mountCard2({ id: 1, name: 'P', price: 1000, stock: 0 })
    expect(wrapper.find('[data-testid="stock-status"]').text()).toBe('Нет в наличии')
  })

  it('иконка сравнения неактивна (aria-disabled + tooltip, D-09)', () => {
    const wrapper = mountCard2({ id: 1, name: 'P', price: 1000, stock: 3 })
    const btn = wrapper.find('[data-testid="compare-button"]')
    expect(btn.exists()).toBe(true)
    expect(btn.attributes('aria-disabled')).toBe('true')
    expect(btn.attributes('title')).toBe('Сравнение скоро появится')
  })
})
