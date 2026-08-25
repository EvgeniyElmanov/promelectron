import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import { computed, ref } from 'vue';
import Cart from '../views/Cart.vue';
import { getSupplierCityCode } from '@/api/cdek';

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
const mockSyncCartCount = vi.hoisted(() => vi.fn());

vi.mock('@/api/cdek', () => ({
  getSupplierCityCode: vi.fn(() => Promise.resolve(44)),
}));

const mockRecipients = ref([]);
const mockRecipientsLoading = ref(false);
const mockLoadRecipients = vi.hoisted(() => vi.fn());

vi.mock('@/composables/useRecipients', () => ({
  useRecipients: () => ({
    recipients: mockRecipients,
    loading: mockRecipientsLoading,
    loadRecipients: mockLoadRecipients,
    defaultRecipient: computed(() => mockRecipients.value.find((r) => r.is_default) || null),
  }),
}));

vi.mock('@/composables/useCart', () => ({
  useCart: () => ({
    cartCount: computed(() => mockCartCount.value),
    addToCart: vi.fn(),
    removeFromCart: vi.fn(),
    updateQuantity: vi.fn(),
    getGuestCartItems: () => mockGuestItems.value,
    clearGuestCart: vi.fn(),
    mergeCartOnLogin: vi.fn(),
    syncCartCount: mockSyncCartCount,
  }),
}));

vi.mock('@/components/AddressForm.vue', () => ({
  default: {
    name: 'AddressForm',
    template: '<div data-testid="address-form">AddressForm</div>',
    props: ['modelValue', 'label', 'testidPrefix'],
  },
}));

vi.mock('@/components/CdekDeliveryWidget.vue', () => ({
  default: {
    name: 'CdekDeliveryWidget',
    template: '<div data-testid="cdek-delivery-widget"><span v-if="isFallback" data-testid="cdek-fallback-hint">fallback</span><button @click="select">Select delivery</button></div>',
    props: ['modelValue', 'items', 'isFallback'],
    methods: {
      select() {
        this.$emit('update:modelValue', { tariff_code: 136, price: 350, delivery_mode: 'PVZ' });
      },
    },
  },
}));

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: { template: '<div>Home</div>' } },
    { path: '/login', component: { template: '<div>Login</div>' } },
  ],
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
        supplier_id: 1,
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

const mockSavedRecipients = [
  {
    id: 1,
    first_name: 'Иван',
    last_name: 'Иванов',
    patronymic: 'Иванович',
    phone: '+79990001122',
    country_code: 'RU',
    is_default: true,
  },
  {
    id: 2,
    first_name: 'Пётр',
    last_name: 'Петров',
    patronymic: '',
    phone: '+79990003344',
    country_code: 'RU',
    is_default: false,
  },
];

describe('Cart.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsAuthenticated.value = true;
    mockGuestItems.value = [];
    mockCartCount.value = 0;
    mockRecipients.value = [];
    mockRecipientsLoading.value = false;
    getSupplierCityCode.mockResolvedValue(44);
    mockGet.mockImplementation((url) => {
      if (url === '/cart/') return Promise.resolve({ data: mockCartWithItems });
      if (url === '/auth/profile') return Promise.resolve({ data: {} });
      if (url === '/delivery-methods/') return Promise.resolve({ data: [] });
      if (url === '/me/recipients/') return Promise.resolve({ data: mockSavedRecipients });
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
      if (url === '/auth/profile') return Promise.resolve({ data: {} });
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

  it('показывает поля получателя для авторизованного пользователя', async () => {
    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.find('[data-testid="recipient-first-name"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="recipient-last-name"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="recipient-phone"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="recipient-country-code"]').exists()).toBe(true);
  });

  it('загружает и отображает сохранённых получателей', async () => {
    mockRecipients.value = mockSavedRecipients;
    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    const select = wrapper.find('[data-testid="recipient-select"]');
    expect(select.exists()).toBe(true);
    expect(select.html()).toContain('Иванов Иван Иванович');
    expect(select.html()).toContain('Петров Пётр');
    expect(select.html()).not.toContain('Новый получатель');
    expect(wrapper.find('[data-testid="recipient-new-button"]').exists()).toBe(true);
  });

  it('не показывает селект, если нет сохранённых получателей', async () => {
    mockRecipients.value = [];
    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.find('[data-testid="recipient-select"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="recipient-new-button"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="recipient-first-name"]').exists()).toBe(true);
  });

  it('подставляет данные выбранного получателя', async () => {
    mockRecipients.value = mockSavedRecipients;
    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    wrapper.vm.selectedRecipientId = 1;
    await flushPromises();

    expect(wrapper.find('[data-testid="recipient-first-name"]').element.value).toBe('Иван');
    expect(wrapper.find('[data-testid="recipient-last-name"]').element.value).toBe('Иванов');
    expect(wrapper.find('[data-testid="recipient-patronymic"]').element.value).toBe('Иванович');
    expect(wrapper.find('[data-testid="recipient-phone"]').element.value).toBe('+79990001122');
  });

  it('отправляет recipient_id при создании заказа с выбранным получателем', async () => {
    mockRecipients.value = mockSavedRecipients;
    mockPost.mockResolvedValue({ data: { id: 42 } });

    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    wrapper.vm.selectedDelivery = { tariff_code: 136, price: 350, delivery_mode: 'PVZ' };
    wrapper.vm.selectedRecipientId = 1;
    await flushPromises();

    const btn = wrapper.find('[data-testid="checkout-button"]');
    await btn.trigger('click');
    await flushPromises();

    expect(mockPost).toHaveBeenCalledWith('/orders/create/', expect.objectContaining({
      cdek_delivery: expect.objectContaining({ tariff_code: 136 }),
      recipient_id: 1,
    }));
  });

  it('отправляет inline-поля получателя при создании заказа', async () => {
    mockPost.mockResolvedValue({ data: { id: 42 } });

    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    wrapper.vm.selectedDelivery = { tariff_code: 136, price: 350, delivery_mode: 'PVZ' };
    wrapper.vm.recipientFirstName = 'Иван';
    wrapper.vm.recipientLastName = 'Иванов';
    wrapper.vm.recipientPatronymic = 'Иванович';
    wrapper.vm.recipientPhone = '+79990001122';
    await flushPromises();

    const btn = wrapper.find('[data-testid="checkout-button"]');
    await btn.trigger('click');
    await flushPromises();

    expect(mockPost).toHaveBeenCalledWith('/orders/create/', expect.objectContaining({
      cdek_delivery: expect.objectContaining({ tariff_code: 136 }),
      recipient_first_name: 'Иван',
      recipient_last_name: 'Иванов',
      recipient_patronymic: 'Иванович',
      recipient_phone: '+79990001122',
      recipient_country_code: 'RU',
    }));
  });

  it('вызывает syncCartCount после успешного создания заказа', async () => {
    mockPost.mockResolvedValue({ data: { id: 42 } });

    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    wrapper.vm.selectedDelivery = { tariff_code: 136, price: 350, delivery_mode: 'PVZ' };
    wrapper.vm.recipientFirstName = 'Иван';
    wrapper.vm.recipientLastName = 'Иванов';
    wrapper.vm.recipientPhone = '+79990001122';
    await flushPromises();

    const btn = wrapper.find('[data-testid="checkout-button"]');
    await btn.trigger('click');
    await flushPromises();

    expect(mockSyncCartCount).toHaveBeenCalled();
  });

  it('не создаёт заказ без телефона получателя', async () => {
    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    wrapper.vm.selectedDelivery = { tariff_code: 136, price: 350, delivery_mode: 'PVZ' };
    wrapper.vm.recipientFirstName = 'Иван';
    wrapper.vm.recipientLastName = 'Иванов';
    await flushPromises();

    const btn = wrapper.find('[data-testid="checkout-button"]');
    expect(btn.attributes('disabled')).toBeDefined();
  });

  it('передаёт isFallback=true, когда город поставщика не определён', async () => {
    getSupplierCityCode.mockResolvedValueOnce(null);
    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    const widget = wrapper.findComponent({ name: 'CdekDeliveryWidget' });
    expect(widget.exists()).toBe(true);
    expect(widget.props('isFallback')).toBe(true);
    expect(wrapper.find('[data-testid="cdek-fallback-hint"]').exists()).toBe(true);
  });

  it('показывает swipe-delete по свайпу влево', async () => {
    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    const item = wrapper.find('[data-testid="cart-item"]');
    await item.trigger('touchstart', { touches: [{ clientX: 200 }] });
    await item.trigger('touchmove', { touches: [{ clientX: 100 }] });

    expect(item.classes()).toContain('cart-item--swiped');
  });

  it('сбрасывает swipe-состояние по touchcancel', async () => {
    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    const item = wrapper.find('[data-testid="cart-item"]');
    await item.trigger('touchstart', { touches: [{ clientX: 200 }] });
    await item.trigger('touchcancel');
    await item.trigger('touchmove', { touches: [{ clientX: 0 }] });

    expect(item.classes()).not.toContain('cart-item--swiped');
  });

  it('помечает swipe-delete кнопку tabindex="-1" и aria-hidden', async () => {
    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    const deleteBg = wrapper.find('.cart-item__delete-bg');
    expect(deleteBg.exists()).toBe(true);
    expect(deleteBg.attributes('tabindex')).toBe('-1');
    expect(deleteBg.attributes('aria-hidden')).toBe('true');
  });
});

describe('Cart.vue — гостевая корзина', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsAuthenticated.value = false;
    mockRecipients.value = [];
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

  it('показывает кнопку "Оформить заказ" для гостя', async () => {
    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    const checkoutBtn = wrapper.find('[data-testid="checkout-button"]');
    expect(checkoutBtn.exists()).toBe(true);
    expect(checkoutBtn.text()).toContain('Оформить заказ');
  });

  it('редиректит гостя на /login?redirect=/cart при оформлении', async () => {
    const push = vi.spyOn(router, 'push');
    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    const checkoutBtn = wrapper.find('[data-testid="checkout-button"]');
    expect(checkoutBtn.attributes('disabled')).toBeUndefined();
    await checkoutBtn.trigger('click');
    await flushPromises();

    expect(push).toHaveBeenCalledWith('/login?redirect=/cart');
  });

  it('не показывает блоки доставки и адреса для гостя', async () => {
    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.text()).not.toContain('Способ доставки');
    expect(wrapper.find('[data-testid="address-form"]').exists()).toBe(false);
  });
});
