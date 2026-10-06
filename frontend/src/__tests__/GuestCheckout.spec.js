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

const mockCalculateDelivery = vi.hoisted(() => vi.fn());

vi.mock('@/api/cdek', () => ({
  getSupplierCityCode: vi.fn(() => Promise.resolve(44)),
  calculateDelivery: mockCalculateDelivery,
}));

vi.mock('@/composables/useCart', () => ({
  useCart: () => ({
    getGuestCartItems: () => mockGuestItems.value,
    clearGuestCart: vi.fn(),
  }),
}));

vi.mock('@/components/CdekDeliveryWidget.vue', () => ({
  default: {
    name: 'CdekDeliveryWidget',
    template: '<div data-testid="cdek-delivery-widget"></div>',
    props: ['modelValue', 'items', 'isFallback'],
  },
}));

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: { template: '<div>Home</div>' } },
    { path: '/login', component: { template: '<div>Login</div>' } },
    { path: '/checkout/:id', component: { template: '<div>Checkout</div>' } },
  ],
});

describe('GuestCheckout.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGuestItems.value = [
      { product_id: 1, quantity: 2, name: 'Товар А', price: 1000, stock: 5, images: [], supplier_id: 1 },
      { product_id: 2, quantity: 1, name: 'Товар Б', price: 2000, stock: 3, images: [], supplier_id: 1 },
    ];
    getSupplierCityCode.mockResolvedValue(44);
    mockGet.mockResolvedValue({ data: {} });
  });

  it('редиректит на /login?redirect=/cart при монтировании', async () => {
    mount(GuestCheckout, { global: { plugins: [router] } });
    await flushPromises();

    expect(router.currentRoute.value.path).toBe('/login');
    expect(router.currentRoute.value.query.redirect).toBe('/cart');
  });

  it('409 при создании заказа: пересчитывает доставку и повторяет заказ только после подтверждения', async () => {
    mockPost
      .mockRejectedValueOnce({
        response: { status: 409, data: { detail: 'Стоимость доставки устарела. Пересчитайте доставку и повторите заказ.' } },
      })
      .mockResolvedValueOnce({ data: { id: 7, guest_email: 'guest@example.com' } });
    mockCalculateDelivery.mockResolvedValue({
      tariffs: [{ tariff_code: 136, tariff_name: 'Посылка склад-склад', price: 420, period_min: 3, period_max: 5 }],
    });

    const wrapper = mount(GuestCheckout, { global: { plugins: [router] } });
    await flushPromises();

    wrapper.vm.selectedDelivery = { tariff_code: 136, price: 350, delivery_mode: 'PVZ', delivery_point: 'MSK123' };
    wrapper.vm.guestEmail = 'guest@example.com';
    wrapper.vm.guestFirstName = 'Иван';
    wrapper.vm.guestLastName = 'Иванов';
    wrapper.vm.guestPhone = '+79990001122';
    await flushPromises();

    await wrapper.find('[data-testid="guest-checkout-submit"]').trigger('click');
    await flushPromises();

    // Пересчёт вызван, но заказ НЕ повторён без подтверждения пользователя.
    expect(mockPost).toHaveBeenCalledTimes(1);
    expect(mockPost).toHaveBeenCalledWith('/orders/create-guest/', expect.anything());
    expect(mockCalculateDelivery).toHaveBeenCalledWith(expect.objectContaining({
      supplier_id: 1,
      delivery_point: 'MSK123',
    }));
    const notice = wrapper.find('[data-testid="delivery-price-update-notice"]');
    expect(notice.exists()).toBe(true);
    expect(notice.text()).toContain('350');
    expect(notice.text()).toContain('420');
    expect(wrapper.vm.selectedDelivery.price).toBe(420);

    await wrapper.find('[data-testid="delivery-price-update-confirm"]').trigger('click');
    await flushPromises();

    expect(mockPost).toHaveBeenCalledTimes(2);
    expect(mockPost).toHaveBeenLastCalledWith('/orders/create-guest/', expect.objectContaining({
      cdek_delivery: expect.objectContaining({ price: 420 }),
    }));
    expect(wrapper.find('[data-testid="delivery-price-update-notice"]').exists()).toBe(false);
  });

  it('503 при создании заказа: показывает «недоступен» с возможностью повторить', async () => {
    mockPost.mockRejectedValue({
      response: { status: 503, data: { detail: 'Сервис расчёта доставки временно недоступен' } },
    });

    const wrapper = mount(GuestCheckout, { global: { plugins: [router] } });
    await flushPromises();

    wrapper.vm.selectedDelivery = { tariff_code: 136, price: 350, delivery_mode: 'PVZ', delivery_point: 'MSK123' };
    wrapper.vm.guestEmail = 'guest@example.com';
    wrapper.vm.guestFirstName = 'Иван';
    wrapper.vm.guestLastName = 'Иванов';
    wrapper.vm.guestPhone = '+79990001122';
    await flushPromises();

    await wrapper.find('[data-testid="guest-checkout-submit"]').trigger('click');
    await flushPromises();

    expect(mockCalculateDelivery).not.toHaveBeenCalled();
    const notice = wrapper.find('[data-testid="delivery-unavailable-notice"]');
    expect(notice.exists()).toBe(true);
    expect(notice.text()).toContain('временно недоступен');
  });
});
