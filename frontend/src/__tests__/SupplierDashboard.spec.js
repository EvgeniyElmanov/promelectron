import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import SupplierDashboard from '../views/SupplierDashboard.vue';

const mockGet = vi.fn();

vi.mock('@/services/api', () => ({
  default: {
    get: (...args) => mockGet(...args),
  },
}));

const toastFn = vi.fn();
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ add: toastFn }),
}));

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: { template: '<div>Home</div>' } },
    { path: '/my-products', component: { template: '<div>My Products</div>' } },
    { path: '/supplier-orders', component: { template: '<div>Supplier Orders</div>' } },
  ],
});

const mockAnalytics = {
  kpi: {
    total_orders: 150,
    pending_orders: 12,
    shipped_orders: 45,
    delivered_orders: 88,
    total_revenue: 245000,
    total_products: 32,
  },
  orders_by_day: [
    { date: '2026-04-29', orders: 2, revenue: 5000 },
    { date: '2026-04-30', orders: 4, revenue: 12000 },
    { date: '2026-05-01', orders: 3, revenue: 8000 },
    { date: '2026-05-02', orders: 6, revenue: 18000 },
    { date: '2026-05-03', orders: 5, revenue: 15000 },
    { date: '2026-05-04', orders: 7, revenue: 21000 },
    { date: '2026-05-05', orders: 4, revenue: 11000 },
  ],
  top_products: [
    { id: 1, name: 'iPhone 15 Pro', sold: 25, revenue: 224975 },
    { id: 2, name: 'AirPods Pro 2', sold: 18, revenue: 71982 },
    { id: 3, name: 'MacBook Air', sold: 10, revenue: 99990 },
    { id: 4, name: 'iPad Air', sold: 8, revenue: 47992 },
    { id: 5, name: 'Apple Watch', sold: 5, revenue: 24995 },
  ],
};

describe('SupplierDashboard.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    toastFn.mockClear();
    mockGet.mockImplementation((url) => {
      if (url === '/api/v1/analytics/supplier') return Promise.resolve({ data: mockAnalytics });
      return Promise.resolve({ data: {} });
    });
  });

  it('отображает страницу дашборда поставщика', async () => {
    const wrapper = mount(SupplierDashboard, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.find('[data-testid="supplier-dashboard-page"]').exists()).toBe(true);
    expect(wrapper.text()).toContain('Дашборд поставщика');
  });

  it('отображает KPI карточки', async () => {
    const wrapper = mount(SupplierDashboard, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.text()).toContain('Всего заказов');
    expect(wrapper.text()).toContain('150');
    expect(wrapper.text()).toContain('Ожидают отправки');
    expect(wrapper.text()).toContain('12');
    expect(wrapper.text()).toContain('Отправлено');
    expect(wrapper.text()).toContain('45');
    expect(wrapper.text()).toContain('Доставлено');
    expect(wrapper.text()).toContain('88');
    expect(wrapper.text()).toContain('Выручка');
    expect(wrapper.text()).toContain('245\u00A0000\u00A0₽');
    expect(wrapper.text()).toContain('Товаров');
    expect(wrapper.text()).toContain('32');
  });

  it('отображает график заказов по дням', async () => {
    const wrapper = mount(SupplierDashboard, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.text()).toContain('Заказы за 30 дней');
    const bars = wrapper.findAll('.supplier-dashboard__chart-bar-wrap');
    expect(bars.length).toBe(7);
  });

  it('отображает топ товаров списком', async () => {
    const wrapper = mount(SupplierDashboard, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.text()).toContain('Топ товаров');
    const items = wrapper.findAll('[data-testid="top-product-item"]');
    expect(items.length).toBe(5);
    expect(wrapper.text()).toContain('iPhone 15 Pro');
    expect(wrapper.text()).toContain('25 продано');
    expect(wrapper.text()).toContain('AirPods Pro 2');
  });

  it('отображает топ товаров таблицей', async () => {
    const wrapper = mount(SupplierDashboard, { global: { plugins: [router] } });
    await flushPromises();

    const table = wrapper.find('[data-testid="top-products-table"]');
    expect(table.exists()).toBe(true);
    expect(table.text()).toContain('Название');
    expect(table.text()).toContain('Продано');
    expect(table.text()).toContain('Выручка');
    expect(table.text()).toContain('iPhone 15 Pro');
    expect(table.text()).toContain('25');
  });

  it('отображает быстрые ссылки', async () => {
    const wrapper = mount(SupplierDashboard, { global: { plugins: [router] } });
    await flushPromises();

    const productsLink = wrapper.find('[data-testid="link-my-products"]');
    const ordersLink = wrapper.find('[data-testid="link-supplier-orders"]');

    expect(productsLink.exists()).toBe(true);
    expect(productsLink.text()).toContain('Мои товары');
    expect(ordersLink.exists()).toBe(true);
    expect(ordersLink.text()).toContain('Мои заказы');
  });

  it('показывает пустое состояние при отсутствии заказов', async () => {
    mockGet.mockImplementation((url) => {
      if (url === '/api/v1/analytics/supplier') {
        return Promise.resolve({
          data: {
            kpi: {
              total_orders: 0,
              pending_orders: 0,
              shipped_orders: 0,
              delivered_orders: 0,
              total_revenue: 0,
              total_products: 0,
            },
            orders_by_day: [],
            top_products: [],
          },
        });
      }
      return Promise.resolve({ data: {} });
    });

    const wrapper = mount(SupplierDashboard, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.find('[data-testid="orders-empty"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="products-empty"]').exists()).toBe(true);
    expect(wrapper.text()).toContain('Нет данных');
    expect(wrapper.findAll('[data-testid="top-product-item"]').length).toBe(0);
  });

  it('показывает ошибку загрузки через тост', async () => {
    mockGet.mockRejectedValue(new Error('Network error'));

    mount(SupplierDashboard, { global: { plugins: [router] } });
    await flushPromises();

    expect(toastFn).toHaveBeenCalledWith('Не удалось загрузить аналитику', 'error');
  });
});
