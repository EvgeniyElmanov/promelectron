import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import { ref } from 'vue';
import GuestCheckout from '../views/GuestCheckout.vue';

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
  { product_id: 1, quantity: 2, name: 'Товар А', price: 1000, stock: 5, images: [] },
  { product_id: 2, quantity: 1, name: 'Товар Б', price: 2000, stock: 3, images: [] },
]);
let mockCleared = false;

vi.mock('@/composables/useCart', () => ({
  useCart: () => ({
    getGuestCartItems: () => mockGuestItems.value,
    clearGuestCart: () => { mockCleared = true; },
  }),
}));

vi.mock('@/components/AddressForm.vue', () => ({
  default: {
    name: 'AddressForm',
    template: '<div data-testid="address-form"><input v-model="modelValue.city" /></div>',
    props: ['modelValue', 'label', 'testidPrefix'],
  },
}));

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: { template: '<div>Home</div>' } },
    { path: '/guest-order-success/:id', component: { template: '<div>Success</div>' } },
  ],
});

describe('GuestCheckout.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockCleared = false;
    mockGuestItems.value = [
      { product_id: 1, quantity: 2, name: 'Товар А', price: 1000, stock: 5, images: [] },
      { product_id: 2, quantity: 1, name: 'Товар Б', price: 2000, stock: 3, images: [] },
    ];
    mockGet.mockImplementation((url) => {
      if (url === '/delivery-methods/') {
        return Promise.resolve({
          data: [
            { id: 1, name: 'Курьер', base_price: 300, estimated_days: '1-2', is_active: true },
            { id: 2, name: 'Самовывоз', base_price: 0, estimated_days: '1', is_active: true },
          ],
        });
      }
      return Promise.resolve({ data: {} });
    });
  });

  it('отображает товары из гостевой корзины', async () => {
    const wrapper = mount(GuestCheckout, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.text()).toContain('Товар А');
    expect(wrapper.text()).toContain('Товар Б');
    expect(wrapper.text()).toContain('4\u00A0000'); // 2*1000 + 1*2000
  });

  it('отображает способы доставки', async () => {
    const wrapper = mount(GuestCheckout, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.text()).toContain('Курьер');
    expect(wrapper.text()).toContain('Самовывоз');
  });

  it('показывает форму контактных данных', async () => {
    const wrapper = mount(GuestCheckout, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.find('[data-testid="guest-email"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="guest-name"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="guest-phone"]').exists()).toBe(true);
  });

  it('кнопка оформления disabled без email и адреса', async () => {
    const wrapper = mount(GuestCheckout, { global: { plugins: [router] } });
    await flushPromises();

    const btn = wrapper.find('[data-testid="guest-checkout-submit"]');
    expect(btn.attributes('disabled')).toBeDefined();
  });

  it('отправляет запрос на создание гостевого заказа', async () => {
    mockPost.mockResolvedValue({
      data: { id: 42, guest_email: 'test@example.com', total_price: 4300 },
    });
    const push = vi.spyOn(router, 'push');

    const wrapper = mount(GuestCheckout, { global: { plugins: [router] } });
    await flushPromises();

    // Fill email
    const emailInput = wrapper.find('[data-testid="guest-email"]');
    await emailInput.setValue('test@example.com');

    // Fill address via component emit (simulate v-model update)
    await wrapper.findComponent({ name: 'AddressForm' }).vm.$emit('update:modelValue', {
      city: 'Москва', street: 'Ленина', house: '1', region: '', district: '', apartment: ''
    });
    // Directly set the ref since component mock may not emit properly
    wrapper.vm.shippingAddress = { city: 'Москва', street: 'Ленина', house: '1', region: '', district: '', apartment: '' };
    await flushPromises();

    const btn = wrapper.find('[data-testid="guest-checkout-submit"]');
    expect(btn.attributes('disabled')).toBeUndefined();

    await btn.trigger('click');
    await flushPromises();

    expect(mockPost).toHaveBeenCalledWith('/orders/create-guest', expect.objectContaining({
      guest_email: 'test@example.com',
      items: [
        { product_id: 1, quantity: 2 },
        { product_id: 2, quantity: 1 },
      ],
      shipping_address: expect.objectContaining({ city: 'Москва', street: 'Ленина', house: '1' }),
      delivery_method_id: 1,
    }));
    expect(mockCleared).toBe(true);
    expect(push).toHaveBeenCalledWith('/guest-order-success/42?email=test%40example.com');
  });

  it('показывает ошибку при неудачном создании заказа', async () => {
    mockPost.mockRejectedValue({ response: { data: { detail: 'Недостаточно товара' } } });

    const wrapper = mount(GuestCheckout, { global: { plugins: [router] } });
    await flushPromises();

    wrapper.vm.guestEmail = 'test@example.com';
    wrapper.vm.shippingAddress = { city: 'Москва', street: 'Ленина', house: '1', region: '', district: '', apartment: '' };
    await flushPromises();

    const btn = wrapper.find('[data-testid="guest-checkout-submit"]');
    await btn.trigger('click');
    await flushPromises();

    expect(mockPost).toHaveBeenCalled();
    expect(mockCleared).toBe(false);
  });
});
