import { describe, it, expect, vi, beforeEach } from 'vitest';

const GUEST_CART_KEY = 'guest_cart';

// Соседние тесты (например, Cart.spec.js) мокируют useCart целиком.
// Гарантируем, что здесь тестируется реальная реализация composable.
vi.unmock('@/composables/useCart');

const mockIsAuthenticated = vi.hoisted(() => ({ ref: null }));

vi.mock('@/composables/useAuth', async () => {
  const { ref } = await import('vue');
  if (!mockIsAuthenticated.ref) {
    mockIsAuthenticated.ref = ref(false);
  }
  return {
    useAuth: () => ({
      isAuthenticated: mockIsAuthenticated.ref,
    }),
  };
});

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

describe('useCart — cartQuantities (гость)', () => {
  beforeEach(() => {
    localStorage.clear();
    mockIsAuthenticated.ref.value = false;
    const { clearGuestCart } = useCart();
    clearGuestCart();
  });

  it('addToCart заполняет map, getQuantityInCart/isInCart читают его', async () => {
    const { addToCart, getQuantityInCart, isInCart } = useCart();
    await addToCart(1, 2, { id: 1, name: 'A', price: 1000, stock: 5, supplier_id: 1 });

    expect(getQuantityInCart(1)).toBe(2);
    expect(isInCart(1)).toBe(true);
    expect(isInCart(2)).toBe(false);
  });

  it('повторный addToCart увеличивает quantity в map', async () => {
    const { addToCart, getQuantityInCart } = useCart();
    await addToCart(1, 1, { id: 1, name: 'A', price: 1000, stock: 5, supplier_id: 1 });
    await addToCart(1, 1, { id: 1, name: 'A', price: 1000, stock: 5, supplier_id: 1 });

    expect(getQuantityInCart(1)).toBe(2);
  });

  it('updateQuantity обновляет map, quantity<=0 удаляет ключ', async () => {
    const { addToCart, updateQuantity, getQuantityInCart, isInCart } = useCart();
    await addToCart(1, 2, { id: 1, name: 'A', price: 1000, stock: 5, supplier_id: 1 });

    await updateQuantity(1, 3);
    expect(getQuantityInCart(1)).toBe(3);

    await updateQuantity(1, 0);
    expect(getQuantityInCart(1)).toBe(0);
    expect(isInCart(1)).toBe(false);
  });

  it('removeFromCart удаляет товар из map', async () => {
    const { addToCart, removeFromCart, isInCart } = useCart();
    await addToCart(1, 1, { id: 1, name: 'A', price: 1000, stock: 5, supplier_id: 1 });

    await removeFromCart(1);

    expect(isInCart(1)).toBe(false);
  });

  it('clearGuestCart очищает map', async () => {
    const { addToCart, clearGuestCart, isInCart } = useCart();
    await addToCart(1, 1, { id: 1, name: 'A', price: 1000, stock: 5, supplier_id: 1 });

    clearGuestCart();

    expect(isInCart(1)).toBe(false);
  });
});

describe('useCart — cartQuantities (auth)', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    mockIsAuthenticated.ref.value = false;
    const { clearGuestCart } = useCart();
    clearGuestCart();
    mockGet.mockResolvedValue({ data: { items: [] } });
  });

  it('syncCartCount заполняет map из GET /cart/', async () => {
    mockGet.mockResolvedValue({
      data: { items: [{ product_id: 7, quantity: 3 }, { product_id: 8, quantity: 1 }] },
    });
    mockIsAuthenticated.ref.value = true;

    const { syncCartCount, getQuantityInCart, isInCart } = useCart();
    await syncCartCount();

    expect(getQuantityInCart(7)).toBe(3);
    expect(getQuantityInCart(8)).toBe(1);
    expect(isInCart(9)).toBe(false);
  });

  it('исчезнувший из /cart/ товар удаляется из map', async () => {
    mockGet.mockResolvedValue({
      data: { items: [{ product_id: 7, quantity: 2 }] },
    });

    const { syncCartCount, isInCart } = useCart();
    mockIsAuthenticated.ref.value = true;
    await vi.waitFor(() => {
      expect(isInCart(7)).toBe(true);
    });

    mockGet.mockResolvedValue({ data: { items: [] } });
    await syncCartCount();
    expect(isInCart(7)).toBe(false);
  });

  it('при logout map переключается на guest_cart', async () => {
    localStorage.setItem(GUEST_CART_KEY, JSON.stringify([
      { product_id: 5, quantity: 2, name: 'A', price: 1000, stock: 5, supplier_id: 1, selected: true },
    ]));
    mockIsAuthenticated.ref.value = true;

    const { isInCart, getQuantityInCart } = useCart();
    // logout: watch(isAuthenticated) пересобирает map из localStorage
    mockIsAuthenticated.ref.value = false;
    await vi.waitFor(() => {
      expect(getQuantityInCart(5)).toBe(2);
    });
    expect(isInCart(5)).toBe(true);
  });
});
