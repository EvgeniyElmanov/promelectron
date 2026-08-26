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

const mockPost = vi.hoisted(() => vi.fn());
const mockGet = vi.hoisted(() => vi.fn());

vi.mock('@/services/api', () => ({
  default: {
    get: (...args) => mockGet(...args),
    post: (...args) => mockPost(...args),
  },
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

describe('useCart — merge при входе', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    mockPost.mockResolvedValue({ data: {} });
    mockGet.mockResolvedValue({ data: { items: [] } });
  });

  it('mergeCartOnLogin отправляет товары на /cart/merge и очищает localStorage', async () => {
    localStorage.setItem(GUEST_CART_KEY, JSON.stringify([
      { product_id: 1, quantity: 2, name: 'A', price: 1000, stock: 5, supplier_id: 1, selected: true },
      { product_id: 2, quantity: 1, name: 'B', price: 2000, stock: 5, supplier_id: 1, selected: true },
    ]));

    const { mergeCartOnLogin, getGuestCartItems } = useCart();
    await mergeCartOnLogin();

    expect(mockPost).toHaveBeenCalledWith('/cart/merge', {
      items: [
        { product_id: 1, quantity: 2, selected: true },
        { product_id: 2, quantity: 1, selected: true },
      ],
    });
    expect(getGuestCartItems()).toHaveLength(0);
  });

  it('mergeCartOnLogin переносит selected=false из гостевой корзины', async () => {
    localStorage.setItem(GUEST_CART_KEY, JSON.stringify([
      { product_id: 1, quantity: 2, name: 'A', price: 1000, stock: 5, supplier_id: 1, selected: false },
    ]));

    const { mergeCartOnLogin } = useCart();
    await mergeCartOnLogin();

    expect(mockPost).toHaveBeenCalledWith('/cart/merge', {
      items: [
        { product_id: 1, quantity: 2, selected: false },
      ],
    });
  });

  it('mergeCartOnLogin не вызывает запрос при пустой гостевой корзине', async () => {
    const { mergeCartOnLogin } = useCart();
    await mergeCartOnLogin();

    expect(mockPost).not.toHaveBeenCalled();
  });

  it('mergeCartOnLogin не очищает localStorage при ошибке запроса', async () => {
    localStorage.setItem(GUEST_CART_KEY, JSON.stringify([
      { product_id: 1, quantity: 2, name: 'A', price: 1000, stock: 5, supplier_id: 1, selected: true },
    ]));
    mockPost.mockRejectedValue(new Error('Network error'));

    const { mergeCartOnLogin, getGuestCartItems } = useCart();
    await expect(mergeCartOnLogin()).rejects.toThrow('Network error');

    expect(getGuestCartItems()).toHaveLength(1);
  });
});
