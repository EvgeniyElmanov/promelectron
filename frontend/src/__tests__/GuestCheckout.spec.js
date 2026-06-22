import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import { ref } from 'vue';
import GuestCheckout from '../views/GuestCheckout.vue';
import { getSupplierCityCode } from '@/api/cdek';

const mockGet = vi.fn();
const mockPost = vi.fn();

vi.mock('@/services/api', () => ({
  default: {
    get: (...args) => mockGet(...args),
    post: (...args) => mockPost(...args),
  },
}));

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ add: vi.fn() }),
}));

const mockGuestItems = ref([
  { product_id: 1, quantity: 2, name: 'Товар А', price: 1000, stock: 5, images: [], supplier_id: 1 },
  { product_id: 2, quantity: 1, name: 'Товар Б', price: 2000, stock: 3, images: [], supplier_id: 1 },
]);
let mockCleared = false;
let storedGuestEmail = null;

vi.mock('@/api/cdek', () => ({
  getSupplierCityCode: vi.fn(() => Promise.resolve(44)),
}));

vi.mock('@/composables/useCart', () => ({
  useCart: () => ({
    getGuestCartItems: () => mockGuestItems.value,
    clearGuestCart: () => { mockCleared = true; },
  }),
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
    { path: '/guest-order-success/:id', component: { template: '<div>Success</div>' } },
  ],
});

const selectedDelivery = { tariff_code: 136, price: 350, delivery_mode: 'PVZ' };

describe('GuestCheckout.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockCleared = false;
    storedGuestEmail = null;
    mockGuestItems.value = [
      { product_id: 1, quantity: 2, name: 'Товар А', price: 1000, stock: 5, images: [] },
      { product_id: 2, quantity: 1, name: 'Товар Б', price: 2000, stock: 3, images: [] },
    ];
    getSupplierCityCode.mockResolvedValue(44);
    mockGet.mockResolvedValue({ data: {} });
    vi.stubGlobal('localStorage', {
      getItem: () => null,
      setItem: (_key, value) => { storedGuestEmail = value; },
      removeItem: vi.fn(),
    });
    delete window.location;
    window.location = { href: '' };
  });

  it('отображает товары из гостевой корзины', async () => {
    const wrapper = mount(GuestCheckout, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.text()).toContain('Товар А');
    expect(wrapper.text()).toContain('Товар Б');
    expect(wrapper.text()).toContain('4\u00A0000'); // 2*1000 + 1*2000
  });

  it('отображает виджет доставки СДЭК', async () => {
    const wrapper = mount(GuestCheckout, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.find('[data-testid="cdek-delivery-widget"]').exists()).toBe(true);
    expect(wrapper.text()).toContain('Способ доставки');
  });

  it('показывает форму контактных данных', async () => {
    const wrapper = mount(GuestCheckout, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.find('[data-testid="guest-email"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="guest-first-name"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="guest-last-name"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="guest-phone"]').exists()).toBe(true);
  });

  it('показывает ссылку "Уже есть аккаунт? Войти"', async () => {
    const wrapper = mount(GuestCheckout, { global: { plugins: [router] } });
    await flushPromises();

    const link = wrapper.find('[data-testid="guest-login-link"]');
    expect(link.exists()).toBe(true);
    expect(link.attributes('href')).toContain('/login?redirect=/guest-checkout');
  });

  it('показывает галочку "Сохранить адрес"', async () => {
    const wrapper = mount(GuestCheckout, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.find('[data-testid="guest-save-address"]').exists()).toBe(true);
  });

  it('кнопка оформления disabled без email, имени, телефона и доставки', async () => {
    const wrapper = mount(GuestCheckout, { global: { plugins: [router] } });
    await flushPromises();

    const btn = wrapper.find('[data-testid="guest-checkout-submit"]');
    expect(btn.attributes('disabled')).toBeDefined();
  });

  it('валидирует email перед отправкой', async () => {
    const wrapper = mount(GuestCheckout, { global: { plugins: [router] } });
    await flushPromises();

    await wrapper.find('[data-testid="guest-email"]').setValue('invalid-email');
    await wrapper.find('[data-testid="guest-first-name"]').setValue('Иван');
    await wrapper.find('[data-testid="guest-last-name"]').setValue('Иванов');
    await wrapper.find('[data-testid="guest-phone"]').setValue('+79990001122');
    wrapper.vm.selectedDelivery = selectedDelivery;
    await flushPromises();

    await wrapper.find('[data-testid="guest-checkout-submit"]').trigger('click');
    await flushPromises();

    expect(wrapper.find('[data-testid="guest-email-error"]').text()).toContain('Некорректный email');
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('валидирует телефон перед отправкой', async () => {
    const wrapper = mount(GuestCheckout, { global: { plugins: [router] } });
    await flushPromises();

    await wrapper.find('[data-testid="guest-email"]').setValue('test@example.com');
    await wrapper.find('[data-testid="guest-first-name"]').setValue('Иван');
    await wrapper.find('[data-testid="guest-last-name"]').setValue('Иванов');
    await wrapper.find('[data-testid="guest-phone"]').setValue('89990001122');
    wrapper.vm.selectedDelivery = selectedDelivery;
    await flushPromises();

    await wrapper.find('[data-testid="guest-checkout-submit"]').trigger('click');
    await flushPromises();

    expect(wrapper.find('[data-testid="guest-phone-error"]').text()).toContain('+7');
    expect(mockPost).not.toHaveBeenCalled();
  });

  it('создаёт заказ и платёж, затем редиректит на confirmation_url', async () => {
    mockPost.mockImplementation((url) => {
      if (url === '/orders/create-guest') {
        return Promise.resolve({
          data: { id: 42, guest_email: 'test@example.com', total_price: 4350 },
        });
      }
      if (url === '/payments/guest/42/') {
        return Promise.resolve({
          data: { payment_id: 99, status: 'pending', confirmation_url: 'https://yoomoney.ru/checkout/42/pay', amount: 4350 },
        });
      }
      return Promise.resolve({ data: {} });
    });

    const wrapper = mount(GuestCheckout, { global: { plugins: [router] } });
    await flushPromises();

    await wrapper.find('[data-testid="guest-email"]').setValue('test@example.com');
    await wrapper.find('[data-testid="guest-first-name"]').setValue('Иван');
    await wrapper.find('[data-testid="guest-last-name"]').setValue('Иванов');
    await wrapper.find('[data-testid="guest-phone"]').setValue('+79990001122');
    wrapper.vm.selectedDelivery = selectedDelivery;
    await wrapper.find('[data-testid="guest-save-address"]').setValue(true);
    await flushPromises();

    const btn = wrapper.find('[data-testid="guest-checkout-submit"]');
    expect(btn.attributes('disabled')).toBeUndefined();

    await btn.trigger('click');
    await flushPromises();

    expect(mockPost).toHaveBeenCalledWith('/orders/create-guest', expect.objectContaining({
      guest_email: 'test@example.com',
      guest_phone: '+79990001122',
      recipient_first_name: 'Иван',
      recipient_last_name: 'Иванов',
      save_address: true,
      items: [
        { product_id: 1, quantity: 2 },
        { product_id: 2, quantity: 1 },
      ],
      cdek_delivery: expect.objectContaining({ tariff_code: 136, price: 350 }),
    }));
    expect(mockPost).toHaveBeenCalledWith('/payments/guest/42/', { guest_email: 'test@example.com' });
    expect(mockCleared).toBe(true);
    expect(storedGuestEmail).toBe('test@example.com');
    expect(window.location.href).toBe('https://yoomoney.ru/checkout/42/pay');
  });

  it('показывает ошибку при неудачном создании заказа', async () => {
    mockPost.mockRejectedValue({ response: { data: { detail: 'Недостаточно товара' } } });

    const wrapper = mount(GuestCheckout, { global: { plugins: [router] } });
    await flushPromises();

    wrapper.vm.guestEmail = 'test@example.com';
    wrapper.vm.guestFirstName = 'Иван';
    wrapper.vm.guestLastName = 'Иванов';
    wrapper.vm.guestPhone = '+79990001122';
    wrapper.vm.selectedDelivery = selectedDelivery;
    await flushPromises();

    const btn = wrapper.find('[data-testid="guest-checkout-submit"]');
    await btn.trigger('click');
    await flushPromises();

    expect(mockPost).toHaveBeenCalled();
    expect(mockCleared).toBe(false);
  });

  it('передаёт isFallback=true, когда город поставщика не определён', async () => {
    getSupplierCityCode.mockResolvedValueOnce(null);
    const wrapper = mount(GuestCheckout, { global: { plugins: [router] } });
    await flushPromises();

    const widget = wrapper.findComponent({ name: 'CdekDeliveryWidget' });
    expect(widget.exists()).toBe(true);
    expect(widget.props('isFallback')).toBe(true);
    expect(wrapper.find('[data-testid="cdek-fallback-hint"]').exists()).toBe(true);
  });
});
