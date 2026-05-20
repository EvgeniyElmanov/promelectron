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
});
