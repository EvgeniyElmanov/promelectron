import { describe, it, expect, vi } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import OrderDetail from '../views/OrderDetail.vue';

const mockGet = vi.fn();

vi.mock('@/services/api', () => ({
  default: {
    get: (...args) => mockGet(...args),
  },
}));

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ add: vi.fn() }),
}));

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/orders/:id', component: OrderDetail },
    { path: '/', component: { template: '<div>Home</div>' } },
  ],
});

const mockOrder = {
  id: 42,
  user_id: 1,
  status: 'shipped',
  total_price: 64970,
  shipping_address: 'Москва, ул. Тестовая, д. 1',
  created_at: '2026-05-18T10:00:00Z',
  items: [
    { id: 1, product_id: 1, quantity: 2, price_at_time: 29990, product: { name: 'Смартфон Pro' } },
    { id: 2, product_id: 2, quantity: 1, price_at_time: 4990, product: { name: 'Наушники' } },
  ],
};

const mockOrderWithCdek = {
  ...mockOrder,
  cdek_order: {
    id: 1,
    cdek_uuid: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
    cdek_number: 'CDEK123456',
    tracking_number: 'TRK987654321',
    cdek_status: 'DELIVERED',
    cdek_status_name: 'Доставлено',
    status_date_time: '2026-05-20T14:30:00Z',
    status_city: 'Москва',
    tracking_url: 'https://cdek.ru/track?number=TRK987654321',
    status_history: [
      { id: 1, cdek_status: 'CREATED', cdek_status_name: 'Создан', status_date_time: '2026-05-18T12:00:00Z', city: null },
      { id: 2, cdek_status: 'ACCEPTED', cdek_status_name: 'Принят', status_date_time: '2026-05-19T10:00:00Z', city: 'Москва' },
      { id: 3, cdek_status: 'DELIVERED', cdek_status_name: 'Доставлено', status_date_time: '2026-05-20T14:30:00Z', city: 'Москва' },
    ],
  },
};

describe('OrderDetail.vue', () => {
  it('отображает детали заказа с таймлайном', async () => {
    mockGet.mockResolvedValue({ data: mockOrder });

    await router.push('/orders/42');
    await router.isReady();

    const wrapper = mount(OrderDetail, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.text()).toContain('Заказ №42');
    expect(wrapper.text()).toContain('Отправлен');
    expect(wrapper.text()).toContain('64\u00A0970');
    expect(wrapper.text()).toContain('Смартфон Pro');
    expect(wrapper.text()).toContain('Наушники');
    expect(wrapper.text()).toContain('Москва, ул. Тестовая, д. 1');
  });

  it('отмечает текущий статус в таймлайне', async () => {
    mockGet.mockResolvedValue({ data: mockOrder });

    await router.push('/orders/42');
    await router.isReady();

    const wrapper = mount(OrderDetail, { global: { plugins: [router] } });
    await flushPromises();

    const currentSteps = wrapper.findAll('.timeline__step--current');
    expect(currentSteps.length).toBe(1);
    expect(currentSteps[0].text()).toContain('Отправлен');
  });

  it('отображает ошибку при неудаче загрузки', async () => {
    mockGet.mockRejectedValue({ response: { data: { detail: 'Заказ не найден' } } });

    await router.push('/orders/999');
    await router.isReady();

    const wrapper = mount(OrderDetail, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.text()).toContain('Заказ не найден');
  });

  it('отображает блок CDEK со статусом, ссылкой и историей', async () => {
    mockGet.mockResolvedValue({ data: mockOrderWithCdek });

    await router.push('/orders/42');
    await router.isReady();

    const wrapper = mount(OrderDetail, { global: { plugins: [router] } });
    await flushPromises();

    const cdekCard = wrapper.find('[data-testid="cdek-order-card"]');
    expect(cdekCard.exists()).toBe(true);
    expect(cdekCard.text()).toContain('Доставка CDEK');
    expect(cdekCard.text()).toContain('Доставлено');
    expect(cdekCard.text()).toContain('TRK987654321');

    const trackingLink = wrapper.find('[data-testid="cdek-tracking-link"]');
    expect(trackingLink.exists()).toBe(true);
    expect(trackingLink.attributes('href')).toBe(mockOrderWithCdek.cdek_order.tracking_url);

    const history = wrapper.find('[data-testid="cdek-status-history"]');
    expect(history.exists()).toBe(true);
    expect(history.text()).toContain('Доставлено');
    expect(history.text()).toContain('Принят');
    expect(history.text()).toContain('Создан');
  });
});
