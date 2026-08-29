import { ref, computed, reactive, watch } from 'vue';
import api from '@/services/api';
import { useAuth } from '@/composables/useAuth';

const GUEST_CART_KEY = 'guest_cart';

const loadGuestCart = () => {
  try {
    const raw = localStorage.getItem(GUEST_CART_KEY);
    if (!raw) return [];
    const items = JSON.parse(raw);
    // Миграция старых записей без флага selected: считаем выбранными.
    return items.map((item) => ({
      ...item,
      selected: item.selected !== undefined ? item.selected : true,
    }));
  } catch {
    return [];
  }
};

const saveGuestCart = (items) => {
  localStorage.setItem(GUEST_CART_KEY, JSON.stringify(items));
};

const getGuestCartCount = () => {
  return loadGuestCart().reduce((sum, item) => sum + (item.quantity || 0), 0);
};

const cartCount = ref(getGuestCartCount());

// Per-product количество в корзине: { [productId]: qty }.
// Гость — синхронно из localStorage, auth — из GET /cart/ через syncCartCount().
const cartQuantities = reactive({});

const _syncQuantities = (items) => {
  for (const key of Object.keys(cartQuantities)) {
    delete cartQuantities[key];
  }
  for (const item of items || []) {
    if (item.quantity > 0) {
      cartQuantities[item.product_id] = item.quantity;
    }
  }
};

// Init для гостя: map из localStorage синхронно при загрузке модуля.
_syncQuantities(loadGuestCart());

// Однократный sync для auth при первом useCart() (watch не ловит already-logged-in).
let authSyncInitialized = false;

export const useCart = () => {
  const { isAuthenticated } = useAuth();

  const addToCart = async (productId, quantity = 1, product = null) => {
    if (product && quantity > product.stock) {
      throw new Error(
        `Недостаточно товара в наличии. Доступно: ${product.stock}, запрошено: ${quantity}`
      );
    }
    if (isAuthenticated.value) {
      await api.post('/cart/add', { product_id: productId, quantity });
      await syncCartCount();
    } else {
      const items = loadGuestCart();
      const existing = items.find((i) => i.product_id === productId);
      const newQuantity = (existing?.quantity || 0) + quantity;
      if (product && newQuantity > product.stock) {
        throw new Error(
          `Недостаточно товара в наличии. Доступно: ${product.stock}, в корзине будет: ${newQuantity}`
        );
      }
      if (existing) {
        existing.quantity = newQuantity;
      } else {
        items.push({
          product_id: productId,
          quantity,
          name: product?.name || '',
          price: product?.price || 0,
          stock: product?.stock || 0,
          images: product?.images || [],
          supplier_id: product?.supplier_id ?? null,
          selected: true,
        });
      }
      saveGuestCart(items);
      cartCount.value = getGuestCartCount();
      _syncQuantities(items);
    }
  };

  const removeFromCart = async (productId) => {
    const items = loadGuestCart().filter((i) => i.product_id !== productId);
    saveGuestCart(items);
    cartCount.value = getGuestCartCount();
    _syncQuantities(items);
  };

  const updateQuantity = async (productId, quantity) => {
    const items = loadGuestCart();
    const item = items.find((i) => i.product_id === productId);
    if (item) {
      item.quantity = quantity;
      if (item.quantity <= 0) {
        const idx = items.indexOf(item);
        items.splice(idx, 1);
      }
      saveGuestCart(items);
      cartCount.value = getGuestCartCount();
      _syncQuantities(items);
    }
  };

  const getGuestCartItems = () => loadGuestCart();

  const getSelectedGuestCartItems = () => loadGuestCart().filter((i) => i.selected);

  const selectItem = async (productId, selected) => {
    const items = loadGuestCart();
    const item = items.find((i) => i.product_id === productId);
    if (item) {
      item.selected = selected;
      saveGuestCart(items);
    }
  };

  const selectAll = async () => {
    const items = loadGuestCart().map((i) => ({ ...i, selected: true }));
    saveGuestCart(items);
  };

  const deselectAll = async () => {
    const items = loadGuestCart().map((i) => ({ ...i, selected: false }));
    saveGuestCart(items);
  };

  const clearGuestCart = () => {
    localStorage.removeItem(GUEST_CART_KEY);
    cartCount.value = 0;
    _syncQuantities([]);
  };

  const mergeCartOnLogin = async () => {
    const items = loadGuestCart();
    if (items.length === 0) return;
    const payload = items.map((i) => ({
      product_id: i.product_id,
      quantity: i.quantity,
      selected: i.selected,
    }));
    await api.post('/cart/merge', { items: payload });
    clearGuestCart();
    await syncCartCount();
  };

  const syncCartCount = async () => {
    if (isAuthenticated.value) {
      try {
        const { data } = await api.get('/cart/');
        const count = (data.items || []).reduce((sum, item) => sum + (item.quantity || 0), 0);
        cartCount.value = count;
        _syncQuantities(data.items || []);
      } catch {
        cartCount.value = 0;
        _syncQuantities([]);
      }
    } else {
      cartCount.value = getGuestCartCount();
      _syncQuantities(loadGuestCart());
    }
  };

  watch(isAuthenticated, (val) => {
    if (val) {
      syncCartCount();
    } else {
      cartCount.value = getGuestCartCount();
      _syncQuantities(loadGuestCart());
    }
  });

  // Однократный sync для auth при первом вызове (watch не ловит already-logged-in).
  if (!authSyncInitialized && isAuthenticated.value) {
    authSyncInitialized = true;
    syncCartCount();
  }

  return {
    cartCount: computed(() => cartCount.value),
    addToCart,
    removeFromCart,
    updateQuantity,
    getGuestCartItems,
    getSelectedGuestCartItems,
    selectItem,
    selectAll,
    deselectAll,
    clearGuestCart,
    mergeCartOnLogin,
    syncCartCount,
    getQuantityInCart: (productId) => cartQuantities[productId] || 0,
    isInCart: (productId) => !!cartQuantities[productId],
  };
};
