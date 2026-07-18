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

vi.mock('@/api/cdek', () => ({
  getSupplierCityCode: vi.fn(() => Promise.resolve(44)),
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
});
