import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import Favorites from '@/views/Favorites.vue'
import ProductCard from '@/components/ProductCard.vue'

const mockFavorites = [
  {
    id: 1,
    product: { id: 10, name: 'Favorite Product', price: 5999, stock: 3 },
  },
]

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn((url) => {
      if (url === '/favorites/') {
        return Promise.resolve({ data: mockFavorites })
      }
      return Promise.resolve({ data: [] })
    }),
    post: vi.fn(),
    delete: vi.fn(),
  },
}))

describe('Favorites.vue', () => {
  it('отображает заголовок "Избранное"', async () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [{ path: '/favorites', component: Favorites }],
    })
    await router.push('/favorites')
    await router.isReady()

    const wrapper = mount(Favorites, {
      global: { plugins: [router] },
    })

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('Избранное')
    })
  })

  it('отображает избранные товары', async () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [{ path: '/favorites', component: Favorites }],
    })
    await router.push('/favorites')
    await router.isReady()

    const wrapper = mount(Favorites, {
      global: { plugins: [router] },
    })

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('Favorite Product')
    })
  })

  it('удаляет карточку из списка после события removed', async () => {
    const router = createRouter({
      history: createWebHistory(),
      routes: [{ path: '/favorites', component: Favorites }],
    })
    await router.push('/favorites')
    await router.isReady()

    const wrapper = mount(Favorites, {
      global: { plugins: [router] },
    })

    await vi.waitFor(() => {
      expect(wrapper.findComponent(ProductCard).exists()).toBe(true)
    })

    wrapper.findComponent(ProductCard).vm.$emit('removed', 10)
    await nextTick()

    expect(wrapper.findComponent(ProductCard).exists()).toBe(false)
    expect(wrapper.find('[data-testid="favorites-empty"]').exists()).toBe(true)
  })

  it('отображает пустое состояние', async () => {
    const { default: api } = await import('@/services/api')
    api.get.mockImplementationOnce(() => Promise.resolve({ data: [] }))

    const router = createRouter({
      history: createWebHistory(),
      routes: [{ path: '/favorites', component: Favorites }],
    })
    await router.push('/favorites')
    await router.isReady()

    const wrapper = mount(Favorites, {
      global: { plugins: [router] },
    })

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('У вас пока нет избранных товаров')
    })
  })
})
