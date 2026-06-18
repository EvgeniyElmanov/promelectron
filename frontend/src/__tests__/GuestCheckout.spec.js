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

vi.mock('@/components/CdekDeliveryWidget.vue', () => ({
  default: {
    name: 'CdekDeliveryWidget',
    template: '<div data-testid="cdek-delivery-widget"><button @click="select">Select delivery</button></div>',
    props: ['modelValue', 'items'],
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
    { path: '/guest-order-success/:id', component: { template: '<div>Success</div>' } },
  ],
});

const selectedDelivery = { tariff_code: 136, price: 350, delivery_mode: 'PVZ' };

describe('GuestCheckout.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockCleared = false;
    mockGuestItems.value = [
      { product_id: 1, quantity: 2, name: 'Товар А', price: 1000, stock: 5, images: [] },
      { product_id: 2, quantity: 1, name: 'Товар Б', price: 2000, stock: 3, images: [] },
    ];
    mockGet.mockResolvedValue({ data: {} });
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

  it('кнопка оформления disabled без email, имени, телефона и доставки', async () => {
    const wrapper = mount(GuestCheckout, { global: { plugins: [router] } });
    await flushPromises();

    const btn = wrapper.find('[data-testid="guest-checkout-submit"]');
    expect(btn.attributes('disabled')).toBeDefined();
  });

  it('отправляет запрос на создание гостевого заказа', async () => {
    mockPost.mockResolvedValue({
      data: { id: 42, guest_email: 'test@example.com', total_price: 4350 },
    });
    const push = vi.spyOn(router, 'push');

    const wrapper = mount(GuestCheckout, { global: { plugins: [router] } });
    await flushPromises();

    // Fill contact fields
    await wrapper.find('[data-testid="guest-email"]').setValue('test@example.com');
    await wrapper.find('[data-testid="guest-first-name"]').setValue('Иван');
    await wrapper.find('[data-testid="guest-last-name"]').setValue('Иванов');
    await wrapper.find('[data-testid="guest-phone"]').setValue('+79990001122');

    // Select delivery
    wrapper.vm.selectedDelivery = selectedDelivery;
    await flushPromises();

    const btn = wrapper.find('[data-testid="guest-checkout-submit"]');
    expect(btn.attributes('disabled')).toBeUndefined();

    await btn.trigger('click');
    await flushPromises();

    expect(mockPost).toHaveBeenCalledWith('/orders/create-guest', expect.objectContaining({
      guest_email: 'test@example.com',
      guest_name: 'Иван Иванов',
      guest_phone: '+79990001122',
      recipient_first_name: 'Иван',
      recipient_last_name: 'Иванов',
      items: [
        { product_id: 1, quantity: 2 },
        { product_id: 2, quantity: 1 },
      ],
      cdek_delivery: expect.objectContaining({ tariff_code: 136, price: 350 }),
    }));
    expect(mockCleared).toBe(true);
    expect(push).toHaveBeenCalledWith('/guest-order-success/42?email=test%40example.com');
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
});
