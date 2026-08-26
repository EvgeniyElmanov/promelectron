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
const mockSelectItem = vi.hoisted(() => vi.fn(() => Promise.resolve()));
const mockSelectAll = vi.hoisted(() => vi.fn(() => Promise.resolve()));
const mockDeselectAll = vi.hoisted(() => vi.fn(() => Promise.resolve()));
const mockApiSelectCartItem = vi.hoisted(() => vi.fn(() => Promise.resolve({ data: {} })));
const mockApiSelectAll = vi.hoisted(() => vi.fn(() => Promise.resolve({ data: {} })));
const mockApiDeselectAll = vi.hoisted(() => vi.fn(() => Promise.resolve({ data: {} })));

vi.mock('@/api/cart', () => ({
  selectCartItem: mockApiSelectCartItem,
  selectAllCartItems: mockApiSelectAll,
  deselectAllCartItems: mockApiDeselectAll,
}));

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
    selectItem: mockSelectItem,
    selectAll: mockSelectAll,
    deselectAll: mockDeselectAll,
    getGuestCartItems: () => mockGuestItems.value,
    getSelectedGuestCartItems: () => mockGuestItems.value.filter((i) => i.selected !== false),
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
      selected: true,
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
      selected: true,
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
      if (url === '/cart/') return Promise.resolve({ data: structuredClone(mockCartWithItems) });
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

  it('отображает чекбокс выбора для каждого товара', async () => {
    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    const checkboxes = wrapper.findAll('[data-testid="cart-item-select"] input');
    expect(checkboxes.length).toBe(2);
    expect(checkboxes[0].element.checked).toBe(true);
    expect(checkboxes[1].element.checked).toBe(true);
  });

  it('отображает чекбокс "Выбрать все"', async () => {
    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    const selectAll = wrapper.find('[data-testid="cart-select-all"]');
    expect(selectAll.exists()).toBe(true);
    expect(selectAll.find('input').element.checked).toBe(true);
    expect(selectAll.find('input').element.indeterminate).toBe(false);
  });

  it('помечает "Выбрать все" indeterminate при частичном выборе', async () => {
    const mixedCart = {
      ...mockCartWithItems,
      items: [
        { ...mockCartWithItems.items[0], selected: true },
        { ...mockCartWithItems.items[1], selected: false },
      ],
    };
    mockGet.mockImplementation((url) => {
      if (url === '/cart/') return Promise.resolve({ data: mixedCart });
      if (url === '/auth/profile') return Promise.resolve({ data: {} });
      if (url === '/delivery-methods/') return Promise.resolve({ data: [] });
      if (url === '/me/recipients/') return Promise.resolve({ data: mockSavedRecipients });
      return Promise.resolve({ data: {} });
    });

    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    const input = wrapper.find('[data-testid="cart-select-all"] input');
    expect(input.element.checked).toBe(false);
    expect(input.element.indeterminate).toBe(true);
  });

  it('считает итоги только по выбранным товарам', async () => {
    const unselectedCart = {
      ...mockCartWithItems,
      items: mockCartWithItems.items.map((item, index) => ({
        ...item,
        selected: index === 0,
      })),
    };
    mockGet.mockImplementation((url) => {
      if (url === '/cart/') return Promise.resolve({ data: unselectedCart });
      if (url === '/auth/profile') return Promise.resolve({ data: {} });
      if (url === '/delivery-methods/') return Promise.resolve({ data: [] });
      if (url === '/me/recipients/') return Promise.resolve({ data: mockSavedRecipients });
      return Promise.resolve({ data: {} });
    });

    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    // Выбран только первый товар: 29990 * 2 = 59980; полный итог 64970 не показывается
    expect(wrapper.text()).toContain('59\u00A0980');
    expect(wrapper.text()).not.toContain('64\u00A0970');
  });

  it('блокирует кнопку оформления, когда нет выбранных товаров', async () => {
    const emptySelectionCart = {
      ...mockCartWithItems,
      items: mockCartWithItems.items.map((item) => ({ ...item, selected: false })),
    };
    mockGet.mockImplementation((url) => {
      if (url === '/cart/') return Promise.resolve({ data: emptySelectionCart });
      if (url === '/auth/profile') return Promise.resolve({ data: {} });
      if (url === '/delivery-methods/') return Promise.resolve({ data: [] });
      if (url === '/me/recipients/') return Promise.resolve({ data: mockSavedRecipients });
      return Promise.resolve({ data: {} });
    });

    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    const btn = wrapper.find('[data-testid="checkout-button"]');
    expect(btn.attributes('disabled')).toBeDefined();
  });

  it('передаёт в CDEK-виджет только выбранные товары', async () => {
    const unselectedCart = {
      ...mockCartWithItems,
      items: [
        { ...mockCartWithItems.items[0], selected: true },
        { ...mockCartWithItems.items[1], selected: false },
      ],
    };
    mockGet.mockImplementation((url) => {
      if (url === '/cart/') return Promise.resolve({ data: unselectedCart });
      if (url === '/auth/profile') return Promise.resolve({ data: {} });
      if (url === '/delivery-methods/') return Promise.resolve({ data: [] });
      if (url === '/me/recipients/') return Promise.resolve({ data: mockSavedRecipients });
      return Promise.resolve({ data: {} });
    });

    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    const widget = wrapper.findComponent({ name: 'CdekDeliveryWidget' });
    expect(widget.props('items').length).toBe(1);
    expect(widget.props('items')[0].product.name).toBe('Смартфон Pro');
  });

  it('переключает выбор товара через API (auth)', async () => {
    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    const checkboxes = wrapper.findAll('[data-testid="cart-item-select"] input');
    await checkboxes[0].setValue(false);
    await flushPromises();

    expect(mockApiSelectCartItem).toHaveBeenCalledWith(101, false);
    // Оптимистичное обновление: чекбокс снят без перезагрузки корзины
    expect(checkboxes[0].element.checked).toBe(false);
  });

  it('откатывает выбор через fetchCart при ошибке API', async () => {
    mockApiSelectCartItem.mockRejectedValueOnce(new Error('Network error'));

    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    const initialCalls = mockGet.mock.calls.length;
    const checkboxes = wrapper.findAll('[data-testid="cart-item-select"] input');
    await checkboxes[0].setValue(false);
    await flushPromises();

    expect(mockApiSelectCartItem).toHaveBeenCalledWith(101, false);
    expect(mockGet.mock.calls.length).toBeGreaterThan(initialCalls);
    // После отката мок возвращает selected: true
    expect(wrapper.findAll('[data-testid="cart-item-select"] input')[0].element.checked).toBe(true);
  });

  it('снимает выбор со всех товаров через API при клике на "Выбрать все"', async () => {
    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    const selectAll = wrapper.find('[data-testid="cart-select-all"] input');
    await selectAll.setValue(false);
    await flushPromises();

    expect(mockApiDeselectAll).toHaveBeenCalled();
    const checkboxes = wrapper.findAll('[data-testid="cart-item-select"] input');
    expect(checkboxes[0].element.checked).toBe(false);
    expect(checkboxes[1].element.checked).toBe(false);
  });

  it('выбирает все товары через API при частичном выборе', async () => {
    const mixedCart = {
      ...mockCartWithItems,
      items: [
        { ...mockCartWithItems.items[0], selected: true },
        { ...mockCartWithItems.items[1], selected: false },
      ],
    };
    mockGet.mockImplementation((url) => {
      if (url === '/cart/') return Promise.resolve({ data: mixedCart });
      if (url === '/auth/profile') return Promise.resolve({ data: {} });
      if (url === '/delivery-methods/') return Promise.resolve({ data: [] });
      if (url === '/me/recipients/') return Promise.resolve({ data: mockSavedRecipients });
      return Promise.resolve({ data: {} });
    });

    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    const selectAll = wrapper.find('[data-testid="cart-select-all"] input');
    await selectAll.setValue(true);
    await flushPromises();

    expect(mockApiSelectAll).toHaveBeenCalled();
  });

  it('сбрасывает выбранную доставку при снятии чекбокса с товара', async () => {
    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    wrapper.vm.selectedDelivery = { tariff_code: 136, price: 350, delivery_mode: 'PVZ' };
    await flushPromises();

    const checkboxes = wrapper.findAll('[data-testid="cart-item-select"] input');
    await checkboxes[0].setValue(false);
    await flushPromises();

    expect(mockApiSelectCartItem).toHaveBeenCalledWith(101, false);
    expect(wrapper.vm.selectedDelivery).toBeNull();
  });

  it('не сбрасывает выбранную доставку при повторной загрузке корзины с тем же составом', async () => {
    mockPut.mockResolvedValue({ data: {} });

    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    wrapper.vm.selectedDelivery = { tariff_code: 136, price: 350, delivery_mode: 'PVZ' };
    await flushPromises();

    // updateQuantity → fetchCart, но мок возвращает тот же состав (сигнатура не меняется)
    const plusButtons = wrapper.findAll('.cart-item__qty-btn');
    await plusButtons[1].trigger('click');
    await flushPromises();

    expect(mockPut).toHaveBeenCalledWith('/cart/update/101', { quantity: 3 });
    expect(wrapper.vm.selectedDelivery).not.toBeNull();
  });

  it('сбрасывает выбранную доставку при изменении количества товара', async () => {
    mockPut.mockResolvedValue({ data: {} });

    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    wrapper.vm.selectedDelivery = { tariff_code: 136, price: 350, delivery_mode: 'PVZ' };
    await flushPromises();

    // После обновления количества мок отдаёт корзину с quantity=3 у первого товара
    const updatedCart = structuredClone(mockCartWithItems);
    updatedCart.items[0].quantity = 3;
    mockGet.mockImplementation((url) => {
      if (url === '/cart/') return Promise.resolve({ data: structuredClone(updatedCart) });
      if (url === '/auth/profile') return Promise.resolve({ data: {} });
      if (url === '/delivery-methods/') return Promise.resolve({ data: [] });
      if (url === '/me/recipients/') return Promise.resolve({ data: mockSavedRecipients });
      return Promise.resolve({ data: {} });
    });

    const plusButtons = wrapper.findAll('.cart-item__qty-btn');
    await plusButtons[1].trigger('click');
    await flushPromises();

    expect(wrapper.vm.selectedDelivery).toBeNull();
  });

  it('показывает swipe-delete по свайпу влево', async () => {
    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    const item = wrapper.find('[data-testid="cart-item"]');
    await item.trigger('touchstart', { touches: [{ clientX: 200, clientY: 100 }] });
    await item.trigger('touchmove', { touches: [{ clientX: 100, clientY: 100 }] });

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

  it('помечает swipe-delete кнопку tabindex="-1" и aria-hidden до свайпа', async () => {
    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    const deleteBg = wrapper.find('.cart-item__delete-bg');
    expect(deleteBg.exists()).toBe(true);
    expect(deleteBg.attributes('tabindex')).toBe('-1');
    expect(deleteBg.attributes('aria-hidden')).toBe('true');
  });

  it('делает swipe-delete кнопку доступной после свайпа', async () => {
    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    const item = wrapper.find('[data-testid="cart-item"]');
    await item.trigger('touchstart', { touches: [{ clientX: 200, clientY: 100 }] });
    await item.trigger('touchmove', { touches: [{ clientX: 100, clientY: 100 }] });
    expect(item.classes()).toContain('cart-item--swiped');

    const deleteBg = wrapper.find('.cart-item__delete-bg');
    expect(deleteBg.attributes('tabindex')).toBe('0');
    expect(deleteBg.attributes('aria-hidden')).toBeUndefined();
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
        selected: true,
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

  it('переключает выбор товара через localStorage-хелпер (guest)', async () => {
    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    const checkbox = wrapper.find('[data-testid="cart-item-select"] input');
    expect(checkbox.exists()).toBe(true);
    await checkbox.setValue(false);
    await flushPromises();

    expect(mockSelectItem).toHaveBeenCalledWith(10, false);
    expect(mockApiSelectCartItem).not.toHaveBeenCalled();
  });

  it('выбирает все товары через localStorage-хелпер (guest)', async () => {
    mockGuestItems.value = [
      { product_id: 10, quantity: 3, selected: false, name: 'Гостевой товар', price: 1500, stock: 8, images: [] },
    ];

    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    const selectAll = wrapper.find('[data-testid="cart-select-all"] input');
    await selectAll.setValue(true);
    await flushPromises();

    expect(mockSelectAll).toHaveBeenCalled();
    expect(mockApiSelectAll).not.toHaveBeenCalled();
  });

  it('считает итоги только по выбранным товарам для гостя', async () => {
    mockGuestItems.value = [
      { product_id: 11, quantity: 2, selected: true, name: 'Выбранный товар', price: 1000, stock: 5, images: [] },
      { product_id: 12, quantity: 1, selected: false, name: 'Невыбранный товар', price: 2000, stock: 3, images: [] },
    ];
    mockCartCount.value = 2;

    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.text()).toContain('Выбранный товар');
    expect(wrapper.text()).toContain('Невыбранный товар');
    // Итог по выбранным: 2 * 1000 = 2000; полный итог 4000 не показывается
    expect(wrapper.text()).toContain('2 000');
    expect(wrapper.text()).not.toContain('4 000');
  });
});

describe('Cart.vue — свайп-удаление (mobile)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsAuthenticated.value = true;
    mockGuestItems.value = [];
    mockCartCount.value = 0;
    mockRecipients.value = [];
    mockRecipientsLoading.value = false;
    getSupplierCityCode.mockResolvedValue(44);
    mockGet.mockImplementation((url) => {
      if (url === '/cart/') return Promise.resolve({ data: structuredClone(mockCartWithItems) });
      if (url === '/auth/profile') return Promise.resolve({ data: {} });
      if (url === '/delivery-methods/') return Promise.resolve({ data: [] });
      if (url === '/me/recipients/') return Promise.resolve({ data: mockSavedRecipients });
      return Promise.resolve({ data: {} });
    });
  });

  it('свайп влево открывает подложку, клик по .cart-item__delete-bg удаляет товар', async () => {
    mockDelete.mockResolvedValue({ data: {} });
    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    const item = wrapper.find('[data-cart-item-id="101"]');
    // обёртка контента существует
    expect(item.find('.cart-item__content').exists()).toBe(true);

    // симуляция горизонтального свайпа влево
    await item.trigger('touchstart', { touches: [{ clientX: 300, clientY: 100 }] });
    await item.trigger('touchmove', { touches: [{ clientX: 200, clientY: 105 }] });
    await item.trigger('touchend');

    expect(item.classes()).toContain('cart-item--swiped');
    // подложка — сиблинг обёртки, НЕ внутри неё (не трансформируется)
    expect(item.find('.cart-item__content .cart-item__delete-bg').exists()).toBe(false);
    const deleteBg = item.element.querySelector(':scope > .cart-item__delete-bg');
    expect(deleteBg).not.toBeNull();

    await item.find('.cart-item__delete-bg').trigger('click');
    await flushPromises();

    expect(mockDelete).toHaveBeenCalledWith('/cart/remove/101');
  });

  it('вертикальный жест не открывает свайп', async () => {
    const wrapper = mount(Cart, { global: { plugins: [router] } });
    await flushPromises();

    const item = wrapper.find('[data-cart-item-id="101"]');
    await item.trigger('touchstart', { touches: [{ clientX: 300, clientY: 100 }] });
    await item.trigger('touchmove', { touches: [{ clientX: 280, clientY: 200 }] });
    await item.trigger('touchend');

    expect(item.classes()).not.toContain('cart-item--swiped');
  });
});
