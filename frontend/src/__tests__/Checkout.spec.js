import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import Checkout from '../views/Checkout.vue';

const mockGet = vi.fn();
const mockPost = vi.fn();

vi.mock('@/services/api', () => ({
  default: {
    get: (...args) => mockGet(...args),
    post: (...args) => mockPost(...args),
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
    { path: '/orders/:id', component: { template: '<div>Order</div>' } },
    { path: '/checkout/:id', component: Checkout },
  ],
});

const mockOrder = {
  id: 42,
  user_id: 1,
  status: 'pending',
  total_price: 14990,
  shipping_address: 'Москва, ул. Ленина, д. 1',
  created_at: '2026-05-13T10:00:00Z',
  items: [
    { id: 1, product_id: 1, quantity: 1, price_at_time: 14990 },
  ],
};

describe('Checkout.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    toastFn.mockClear();
    mockGet.mockImplementation((url) => {
      if (url === '/orders/42') return Promise.resolve({ data: mockOrder });
      return Promise.resolve({ data: {} });
    });
    mockPost.mockImplementation((url) => {
      if (url === '/payments/42') return Promise.resolve({ data: { payment_id: 99, status: 'pending', confirmation_url: '/checkout/42/pay', amount: 14990 } });
      if (url === '/payments/99/confirm') return Promise.resolve({ data: { id: 99, status: 'paid' } });
      return Promise.resolve({ data: {} });
    });
  });

  const mountComponent = async () => {
    await router.push('/checkout/42');
    await router.isReady();
    const wrapper = mount(Checkout, { global: { plugins: [router] } });
    await flushPromises();
    return wrapper;
  };

  it('отображает страницу оплаты', async () => {
    const wrapper = await mountComponent();
    expect(wrapper.find('[data-testid="checkout-page"]').exists()).toBe(true);
    expect(wrapper.text()).toContain('Оплата заказа №42');
  });

  it('показывает сумму заказа', async () => {
    const wrapper = await mountComponent();
    expect(wrapper.text()).toContain('14\u00A0990');
    expect(wrapper.text()).toContain('1 товаров');
  });

  it('кнопка оплаты неактивна при пустой форме', async () => {
    const wrapper = await mountComponent();
    const btn = wrapper.find('[data-testid="pay-button"]');
    expect(btn.attributes('disabled')).toBeDefined();
  });

  it('кнопка оплаты активна при заполненной форме', async () => {
    const wrapper = await mountComponent();

    await wrapper.find('[data-testid="card-number"]').setValue('4242 4242 4242 4242');
    await wrapper.find('[data-testid="card-expiry"]').setValue('12/30');
    await wrapper.find('[data-testid="card-cvv"]').setValue('123');
    await wrapper.find('[data-testid="card-holder"]').setValue('IVAN IVANOV');
    await flushPromises();

    const btn = wrapper.find('[data-testid="pay-button"]');
    expect(btn.attributes('disabled')).toBeUndefined();
  });

  it('форматирует номер карты при вводе', async () => {
    const wrapper = await mountComponent();
    const input = wrapper.find('[data-testid="card-number"]');

    await input.setValue('4242424242424242');
    await input.trigger('input');
    await flushPromises();

    expect(input.element.value).toBe('4242 4242 4242 4242');
  });

  it('успешно обрабатывает оплату', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const wrapper = await mountComponent();

    await wrapper.find('[data-testid="card-number"]').setValue('4242 4242 4242 4242');
    await wrapper.find('[data-testid="card-expiry"]').setValue('12/30');
    await wrapper.find('[data-testid="card-cvv"]').setValue('123');
    await wrapper.find('[data-testid="card-holder"]').setValue('IVAN IVANOV');
    await flushPromises();

    await wrapper.find('[data-testid="pay-button"]').trigger('click');
    await flushPromises();

    // Advance past the simulated processing delays (1200ms + 600ms)
    await vi.advanceTimersByTimeAsync(2000);
    await flushPromises();

    expect(mockPost).toHaveBeenCalledWith('/payments/42');
    expect(mockPost).toHaveBeenCalledWith('/payments/99/confirm');
    expect(toastFn).toHaveBeenCalledWith('Оплата прошла успешно!', 'success');
    vi.useRealTimers();
  });

  it('редиректит если заказ уже оплачен', async () => {
    mockGet.mockImplementation((url) => {
      if (url === '/orders/42') return Promise.resolve({ data: { ...mockOrder, status: 'paid' } });
      return Promise.resolve({ data: {} });
    });

    await mountComponent();
    await flushPromises();

    expect(router.currentRoute.value.path).toBe('/orders/42');
  });
});
