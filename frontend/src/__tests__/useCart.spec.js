import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ref } from 'vue';

const GUEST_CART_KEY = 'guest_cart';

// Соседние тесты (например, Cart.spec.js) мокируют useCart целиком.
// Гарантируем, что здесь тестируется реальная реализация composable.
vi.unmock('@/composables/useCart');

vi.mock('@/composables/useAuth', () => ({
  useAuth: () => ({
    isAuthenticated: ref(false),
  }),
}));

const { useCart } = await import('@/composables/useCart');

describe('useCart — гостевая корзина', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('addToCart сохраняет selected=true по умолчанию', async () => {
    const { addToCart, getSelectedGuestCartItems } = useCart();
    await addToCart(1, 2, { id: 1, name: 'Товар', price: 1000, stock: 5, supplier_id: 1 });

    expect(getSelectedGuestCartItems()).toHaveLength(1);
    expect(getSelectedGuestCartItems()[0].selected).toBe(true);
  });

  it('selectItem снимает выбор с товара', async () => {
    const { addToCart, selectItem, getSelectedGuestCartItems } = useCart();
    await addToCart(1, 2, { id: 1, name: 'Товар', price: 1000, stock: 5, supplier_id: 1 });

    await selectItem(1, false);

    expect(getSelectedGuestCartItems()).toHaveLength(0);
  });

  it('selectAll выбирает все товары', async () => {
    const { addToCart, selectItem, selectAll, getSelectedGuestCartItems } = useCart();
    await addToCart(1, 1, { id: 1, name: 'A', price: 1000, stock: 5, supplier_id: 1 });
    await addToCart(2, 1, { id: 2, name: 'B', price: 2000, stock: 5, supplier_id: 1 });
    await selectItem(1, false);

    await selectAll();

    expect(getSelectedGuestCartItems()).toHaveLength(2);
  });

  it('deselectAll снимает выбор со всех товаров', async () => {
    const { addToCart, deselectAll, getSelectedGuestCartItems } = useCart();
    await addToCart(1, 1, { id: 1, name: 'A', price: 1000, stock: 5, supplier_id: 1 });
    await addToCart(2, 1, { id: 2, name: 'B', price: 2000, stock: 5, supplier_id: 1 });

    await deselectAll();

    expect(getSelectedGuestCartItems()).toHaveLength(0);
  });

  it('loadGuestCart восстанавливает selected=true для старых записей без флага', () => {
    localStorage.setItem(GUEST_CART_KEY, JSON.stringify([
      { product_id: 1, quantity: 1, name: 'A', price: 1000 },
    ]));

    const { getSelectedGuestCartItems } = useCart();

    expect(getSelectedGuestCartItems()).toHaveLength(1);
  });
});
