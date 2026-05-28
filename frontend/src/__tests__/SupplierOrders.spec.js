import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import SupplierOrders from '../views/SupplierOrders.vue';

const mockGet = vi.fn();
const mockPatch = vi.fn();

vi.mock('@/services/api', () => ({
  default: {
    get: (...args) => mockGet(...args),
    patch: (...args) => mockPatch(...args),
  },
}));

const toastFn = vi.fn();
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ add: toastFn }),
}));

const router = createRouter({
  history: createWebHistory(),
  routes: [{ path: '/', component: { template: '<div>Home</div>' } }],
});

const mockOrders = [
  {
    id: 123,
    buyer_name: 'Иван Иванов',
    buyer_email: 'ivan@example.com',
    total_amount: 15000,
    status: 'pending',
    created_at: '2026-05-27T10:00:00',
    items: [
      { product_name: 'iPhone 15', quantity: 2, price: 7500 },
    ],
  },
  {
    id: 124,
    buyer_name: 'Пётр Петров',
    buyer_email: 'petr@example.com',
    total_amount: 4990,
    status: 'shipped',
    created_at: '2026-05-26T14:30:00',
    items: [
      { product_name: 'Наушники', quantity: 1, price: 4990 },
    ],
  },
];

describe('SupplierOrders.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    toastFn.mockClear();
    mockGet.mockImplementation((url) => {
      if (url === '/orders/supplier/') return Promise.resolve({ data: mockOrders });
      return Promise.resolve({ data: {} });
    });
    mockPatch.mockResolvedValue({ data: {} });
  });

  it('отображает страницу заказов поставщика', async () => {
    const wrapper = mount(SupplierOrders, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.find('[data-testid="supplier-orders-page"]').exists()).toBe(true);
    expect(wrapper.text()).toContain('Мои заказы');
  });

  it('отображает список заказов с деталями', async () => {
    const wrapper = mount(SupplierOrders, { global: { plugins: [router] } });
    await flushPromises();

    const cards = wrapper.findAll('[data-testid="supplier-order-card"]');
    expect(cards.length).toBe(2);

    expect(wrapper.text()).toContain('Заказ №123');
    expect(wrapper.text()).toContain('Иван Иванов');
    expect(wrapper.text()).toContain('ivan@example.com');
    expect(wrapper.text()).toContain('15\u00A0000');

    expect(wrapper.text()).toContain('Заказ №124');
    expect(wrapper.text()).toContain('Пётр Петров');
  });

  it('показывает статусы заказов', async () => {
    const wrapper = mount(SupplierOrders, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.text()).toContain('Ожидает отправки');
    expect(wrapper.text()).toContain('Отправлен');
  });

  it('показывает кнопку отправки только для pending заказов', async () => {
    const wrapper = mount(SupplierOrders, { global: { plugins: [router] } });
    await flushPromises();

    const shipButtons = wrapper.findAll('[data-testid="ship-order-btn"]');
    expect(shipButtons.length).toBe(1);
    expect(shipButtons[0].text()).toContain('Отметить отправленным');
  });

  it('разворачивает и сворачивает список товаров по клику', async () => {
    const wrapper = mount(SupplierOrders, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.findAll('[data-testid="order-items"]').length).toBe(0);

    const toggleBtn = wrapper.find('.supplier-order-card__items-toggle');
    await toggleBtn.trigger('click');
    await flushPromises();

    expect(wrapper.findAll('[data-testid="order-items"]').length).toBe(1);
    expect(wrapper.text()).toContain('iPhone 15');
    expect(wrapper.text()).toContain('2 шт.');

    await toggleBtn.trigger('click');
    await flushPromises();

    expect(wrapper.findAll('[data-testid="order-items"]').length).toBe(0);
  });

  it('отправляет запрос на отметку заказа как отправленного', async () => {
    const wrapper = mount(SupplierOrders, { global: { plugins: [router] } });
    await flushPromises();

    const shipButton = wrapper.find('[data-testid="ship-order-btn"]');
    await shipButton.trigger('click');
    await flushPromises();

    expect(mockPatch).toHaveBeenCalledWith('/orders/supplier/123/ship');
    expect(toastFn).toHaveBeenCalledWith('Заказ отмечен как отправленный', 'success');
  });

  it('показывает пустое состояние', async () => {
    mockGet.mockImplementation((url) => {
      if (url === '/orders/supplier/') return Promise.resolve({ data: [] });
      return Promise.resolve({ data: {} });
    });

    const wrapper = mount(SupplierOrders, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.text()).toContain('У вас пока нет заказов.');
  });

  it('показывает ошибку загрузки', async () => {
    mockGet.mockRejectedValue({ response: { data: { detail: 'Ошибка сервера' } } });

    const wrapper = mount(SupplierOrders, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.text()).toContain('Ошибка загрузки');
    expect(wrapper.text()).toContain('Ошибка сервера');
  });

  it('повторяет загрузку по клику на кнопку повтора', async () => {
    mockGet.mockRejectedValueOnce({ response: { data: { detail: 'Ошибка сервера' } } });

    const wrapper = mount(SupplierOrders, { global: { plugins: [router] } });
    await flushPromises();

    mockGet.mockImplementation((url) => {
      if (url === '/orders/supplier/') return Promise.resolve({ data: mockOrders });
      return Promise.resolve({ data: {} });
    });

    await wrapper.find('.supplier-orders__retry').trigger('click');
    await flushPromises();

    expect(mockGet).toHaveBeenCalledTimes(2);
    expect(wrapper.findAll('[data-testid="supplier-order-card"]').length).toBe(2);
  });
});
