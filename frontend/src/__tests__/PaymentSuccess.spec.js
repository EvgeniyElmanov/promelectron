import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import { computed, ref } from 'vue';
import PaymentSuccess from '../views/PaymentSuccess.vue';

const mockGet = vi.fn();
const mockPost = vi.fn();

vi.mock('@/services/api', () => ({
  default: {
    get: (...args) => mockGet(...args),
    post: (...args) => mockPost(...args),
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
    { path: '/payment/success', component: PaymentSuccess },
    { path: '/payment/failed', component: { template: '<div>Failed</div>' } },
  ],
});

const mockOrder = {
  id: 42,
  user_id: 1,
  status: 'paid',
  total_price: 14990,
  items: [
    { id: 1, product_id: 1, quantity: 1, price_at_time: 14990 },
  ],
};

describe('PaymentSuccess.vue — авторизованный пользователь', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsAuthenticated.value = true;
    mockGet.mockImplementation((url) => {
      if (url === '/orders/42/') return Promise.resolve({ data: mockOrder });
      return Promise.resolve({ data: {} });
    });
    mockPost.mockResolvedValue({ data: {} });
  });

  const mountComponent = async (query = { order_id: '42' }) => {
    const queryString = new URLSearchParams(query).toString();
    await router.push(`/payment/success?${queryString}`);
    await router.isReady();
    const wrapper = mount(PaymentSuccess, { global: { plugins: [router] } });
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
});

describe('PaymentSuccess.vue — гостевой режим', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsAuthenticated.value = false;
    mockGet.mockImplementation((url) => {
      if (url === '/orders/guest/42/?guest_email=guest%40example.com') {
        return Promise.resolve({ data: { ...mockOrder, user_id: null, guest_email: 'guest@example.com' } });
      }
      return Promise.resolve({ data: {} });
    });
    mockPost.mockResolvedValue({ data: {} });
    vi.stubGlobal('localStorage', {
      getItem: () => 'guest@example.com',
      setItem: vi.fn(),
      removeItem: vi.fn(),
    });
  });

  const mountGuestComponent = async (query = { order_id: '42', guest_email: 'guest@example.com' }) => {
    const queryString = new URLSearchParams(query).toString();
    await router.push(`/payment/success?${queryString}`);
    await router.isReady();
    const wrapper = mount(PaymentSuccess, { global: { plugins: [router] } });
    await flushPromises();
    return wrapper;
  };

  it('загружает гостевой заказ по email', async () => {
    await mountGuestComponent();

    expect(mockGet).toHaveBeenCalledWith('/orders/guest/42/?guest_email=guest%40example.com');
  });

  it('не вызывает sync-by-order для гостя', async () => {
    await mountGuestComponent();
    await flushPromises();

    expect(mockPost).not.toHaveBeenCalledWith('/payments/sync-by-order/42');
  });

  it('не показывает кнопку "Мои заказы" для гостя', async () => {
    const wrapper = await mountGuestComponent();

    expect(wrapper.text()).not.toContain('Мои заказы');
    expect(wrapper.text()).toContain('В каталог');
  });

  it('вызывает guest mock-confirm при mock=1', async () => {
    await mountGuestComponent({ order_id: '42', guest_email: 'guest@example.com', mock: '1' });
    await flushPromises();

    expect(mockPost).toHaveBeenCalledWith('/payments/guest/42/mock-confirm/', { guest_email: 'guest@example.com' });
  });
});
