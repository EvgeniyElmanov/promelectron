import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import { computed, ref } from 'vue';
import PaymentFailed from '../views/PaymentFailed.vue';

const mockGet = vi.fn();

vi.mock('@/services/api', () => ({
  default: {
    get: (...args) => mockGet(...args),
    post: vi.fn(),
  },
}));

const mockIsAuthenticated = ref(true);

vi.mock('@/composables/useAuth', () => ({
  useAuth: () => ({
    isAuthenticated: computed(() => mockIsAuthenticated.value),
  }),
}));

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: { template: '<div>Home</div>' } },
    { path: '/orders', component: { template: '<div>Orders</div>' } },
    { path: '/checkout/:id', component: { template: '<div>Checkout</div>' } },
    { path: '/payment/failed', component: PaymentFailed },
  ],
});

const mockOrder = {
  id: 42,
  user_id: 1,
  status: 'awaiting_payment',
  total_price: 14990,
  items: [
    { id: 1, product_id: 1, quantity: 1 },
  ],
};

describe('PaymentFailed.vue — авторизованный пользователь', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsAuthenticated.value = true;
    mockGet.mockImplementation((url) => {
      if (url === '/orders/42/') return Promise.resolve({ data: mockOrder });
      return Promise.resolve({ data: {} });
    });
  });

  const mountComponent = async (query = { order_id: '42' }) => {
    const queryString = new URLSearchParams(query).toString();
    await router.push(`/payment/failed?${queryString}`);
    await router.isReady();
    const wrapper = mount(PaymentFailed, { global: { plugins: [router] } });
    await flushPromises();
    return wrapper;
  };

  it('загружает заказ по order_id', async () => {
    await mountComponent();

    expect(mockGet).toHaveBeenCalledWith('/orders/42/');
  });

  it('показывает кнопку "Мои заказы" для авторизованного пользователя', async () => {
    const wrapper = await mountComponent();

    expect(wrapper.text()).toContain('Мои заказы');
  });

  it('отображает понятную причину отмены платежа', async () => {
    mockGet.mockImplementation((url) => {
      if (url === '/orders/42/') {
        return Promise.resolve({
          data: { ...mockOrder, status: 'cancelled', cancellation_reason: 'insufficient_funds' },
        });
      }
      return Promise.resolve({ data: {} });
    });
    const wrapper = await mountComponent();

    const reason = wrapper.find('[data-testid="cancellation-reason"]');
    expect(reason.exists()).toBe(true);
    expect(reason.text()).toContain('Недостаточно средств на карте');
  });

  it('отображает техническую причину, если маппинг неизвестен', async () => {
    mockGet.mockImplementation((url) => {
      if (url === '/orders/42/') {
        return Promise.resolve({
          data: { ...mockOrder, status: 'cancelled', cancellation_reason: 'unknown_reason' },
        });
      }
      return Promise.resolve({ data: {} });
    });
    const wrapper = await mountComponent();

    const reason = wrapper.find('[data-testid="cancellation-reason"]');
    expect(reason.exists()).toBe(true);
    expect(reason.text()).toContain('unknown_reason');
  });

  it('редиректит на checkout для авторизованного пользователя', async () => {
    const wrapper = await mountComponent();

    const retryButton = wrapper.findAll('button').find((b) => b.text().includes('Попробовать'));
    expect(retryButton).toBeDefined();
    await retryButton.trigger('click');
    await flushPromises();

    expect(router.currentRoute.value.path).toBe('/checkout/42');
    expect(router.currentRoute.value.query).toEqual({});
  });
});

describe('PaymentFailed.vue — гостевой режим', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsAuthenticated.value = false;
    mockGet.mockImplementation((url) => {
      if (url === '/orders/guest/42/?guest_email=guest%40example.com') {
        return Promise.resolve({ data: { ...mockOrder, user_id: null, guest_email: 'guest@example.com' } });
      }
      return Promise.resolve({ data: {} });
    });
    vi.stubGlobal('sessionStorage', {
      getItem: () => 'guest@example.com',
      setItem: vi.fn(),
      removeItem: vi.fn(),
    });
  });

  const mountGuestComponent = async (query = { order_id: '42', guest_email: 'guest@example.com' }) => {
    const queryString = new URLSearchParams(query).toString();
    await router.push(`/payment/failed?${queryString}`);
    await router.isReady();
    const wrapper = mount(PaymentFailed, { global: { plugins: [router] } });
    await flushPromises();
    return wrapper;
  };

  it('загружает гостевой заказ по email', async () => {
    await mountGuestComponent();

    expect(mockGet).toHaveBeenCalledWith('/orders/guest/42/?guest_email=guest%40example.com');
  });

  it('не показывает кнопку "Мои заказы" для гостя', async () => {
    const wrapper = await mountGuestComponent();

    expect(wrapper.text()).not.toContain('Мои заказы');
    expect(wrapper.text()).toContain('В каталог');
  });

  it('редиректит на checkout без guest_email для гостя', async () => {
    const wrapper = await mountGuestComponent();

    const retryButton = wrapper.findAll('button').find((b) => b.text().includes('Попробовать'));
    expect(retryButton).toBeDefined();
    await retryButton.trigger('click');
    await flushPromises();

    expect(router.currentRoute.value.path).toBe('/checkout/42');
    expect(router.currentRoute.value.query).toEqual({});
  });
});
