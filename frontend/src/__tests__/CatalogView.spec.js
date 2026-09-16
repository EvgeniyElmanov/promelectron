import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory, createMemoryHistory } from 'vue-router'
import CatalogView from '@/views/CatalogView.vue'
import { __resetSearchProbeForTests } from '@/composables/useCatalogSearch'

const mockProducts = [
  { id: 1, name: 'Product 1', price: 9999, stock: 10 },
  { id: 2, name: 'Product 2', price: 14999, stock: 5 },
]

const mockCategories = [
  { id: 1, name: 'Электроника', description: null, parent_id: null },
  { id: 2, name: 'Одежда', description: null, parent_id: null },
]

const mockSearchResponse = {
  items: [
    { id: 1, sku: 'SKU-1', name: 'Search Product 1', price: 9999, stock: 10, category_id: 1, categories: {}, attrs: {} },
  ],
  total: 1,
  page: 1,
  pages: 1,
  facets: [
    {
      code: 'brand',
      name: 'Бренд',
      value_type: 'enum',
      values: [
        { value: 'Samsung', count: 5 },
        { value: 'LG', count: 3 },
      ],
    },
  ],
}

const mocks = vi.hoisted(() => ({ searchEnabled: false }))

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn((url) => {
      if (url === '/search/') {
        if (!mocks.searchEnabled) {
          const err = new Error('Not Found')
          err.response = { status: 404 }
          return Promise.reject(err)
        }
        return Promise.resolve({ data: mockSearchResponse })
      }
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

beforeEach(() => {
  mocks.searchEnabled = false
  __resetSearchProbeForTests()
})

function mountWithWebHistory() {
  const router = createRouter({
    history: createWebHistory(),
    routes: [{ path: '/', component: CatalogView }],
  })

  return mount(CatalogView, {
    global: {
      plugins: [router],
    },
  })
}

describe('CatalogView.vue (legacy /products/ при выключенном флаге)', () => {
  it('отображает заголовок "Популярные товары"', async () => {
    const wrapper = mountWithWebHistory()

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('Популярные товары')
    })
  })

  it('отображает строку поиска', async () => {
    const wrapper = mountWithWebHistory()

    const input = wrapper.find('input[type="text"]')
    expect(input.exists()).toBe(true)
    expect(input.attributes('placeholder')).toBe('Поиск товаров...')
  })

  it('отображает карточки товаров', async () => {
    const wrapper = mountWithWebHistory()

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('Product 1')
      expect(wrapper.text()).toContain('Product 2')
    })
  })

  it('отображает количество товаров', async () => {
    const wrapper = mountWithWebHistory()

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('2 товаров')
    })
  })

  it('отображает фильтр по рейтингу', async () => {
    const wrapper = mountWithWebHistory()

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('Рейтинг:')
    })

    for (let i = 1; i <= 5; i++) {
      expect(wrapper.find(`[data-testid="rating-filter-${i}"]`).exists()).toBe(true)
    }
  })

  it('отображает селектор сортировки с новыми опциями', async () => {
    const wrapper = mountWithWebHistory()

    const select = wrapper.find('[data-testid="sort-select"]')
    expect(select.exists()).toBe(true)

    const options = select.findAll('option')
    const values = options.map(o => o.attributes('value'))
    expect(values).toContain('rating_desc')
    expect(values).toContain('name_asc')
  })

  it('при 404 на /search/ FilterPanel не рендерится (fallback)', async () => {
    const wrapper = mountWithWebHistory()

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('Product 1')
    })
    expect(wrapper.find('[data-testid="filter-panel"]').exists()).toBe(false)
  })
})

describe('CatalogView.vue (search-режим при включённом флаге)', () => {
  const originalMatchMedia = window.matchMedia

  beforeEach(() => {
    mocks.searchEnabled = true
  })

  afterEach(() => {
    window.matchMedia = originalMatchMedia
  })

  function stubMatchMedia(matches) {
    window.matchMedia = vi.fn().mockImplementation((query) => ({
      matches,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
    }))
  }

  async function mountSearchMode(url = '/') {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/', component: CatalogView }],
    })
    await router.push(url)
    await router.isReady()
    return mount(CatalogView, {
      global: {
        plugins: [router],
      },
    })
  }

  it('рендерит FilterPanel и скрывает legacy-фильтры', async () => {
    const wrapper = await mountSearchMode()

    await vi.waitFor(() => {
      expect(wrapper.find('[data-testid="filter-panel"]').exists()).toBe(true)
    })
    expect(wrapper.find('[data-testid="rating-filter-1"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="min-price-input"]').exists()).toBe(false)
    // rating_desc недоступен в search-режиме (backend не поддерживает)
    const values = wrapper.find('[data-testid="sort-select"]').findAll('option').map(o => o.attributes('value'))
    expect(values).not.toContain('rating_desc')
  })

  it('показывает товары и счётчики фасетов из /search/', async () => {
    const wrapper = await mountSearchMode()

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('Search Product 1')
      expect(wrapper.text()).toContain('1 товаров')
      expect(wrapper.text()).toContain('(5)')
    })
  })

  it('восстанавливает выбранный фасет из URL query', async () => {
    const wrapper = await mountSearchMode('/?attr.brand=Samsung')

    await vi.waitFor(() => {
      expect(wrapper.find('[data-testid="filter-panel"]').exists()).toBe(true)
    })
    const checkbox = wrapper.find('[data-testid="filter-value-brand-0"]')
    expect(checkbox.element.checked).toBe(true)
  })

  it('сворачивает панель фильтров по умолчанию на мобилке (<768px)', async () => {
    stubMatchMedia(false)
    const wrapper = await mountSearchMode()

    await vi.waitFor(() => {
      expect(wrapper.find('[data-testid="filter-panel"]').exists()).toBe(true)
    })
    const details = wrapper.find('details.home__filter-panel-wrap')
    expect(details.exists()).toBe(true)
    expect(details.attributes('open')).toBeUndefined()
  })

  it('оставляет панель фильтров развёрнутой по умолчанию на десктопе (>=768px)', async () => {
    stubMatchMedia(true)
    const wrapper = await mountSearchMode()

    await vi.waitFor(() => {
      expect(wrapper.find('[data-testid="filter-panel"]').exists()).toBe(true)
    })
    const details = wrapper.find('details.home__filter-panel-wrap')
    expect(details.exists()).toBe(true)
    expect(details.attributes('open')).toBeDefined()
  })

  it('не закрывает панель при toggle вложенного <details> внутри FilterPanel', async () => {
    stubMatchMedia(true)
    const wrapper = await mountSearchMode()

    await vi.waitFor(() => {
      expect(wrapper.find('[data-testid="filter-panel"]').exists()).toBe(true)
    })
    const outer = wrapper.find('details.home__filter-panel-wrap')
    expect(outer.attributes('open')).toBeDefined()

    // toggle у <details> всплывает — имитируем сворачивание внутренней группы фильтров
    const nested = wrapper.find('details.home__filter-panel-wrap details')
    expect(nested.exists()).toBe(true)
    nested.element.open = false
    nested.element.dispatchEvent(new Event('toggle', { bubbles: true }))
    await wrapper.vm.$nextTick()

    expect(outer.attributes('open')).toBeDefined()
  })
})

describe('CatalogView.vue (структура каталога, D-02)', () => {
  it('рендерит листинг и footer без витринных секций главной', async () => {
    const wrapper = mountWithWebHistory()

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('Product 1')
    })
    expect(wrapper.find('[data-testid="app-footer"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="hero-banner"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="benefits-strip"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="popular-categories"]').exists()).toBe(false)
  })

  it('таб «Новинки» переключает сортировку на newest (legacy-режим)', async () => {
    const api = (await import('@/services/api')).default
    api.get.mockClear()
    const wrapper = mountWithWebHistory()

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('Product 1')
    })

    await wrapper.find('[data-testid="products-tab-new"]').trigger('click')

    await vi.waitFor(() => {
      const productCalls = api.get.mock.calls.filter(([url]) => url === '/products/')
      expect(productCalls.some(([, config]) => config.params.sort_by === 'newest')).toBe(true)
    })
    expect(wrapper.find('[data-testid="products-tab-new"]').classes()).toContain('home__tab--active')
    expect(wrapper.find('[data-testid="products-tab-new"]').attributes('aria-pressed')).toBe('true')
    expect(wrapper.find('[data-testid="products-tab-hits"]').attributes('aria-pressed')).toBe('false')
  })

  it('таб «Хиты продаж» сбрасывает сортировку на default', async () => {
    const api = (await import('@/services/api')).default
    api.get.mockClear()
    const wrapper = mountWithWebHistory()

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('Product 1')
    })

    await wrapper.find('[data-testid="products-tab-new"]').trigger('click')
    await wrapper.find('[data-testid="products-tab-hits"]').trigger('click')

    await vi.waitFor(() => {
      const productCalls = api.get.mock.calls.filter(([url]) => url === '/products/')
      expect(productCalls.some(([, config]) => !config.params.sort_by)).toBe(true)
    })
    expect(wrapper.find('[data-testid="products-tab-hits"]').classes()).toContain('home__tab--active')
  })

  it('клик по chip категории применяет фильтр (legacy-режим)', async () => {
    const api = (await import('@/services/api')).default
    api.get.mockClear()
    const wrapper = mountWithWebHistory()

    await vi.waitFor(() => {
      expect(wrapper.find('[data-testid="category-chip-1"]').exists()).toBe(true)
    })
    await wrapper.find('[data-testid="category-chip-1"]').trigger('click')

    await vi.waitFor(() => {
      const productCalls = api.get.mock.calls.filter(([url]) => url === '/products/')
      expect(productCalls.some(([, config]) => config.params.category_id === 1)).toBe(true)
    })
  })
})

describe('CatalogView.vue (крошки и H1, §21)', () => {
  it('показывает крошки «Главная / Каталог» и H1 «Каталог» в legacy-режиме', async () => {
    const wrapper = mountWithWebHistory()

    const crumbs = wrapper.find('[data-testid="app-breadcrumbs"]')
    expect(crumbs.exists()).toBe(true)
    expect(crumbs.text()).toContain('Главная')
    expect(crumbs.text()).toContain('Каталог')

    const h1 = wrapper.find('h1.home__title')
    expect(h1.exists()).toBe(true)
    expect(h1.text()).toBe('Каталог')
    // h2 с data-testid="products-section-title" сохранён (D-04)
    expect(wrapper.find('[data-testid="products-section-title"]').exists()).toBe(true)
  })

  it('добавляет звено категории в крошки при выбранной категории (search-режим)', async () => {
    mocks.searchEnabled = true
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/', component: CatalogView }],
    })
    await router.push('/?category_id=1')
    await router.isReady()
    const wrapper = mount(CatalogView, { global: { plugins: [router] } })

    await vi.waitFor(() => {
      expect(wrapper.find('[data-testid="filter-panel"]').exists()).toBe(true)
    })
    await vi.waitFor(() => {
      const crumbs = wrapper.find('[data-testid="app-breadcrumbs"]')
      expect(crumbs.text()).toContain('Электроника')
    })
    const crumbs = wrapper.find('[data-testid="app-breadcrumbs"]')
    expect(crumbs.text()).toContain('Главная')
    expect(crumbs.text()).toContain('Каталог')
  })
})

describe('CatalogView.vue (legacy: фильтры из URL query, F-03)', () => {
  it('восстанавливает category_id/sort/price_* из query в legacy-режиме', async () => {
    const api = (await import('@/services/api')).default
    api.get.mockClear()
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/catalog', component: CatalogView }],
    })
    await router.push('/catalog?category_id=2&sort=price_asc&price_min=1000&price_max=5000&min_rating=4')
    await router.isReady()
    const wrapper = mount(CatalogView, { global: { plugins: [router] } })

    await vi.waitFor(() => {
      const productCalls = api.get.mock.calls.filter(([url]) => url === '/products/')
      expect(productCalls.length).toBeGreaterThan(0)
      const params = productCalls[0][1].params
      expect(params.category_id).toBe(2)
      expect(params.sort_by).toBe('price_asc')
      expect(params.min_price).toBe(1000)
      expect(params.max_price).toBe(5000)
      expect(params.min_rating).toBe(4)
    })
    expect(wrapper.find('[data-testid="sort-select"]').element.value).toBe('price_asc')
  })
})

describe('CatalogView.vue (смена query у смонтированного компонента, F-07)', () => {
  it('legacy-режим: смена category_id в URL применяет фильтр без remount', async () => {
    const api = (await import('@/services/api')).default
    api.get.mockClear()
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/catalog', component: CatalogView }],
    })
    await router.push('/catalog?category_id=2')
    await router.isReady()
    mount(CatalogView, { global: { plugins: [router] } })

    await vi.waitFor(() => {
      const calls = api.get.mock.calls.filter(([url]) => url === '/products/')
      expect(calls.some(([, config]) => config.params.category_id === 2)).toBe(true)
    })

    api.get.mockClear()
    await router.push('/catalog?category_id=3')

    await vi.waitFor(() => {
      const calls = api.get.mock.calls.filter(([url]) => url === '/products/')
      expect(calls.some(([, config]) => config.params.category_id === 3)).toBe(true)
    })
  })

  it('legacy-режим: смена price_min даёт ровно один fetch, идентичный query — ни одного', async () => {
    const api = (await import('@/services/api')).default
    api.get.mockClear()
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/catalog', component: CatalogView }],
    })
    await router.push('/catalog?category_id=2')
    await router.isReady()
    mount(CatalogView, { global: { plugins: [router] } })

    await vi.waitFor(() => {
      expect(api.get.mock.calls.filter(([url]) => url === '/products/').length).toBeGreaterThan(0)
    })

    api.get.mockClear()
    await router.push('/catalog?category_id=2&price_min=100')
    await vi.waitFor(() => {
      const calls = api.get.mock.calls.filter(([url]) => url === '/products/')
      expect(calls.length).toBe(1)
      expect(calls[0][1].params.min_price).toBe(100)
    })

    api.get.mockClear()
    await router.replace('/catalog?category_id=2&price_min=100')
    await new Promise((r) => setTimeout(r, 350))
    expect(api.get.mock.calls.filter(([url]) => url === '/products/').length).toBe(0)
  })

  it('search-режим: смена category_id в URL перезагружает выдачу', async () => {
    mocks.searchEnabled = true
    const api = (await import('@/services/api')).default
    api.get.mockClear()
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/catalog', component: CatalogView }],
    })
    await router.push('/catalog?category_id=1')
    await router.isReady()
    mount(CatalogView, { global: { plugins: [router] } })

    await vi.waitFor(() => {
      const calls = api.get.mock.calls.filter(([url]) => url === '/search/')
      expect(calls.some(([, config]) => config.params?.category_id === 1)).toBe(true)
    })

    api.get.mockClear()
    await router.push('/catalog?category_id=3')

    await vi.waitFor(() => {
      const calls = api.get.mock.calls.filter(([url]) => url === '/search/')
      expect(calls.some(([, config]) => config.params?.category_id === 3)).toBe(true)
    })
  })
})
