import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import { computed, ref } from 'vue';
import Cart from '../views/Cart.vue';

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPut = vi.fn();
const mockDelete = vi.fn();

vi.mock('@/services/api', () => ({
  default: {
    get: (...args) => mockGet(...args),
    post: (...args) => mockPost(...args),
    put: (...args) => mockPut(...args),
    delete: (...args) => mockDelete(...args),
  },
}));

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ add: vi.fn() }),
}));

const mockIsAuthenticated = ref(true);

vi.mock('@/composables/useAuth', () => ({
  useAuth: () => ({
    isAuthenticated: computed(() => mockIsAuthenticated.value),
  }),
}));

const mockGuestItems = ref([]);
const mockCartCount = ref(0);

vi.mock('@/composables/useCart', () => ({
  useCart: () => ({
    cartCount: computed(() => mockCartCount.value),
    addToCart: vi.fn(),
    removeFromCart: vi.fn(),
    updateQuantity: vi.fn(),
    getGuestCartItems: () => mockGuestItems.value,
    clearGuestCart: vi.fn(),
    mergeCartOnLogin: vi.fn(),
    syncCartCount: vi.fn(),
  }),
}));

vi.mock('@/components/AddressForm.vue', () => ({
  default: {
    name: 'AddressForm',
    template: '<div data-testid="address-form">AddressForm</div>',
    props: ['modelValue', 'label', 'testidPrefix'],
  },
}));

const router = createRouter({
  history: createWebHistory(),
  routes: [{ path: '/', component: { template: '<div>Home</div>' } }],
});

const mockCartWithItems = {
  id: 1,
  user_id: 1,
  items: [
    {
      id: 101,
      product_id: 1,
      quantity: 2,
      product: {
        id: 1,
        name: 'Смартфон Pro',
        price: 29990,
        stock: 5,
        images: [],
      },
    },
    {
      id: 102,
      product_id: 2,
      quantity: 1,
      product: {
        id: 2,
        name: 'Наушники Wireless',
        price: 4990,
        stock: 10,
        images: ['http://example.com/img.jpg'],
      },
    },
  ],
};

const mockProfile = {
  email: 'test@example.com',
  shipping_address: null,
};

describe('Cart.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsAuthenticated.value = true;
    mockGuestItems.value = [];
    mockCartCount.value = 0;
    mockGet.mockImplementation((url) => {
      if (url === '/cart/') return Promise.resolve({ data: mockCartWithItems });
      if (url === '/auth/profile') return Promise.resolve({ data: mockProfile });
      if (url === '/delivery-methods/') return Promise.resolve({ data: [] });
      return Promise.resolve({ data: {} });
    });
  });

  it('отображает список товаров с ценами', async () => {
    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    const items = wrapper.findAll('[data-testid="cart-item"]');
    expect(items.length).toBe(2);

    expect(wrapper.text()).toContain('Смартфон Pro');
    expect(wrapper.text()).toContain('Наушники Wireless');
    expect(wrapper.text()).toContain('29\u00A0990');
    expect(wrapper.text()).toContain('4\u00A0990');
  });

  it('отображает общую сумму', async () => {
    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    // 29990 * 2 + 4990 = 64970
    expect(wrapper.text()).toContain('64\u00A0970');
  });

  it('отображает пустое состояние', async () => {
    mockGet.mockImplementation((url) => {
      if (url === '/cart/') return Promise.resolve({ data: { id: 1, user_id: 1, items: [] } });
      if (url === '/auth/profile') return Promise.resolve({ data: mockProfile });
      if (url === '/delivery-methods/') return Promise.resolve({ data: [] });
      return Promise.resolve({ data: {} });
    });

    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.text()).toContain('Ваша корзина пуста');
  });

  it('увеличивает количество по клику на +', async () => {
    mockPut.mockResolvedValue({ data: {} });

    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    const plusButtons = wrapper.findAll('.cart-item__qty-btn');
    // + buttons are at index 1 and 3 (for 2 items: - + - +)
    await plusButtons[1].trigger('click');
    await flushPromises();

    expect(mockPut).toHaveBeenCalledWith('/cart/update/101', { quantity: 3 });
  });

  it('удаляет товар по клику на кнопку удаления (desktop)', async () => {
    mockDelete.mockResolvedValue({ data: {} });

    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    const removeButtons = wrapper.findAll('.cart-item__remove-desktop');
    expect(removeButtons.length).toBe(2);

    await removeButtons[0].trigger('click');
    await flushPromises();

    expect(mockDelete).toHaveBeenCalledWith('/cart/remove/101');
  });
});

describe('Cart.vue — гостевая корзина', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsAuthenticated.value = false;
    mockGuestItems.value = [
      {
        product_id: 10,
        quantity: 3,
        name: 'Гостевой товар',
        price: 1500,
        stock: 8,
        images: [],
      },
    ];
    mockCartCount.value = 3;
    mockGet.mockImplementation((url) => {
      if (url === '/delivery-methods/') return Promise.resolve({ data: [] });
      return Promise.resolve({ data: {} });
    });
  });

  it('отображает товары из localStorage для гостя', async () => {
    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.text()).toContain('Гостевой товар');
    expect(wrapper.text()).toContain('4\u00A0500');
  });

  it('показывает кнопку "Войти, чтобы оформить" для гостя', async () => {
    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    const checkoutBtn = wrapper.find('[data-testid="checkout-button"]');
    expect(checkoutBtn.exists()).toBe(true);
    expect(checkoutBtn.text()).toContain('Войти');
  });

  it('не показывает блоки доставки и адреса для гостя', async () => {
    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.text()).not.toContain('Способ доставки');
    expect(wrapper.find('[data-testid="address-form"]').exists()).toBe(false);
  });
});
