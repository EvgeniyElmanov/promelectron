import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createMemoryHistory } from 'vue-router';
import HomeView from '@/views/HomeView.vue';

vi.mock('@/services/api', () => ({
  default: { get: vi.fn() },
}));

import api from '@/services/api';

const mockCategories = [
  { id: 1, name: 'Ноутбуки и компьютеры', parent_id: null, product_count: 312, image_url: null },
  { id: 2, name: 'Смартфоны и гаджеты', parent_id: null, product_count: 428, image_url: '/uploads/phones.png' },
  { id: 3, name: 'Кабели', parent_id: 1, product_count: 10 },
];

const mountView = async (url = '/') => {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/', component: HomeView }],
  });
  await router.push(url);
  await router.isReady();
  return mount(HomeView, {
    global: {
      plugins: [router],
      stubs: {
        ProductCard: { template: '<div data-testid="product-card" />', props: ['product'] },
        SkeletonProductCard: { template: '<div />' },
      },
    },
  });
};

beforeEach(() => {
  vi.clearAllMocks();
  api.get.mockImplementation((url) => {
    if (url === '/categories/') {
      return Promise.resolve({ data: { items: mockCategories, total: 3 } });
    }
    if (url === '/products/') {
      return Promise.resolve({
        data: { items: [{ id: 1, name: 'Laptop', price: 89990, stock: 5, images: ['/uploads/l1.png'] }], total: 1 },
      });
    }
    return Promise.resolve({ data: { items: [] } });
  });
});

describe('HomeView (D-02, §22)', () => {
  it('рендерит все секции витрины и не содержит инлайн-каталога', async () => {
    const wrapper = await mountView();
    await flushPromises();

    expect(wrapper.find('[data-testid="hero-banner"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="promo-stack"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="benefits-strip"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="popular-categories"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="popular-products"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="home-consultation"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="app-footer"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="filter-panel"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="sort-select"]').exists()).toBe(false);
  });

  it('резолвит id категорий ноутбуков/смартфонов по имени (D-05/D-06)', async () => {
    const wrapper = await mountView();
    await flushPromises();

    const hero = wrapper.findComponent({ name: 'HeroBanner' });
    expect(hero.props('categoryId')).toBe(1);
    const promo = wrapper.findComponent({ name: 'PromoStack' });
    expect(promo.props('smartphonesCategoryId')).toBe(2);
    expect(promo.props('smartphonesImageUrl')).toBe('/uploads/phones.png?size=medium');
  });

  it('hero-фото берётся из первого товара категории ноутбуков с images', async () => {
    const wrapper = await mountView();
    await flushPromises();
    const hero = wrapper.findComponent({ name: 'HeroBanner' });
    await vi.waitFor(() => {
      expect(hero.props('imageUrl')).toBe('/uploads/l1.png?size=medium');
    });
  });

  it('fallback: без категории «ноутбуки» CTA и фото не ломают страницу', async () => {
    api.get.mockImplementation((url) => {
      if (url === '/categories/') return Promise.resolve({ data: { items: [], total: 0 } });
      return Promise.resolve({ data: { items: [], total: 0 } });
    });
    const wrapper = await mountView();
    await flushPromises();
    const hero = wrapper.findComponent({ name: 'HeroBanner' });
    expect(hero.props('categoryId')).toBe(null);
    expect(hero.props('imageUrl')).toBe(null);
  });

  it('/?tab=sale открывает таб «Скидки» секции популярных товаров (D-06/D-10)', async () => {
    const wrapper = await mountView('/?tab=sale');
    await flushPromises();
    expect(wrapper.find('[data-testid="products-tab-sale-empty"]').exists()).toBe(true);
  });

  it('при падении /categories/ страница рендерится (S-05)', async () => {
    api.get.mockImplementation((url) => {
      if (url === '/categories/') return Promise.reject(new Error('network'));
      return Promise.resolve({ data: { items: [], total: 0 } });
    });
    const wrapper = await mountView();
    await flushPromises();
    expect(wrapper.find('[data-testid="home-view"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="popular-categories"]').exists()).toBe(false);
  });
});
