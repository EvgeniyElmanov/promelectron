import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import { computed, ref } from 'vue';
import Checkout from '../views/Checkout.vue';

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
    { path: '/payment/success', component: { template: '<div>Success</div>' } },
    { path: '/payment/failed', component: { template: '<div>Failed</div>' } },
  ],
});

const mockOrder = {
  id: 42,
  user_id: 1,
  status: 'pending',
  total_price: 14990,
  shipping_address: 'Москва, ул. Ленина, д. 1',
  recipient_first_name: 'Иван',
  recipient_last_name: 'Иванов',
  created_at: '2026-05-13T10:00:00Z',
  items: [
    { id: 1, product_id: 1, quantity: 1, price_at_time: 14990 },
  ],
};

const mockOrderWithRecipient = {
  ...mockOrder,
  recipient: {
    id: 1,
    first_name: 'Иван',
    last_name: 'Иванов',
    patronymic: 'Иванович',
    phone: '+79990001122',
    country_code: 'RU',
  },
};

describe('Checkout.vue — авторизованный пользователь', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    toastFn.mockClear();
    mockIsAuthenticated.value = true;
    mockGet.mockImplementation((url) => {
      if (url === '/orders/42/') return Promise.resolve({ data: mockOrderWithRecipient });
      return Promise.resolve({ data: {} });
    });
    mockPost.mockImplementation((url) => {
      if (url === '/payments/42/') return Promise.resolve({ data: { payment_id: 99, status: 'pending', confirmation_url: 'https://yoomoney.ru/checkout/42/pay', amount: 14990 } });
      return Promise.resolve({ data: {} });
    });
    delete window.location;
    window.location = { href: '' };
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

  it('показывает имя получателя из nested recipient', async () => {
    const wrapper = await mountComponent();
    const recipient = wrapper.find('[data-testid="checkout-recipient"]');
    expect(recipient.exists()).toBe(true);
    expect(recipient.text()).toContain('Иванов');
    expect(recipient.text()).toContain('Иван');
    expect(recipient.text()).toContain('Иванович');
  });

  it('показывает телефон получателя из nested recipient', async () => {
    const wrapper = await mountComponent();
    const phone = wrapper.find('[data-testid="checkout-recipient-phone"]');
    expect(phone.exists()).toBe(true);
    expect(phone.text()).toBe('+79990001122');
  });

  it('кнопка оплаты активна', async () => {
    const wrapper = await mountComponent();
    const btn = wrapper.find('[data-testid="pay-button"]');
    expect(btn.attributes('disabled')).toBeUndefined();
  });

  it('успешно инициирует оплату', async () => {
    const wrapper = await mountComponent();

    await wrapper.find('[data-testid="pay-button"]').trigger('click');
    await flushPromises();

    expect(mockPost).toHaveBeenCalledWith('/payments/42/');
    expect(window.location.href).toBe('https://yoomoney.ru/checkout/42/pay');
  });

  it('редиректит если заказ уже оплачен', async () => {
    mockGet.mockImplementation((url) => {
      if (url === '/orders/42/') return Promise.resolve({ data: { ...mockOrderWithRecipient, status: 'paid' } });
      return Promise.resolve({ data: {} });
    });

    await mountComponent();
    await flushPromises();

    expect(router.currentRoute.value.path).toBe('/orders/42');
  });
});

describe('Checkout.vue — гостевой режим', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    toastFn.mockClear();
    mockIsAuthenticated.value = false;
    mockGet.mockImplementation((url) => {
      if (url === '/orders/guest/42/?guest_email=guest%40example.com') {
        return Promise.resolve({ data: { ...mockOrder, user_id: null, guest_email: 'guest@example.com' } });
      }
      return Promise.resolve({ data: {} });
    });
    mockPost.mockImplementation((url) => {
      if (url === '/payments/guest/42/') {
        return Promise.resolve({ data: { payment_id: 99, status: 'pending', confirmation_url: 'https://yoomoney.ru/checkout/guest/42/pay', amount: 14990 } });
      }
      return Promise.resolve({ data: {} });
    });
    vi.stubGlobal('sessionStorage', {
      getItem: () => 'guest@example.com',
      setItem: vi.fn(),
      removeItem: vi.fn(),
    });
    delete window.location;
    window.location = { href: '' };
  });

  const mountGuestComponent = async () => {
    await router.push('/checkout/42?guest_email=guest@example.com');
    await router.isReady();
    const wrapper = mount(Checkout, { global: { plugins: [router] } });
    await flushPromises();
    return wrapper;
  };

  it('загружает гостевой заказ по email', async () => {
    await mountGuestComponent();

    expect(mockGet).toHaveBeenCalledWith('/orders/guest/42/?guest_email=guest%40example.com');
  });

  it('инициирует гостевой платёж', async () => {
    const wrapper = await mountGuestComponent();

    await wrapper.find('[data-testid="pay-button"]').trigger('click');
    await flushPromises();

    expect(mockPost).toHaveBeenCalledWith('/payments/guest/42/', { guest_email: 'guest@example.com' });
    expect(window.location.href).toBe('https://yoomoney.ru/checkout/guest/42/pay');
  });

  it('редиректит на success если гостевой заказ уже оплачен', async () => {
    mockGet.mockImplementation((url) => {
      if (url === '/orders/guest/42/?guest_email=guest%40example.com') {
        return Promise.resolve({ data: { ...mockOrder, user_id: null, guest_email: 'guest@example.com', status: 'paid' } });
      }
      return Promise.resolve({ data: {} });
    });

    await mountGuestComponent();
    await flushPromises();

    expect(router.currentRoute.value.path).toBe('/payment/success');
    expect(router.currentRoute.value.query.order_id).toBe('42');
    expect(router.currentRoute.value.query.guest_email).toBe('guest@example.com');
  });
});
