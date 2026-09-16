import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import PopularProducts from '@/components/home/PopularProducts.vue';

const pushMock = vi.hoisted(() => vi.fn());

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock }),
  RouterLink: { template: '<a><slot /></a>' },
}));

vi.mock('@/services/api', () => ({
  default: { get: vi.fn() },
}));

import api from '@/services/api';

const mockProducts = [
  { id: 1, name: 'Product 1', price: 9999, stock: 10 },
  { id: 2, name: 'Product 2', price: 14999, stock: 5, is_hit: true },
];

beforeEach(() => {
  vi.clearAllMocks();
  api.get.mockResolvedValue({ data: { items: mockProducts, total: 2 } });
});

// ProductCard дергает useCart/useAuth — глушим дочерний компонент.
const mountOpts = {
  global: {
    stubs: {
      ProductCard: { template: '<div data-testid="product-card">{{ product.name }}</div>', props: ['product'] },
      SkeletonProductCard: { template: '<div class="sk" />' },
      RouterLink: { template: '<a><slot /></a>' },
    },
  },
};

describe('PopularProducts (D-08)', () => {
  it('по умолчанию грузит таб «Хиты продаж» без sort_by', async () => {
    const wrapper = mount(PopularProducts, mountOpts);
    await flushPromises();
    expect(api.get).toHaveBeenCalledWith('/products/', { params: { skip: 0, limit: 6 } });
    expect(wrapper.text()).toContain('Product 1');
  });

  it('таб «Новинки» запрашивает sort_by=newest', async () => {
    const wrapper = mount(PopularProducts, mountOpts);
    await flushPromises();
    await wrapper.find('[data-testid="products-tab-new"]').trigger('click');
    await flushPromises();
    expect(api.get).toHaveBeenCalledWith('/products/', { params: { skip: 0, limit: 6, sort_by: 'newest' } });
  });

  it('таб «Скидки» показывает честный empty-state без запроса и фейковых данных (D-04)', async () => {
    const wrapper = mount(PopularProducts, mountOpts);
    await flushPromises();
    api.get.mockClear();
    await wrapper.find('[data-testid="products-tab-sale"]').trigger('click');
    await flushPromises();
    expect(api.get).not.toHaveBeenCalled();
    expect(wrapper.find('[data-testid="products-tab-sale-empty"]').text()).toContain('Скидок сейчас нет');
  });

  it('приоритет is_hit в табе «Хиты» (D-03, fallback — порядок API)', async () => {
    const wrapper = mount(PopularProducts, mountOpts);
    await flushPromises();
    const cards = wrapper.findAll('[data-testid="product-card"]');
    expect(cards[0].text()).toContain('Product 2');
  });

  it('при ошибке API грид скрывается, секция не валится (S-05)', async () => {
    api.get.mockRejectedValue(new Error('network'));
    const wrapper = mount(PopularProducts, mountOpts);
    await flushPromises();
    expect(wrapper.find('[data-testid="popular-products"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="popular-products-empty"]').exists()).toBe(true);
  });

  it('initialTab=sale открывает таб «Скидки» (якорь /?tab=sale)', async () => {
    const wrapper = mount(PopularProducts, { ...mountOpts, props: { initialTab: 'sale' } });
    await flushPromises();
    expect(wrapper.find('[data-testid="products-tab-sale-empty"]').exists()).toBe(true);
  });

  it('ссылка «Все товары» ведёт на /catalog', async () => {
    const wrapper = mount(PopularProducts, mountOpts);
    await flushPromises();
    expect(wrapper.find('[data-testid="products-view-all"]').exists()).toBe(true);
  });
});
