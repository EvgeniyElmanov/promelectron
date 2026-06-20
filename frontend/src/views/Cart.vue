<template>
  <div class="cart" data-testid="cart-page">
    <!-- Header -->
    <div class="cart__header">
      <h1 class="cart__title" data-testid="cart-title">
        Корзина
        <span v-if="itemCount > 0" class="cart__count">{{ itemCount }}</span>
      </h1>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="cart__items">
      <SkeletonCartItem v-for="i in 3" :key="'sk' + i" />
    </div>

    <!-- Empty -->
    <div v-else-if="!cart.items || cart.items.length === 0" class="cart__empty">
      <svg class="cart__empty-icon" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4H6z"/>
        <line x1="3" y1="6" x2="21" y2="6"/>
        <path d="M16 10a4 4 0 01-8 0"/>
      </svg>
      <p class="cart__empty-text">Ваша корзина пуста</p>
      <router-link to="/" class="cart__empty-btn">Перейти в каталог</router-link>
    </div>

    <!-- Cart Content -->
    <div v-else class="cart__content">
      <!-- Items List -->
      <div class="cart__items">
        <div
          v-for="item in cart.items"
          :key="item.id"
          class="cart-item"
          :class="{ 'cart-item--swiped': swipedItemId === item.id }"
          data-testid="cart-item"
          :data-cart-item-id="item.id"
          @touchstart="handleTouchStart($event, item.id)"
          @touchmove="handleTouchMove($event, item.id)"
          @touchend="handleTouchEnd(item.id)"
        >
          <!-- Product Image -->
          <div class="cart-item__image" @click="goToProduct(item.product?.id)">
            <img
              v-if="item.product?.images?.length"
              :src="item.product.images[0]"
              :alt="item.product.name"
              class="cart-item__img"
            />
            <span v-else class="cart-item__placeholder">{{ item.product?.name?.charAt(0) || '?' }}</span>
          </div>

          <!-- Product Info -->
          <div class="cart-item__info">
            <p class="cart-item__name" @click="goToProduct(item.product?.id)">
              {{ item.product?.name || 'Товар' }}
            </p>
            <p class="cart-item__price-per-unit">{{ formatPrice(item.product?.price || 0) }} ₽ / шт</p>

            <div class="cart-item__bottom">
              <!-- Quantity Controls -->
              <div class="cart-item__qty">
                <button
                  class="cart-item__qty-btn"
                  :disabled="item.quantity <= 1 || updatingId === item.id"
                  @click="updateQuantity(item.id, item.quantity - 1)"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/></svg>
                </button>
                <span class="cart-item__qty-value">{{ item.quantity }}</span>
                <button
                  class="cart-item__qty-btn"
                  :disabled="item.quantity >= (item.product?.stock || 0) || updatingId === item.id"
                  @click="updateQuantity(item.id, item.quantity + 1)"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                </button>
              </div>

              <!-- Line Total -->
              <span class="cart-item__total">{{ formatPrice((item.product?.price || 0) * item.quantity) }} ₽</span>
            </div>

            <!-- Stock Warning -->
            <p v-if="item.product?.stock !== undefined && item.quantity >= item.product.stock" class="cart-item__stock-warning">
              Максимум в наличии
            </p>
          </div>

          <!-- Desktop Remove -->
          <button class="cart-item__remove-desktop" @click="removeItem(item.id)" title="Удалить">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
            </svg>
          </button>

          <!-- Mobile Swipe Delete Background -->
          <button class="cart-item__delete-bg" @click="removeItem(item.id)">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
            </svg>
            <span>Удалить</span>
          </button>
        </div>
      </div>

      <!-- Summary -->
      <div class="cart__summary">
        <div class="cart__summary-section">
          <h3 class="cart__summary-title">Ваш заказ</h3>

          <div class="cart__summary-row">
            <span>Товары ({{ itemCount }})</span>
            <span>{{ formatPrice(itemsTotal) }} ₽</span>
          </div>
          <div class="cart__summary-row">
            <span>Доставка</span>
            <span>{{ deliveryPrice > 0 ? formatPrice(deliveryPrice) + ' ₽' : 'Бесплатно' }}</span>
          </div>
          <div class="cart__summary-divider"></div>
          <div class="cart__summary-row cart__summary-row--total">
            <span>Итого</span>
            <span>{{ formatPrice(orderTotal) }} ₽</span>
          </div>
        </div>

        <div v-if="isAuthenticated" class="cart__summary-section">
          <CdekDeliveryWidget
            v-model="selectedDelivery"
            :items="cart.items"
            :supplier-city-code="supplierCityCode"
            :is-fallback="isFallback"
          />

          <div class="cart__recipient">
            <h4 class="cart__recipient-title">Получатель</h4>
            <div class="cart__recipient-fields">
              <div class="cart__recipient-field">
                <label for="recipient-first-name">Имя</label>
                <input
                  id="recipient-first-name"
                  v-model="recipientFirstName"
                  type="text"
                  placeholder="Иван"
                  data-testid="recipient-first-name"
                />
              </div>
              <div class="cart__recipient-field">
                <label for="recipient-last-name">Фамилия</label>
                <input
                  id="recipient-last-name"
                  v-model="recipientLastName"
                  type="text"
                  placeholder="Иванов"
                  data-testid="recipient-last-name"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Sticky Checkout Bar -->
    <div v-if="cart.items && cart.items.length > 0" class="cart__checkout-bar">
      <div class="cart__checkout-info">
        <span class="cart__checkout-label">Итого</span>
        <span class="cart__checkout-price">{{ formatPrice(orderTotal) }} ₽</span>
      </div>
      <button
        class="cart__checkout-btn"
        data-testid="checkout-button"
        :disabled="creatingOrder || (isAuthenticated && (!isDeliveryValid || !isRecipientValid))"
        @click="createOrder"
      >
        {{ creatingOrder ? 'Оформление...' : 'Оформить заказ' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/services/api';
import { useAuth } from '@/composables/useAuth';
import { useCart } from '@/composables/useCart';
import { useToast } from '@/composables/useToast';
import { getSupplierCityCode } from '@/api/cdek';
import CdekDeliveryWidget from '@/components/CdekDeliveryWidget.vue';
import SkeletonCartItem from '@/components/SkeletonCartItem.vue';

const cart = ref({ items: [] });
const loading = ref(true);
const creatingOrder = ref(false);
const updatingId = ref(null);
const selectedDelivery = ref(null);
const recipientFirstName = ref('');
const recipientLastName = ref('');
const supplierCityCode = ref(44);
const isFallback = ref(false);
const router = useRouter();
const { add: toast } = useToast();
const { isAuthenticated } = useAuth();
const { getGuestCartItems, updateQuantity: updateGuestQuantity, removeFromCart: removeGuestItem, syncCartCount } = useCart();

// Swipe state
const touchStartX = ref(0);
const swipedItemId = ref(null);

const isDeliveryValid = computed(() => {
  return selectedDelivery.value && selectedDelivery.value.tariff_code;
});

const isRecipientValid = computed(() => {
  return recipientFirstName.value.trim().length > 0 && recipientLastName.value.trim().length > 0;
});

const supplierId = computed(() => {
  const firstItem = cart.value.items?.[0];
  return firstItem?.product?.supplier_id ?? null;
});

const loadSupplierCityCode = async () => {
  if (!supplierId.value) {
    isFallback.value = true;
    supplierCityCode.value = 44;
    return;
  }
  try {
    const code = await getSupplierCityCode(supplierId.value);
    if (code == null) {
      isFallback.value = true;
      supplierCityCode.value = 44;
    } else {
      isFallback.value = false;
      supplierCityCode.value = code;
    }
  } catch {
    isFallback.value = true;
    supplierCityCode.value = 44;
  }
};

const itemCount = computed(() => {
  return cart.value.items.reduce((sum, item) => sum + (item.quantity || 0), 0);
});

const itemsTotal = computed(() => {
  return cart.value.items.reduce((total, item) => {
    return total + (item.product?.price || 0) * (item.quantity || 0);
  }, 0);
});

const deliveryPrice = computed(() => {
  return selectedDelivery.value ? Number(selectedDelivery.value.price) : 0;
});

const orderTotal = computed(() => itemsTotal.value + deliveryPrice.value);

const formatPrice = (price) => {
  return Number(price).toLocaleString('ru-RU');
};

const fetchCart = async () => {
  loading.value = true;
  try {
    if (isAuthenticated.value) {
      const { data } = await api.get('/cart/');
      cart.value = data;
    } else {
      const items = getGuestCartItems();
      cart.value = {
        id: 0,
        user_id: 0,
        items: items.map(item => ({
          id: `guest-${item.product_id}`,
          product_id: item.product_id,
          quantity: item.quantity,
          product: {
            id: item.product_id,
            name: item.name,
            price: item.price,
            stock: item.stock,
            images: item.images || [],
          },
        })),
      };
    }
  } catch {
    toast('Не удалось загрузить корзину', 'error');
  } finally {
    loading.value = false;
    await syncCartCount();
  }
};

const goToProduct = (productId) => {
  if (productId) router.push(`/product/${productId}`);
};

const updateQuantity = async (itemId, newQuantity) => {
  if (newQuantity < 1) return;
  updatingId.value = itemId;
  try {
    if (isAuthenticated.value) {
      await api.put(`/cart/update/${itemId}`, { quantity: newQuantity });
    } else {
      const productId = Number(String(itemId).replace('guest-', ''));
      await updateGuestQuantity(productId, newQuantity);
    }
    await fetchCart();
  } catch {
    toast('Не удалось обновить количество', 'error');
  } finally {
    updatingId.value = null;
  }
};

const removeItem = async (itemId) => {
  swipedItemId.value = null;
  try {
    if (isAuthenticated.value) {
      await api.delete(`/cart/remove/${itemId}`);
    } else {
      const productId = Number(String(itemId).replace('guest-', ''));
      await removeGuestItem(productId);
    }
    await fetchCart();
    toast('Товар удалён из корзины', 'info');
  } catch {
    toast('Не удалось удалить товар', 'error');
  }
};

const createOrder = async () => {
  if (creatingOrder.value) return;
  if (!isAuthenticated.value) {
    router.push('/login?redirect=/cart');
    return;
  }
  if (!isDeliveryValid.value) {
    toast('Выберите доставку СДЭК', 'error');
    return;
  }
  if (!isRecipientValid.value) {
    toast('Укажите имя и фамилию получателя', 'error');
    return;
  }
  creatingOrder.value = true;
  try {
    const { data: order } = await api.post('/orders/create', {
      cdek_delivery: { ...selectedDelivery.value },
      recipient_first_name: recipientFirstName.value.trim(),
      recipient_last_name: recipientLastName.value.trim(),
    });
    toast('Заказ успешно создан!', 'success');
    await router.push(`/checkout/${order.id}`);
  } catch (err) {
    const detail = err.response?.data?.detail;
    toast(detail || 'Не удалось создать заказ', 'error');
  } finally {
    creatingOrder.value = false;
  }
};

// Swipe handlers
const handleTouchStart = (event, itemId) => {
  touchStartX.value = event.touches[0].clientX;
  if (swipedItemId.value !== itemId) swipedItemId.value = null;
};

const handleTouchMove = (event, itemId) => {
  if (!touchStartX.value) return;
  const diff = touchStartX.value - event.touches[0].clientX;
  if (diff > 60) {
    swipedItemId.value = itemId;
  } else if (diff < -40) {
    swipedItemId.value = null;
  }
};

const handleTouchEnd = () => {
  touchStartX.value = 0;
};

onMounted(() => {
  fetchCart();
});

watch(supplierId, () => {
  loadSupplierCityCode();
}, { immediate: true });
</script>

<style scoped>
.cart {
  max-width: 800px;
  margin: 0 auto;
  padding: 12px 12px calc(100px + var(--bottom-nav-height, 56px));
}

@media (min-width: 768px) {
  .cart {
    padding: 20px 20px 40px;
  }
}

/* Header */
.cart__header {
  padding: 8px 0 16px;
}

.cart__title {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text);
  display: flex;
  align-items: center;
  gap: 8px;
}

.cart__count {
  font-size: 15px;
  font-weight: 500;
  color: var(--color-text-secondary);
  background: var(--color-bg);
  padding: 2px 10px;
  border-radius: 12px;
}

/* Loading */
.cart__loading {
  text-align: center;
  padding: 60px 20px;
  color: var(--color-text-secondary);
}

.cart__loading .spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 12px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Empty */
.cart__empty {
  text-align: center;
  padding: 60px 20px;
}

.cart__empty-icon {
  color: var(--color-border);
  margin-bottom: 16px;
}

.cart__empty-text {
  font-size: 16px;
  color: var(--color-text-secondary);
  margin-bottom: 20px;
}

.cart__empty-btn {
  display: inline-block;
  padding: 12px 24px;
  border-radius: 12px;
  background: var(--color-primary);
  color: #fff;
  font-size: 15px;
  font-weight: 500;
}

/* Items */
.cart__items {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.cart-item {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  background: var(--color-bg-white);
  border-radius: 14px;
  overflow: hidden;
  transition: transform 0.2s ease;
}

.cart-item--swiped {
  transform: translateX(-80px);
}

/* Image */
.cart-item__image {
  width: 72px;
  height: 72px;
  border-radius: 10px;
  overflow: hidden;
  flex-shrink: 0;
  cursor: pointer;
  background: var(--color-bg);
  display: flex;
  align-items: center;
  justify-content: center;
}

.cart-item__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cart-item__placeholder {
  font-size: 24px;
  font-weight: 700;
  color: rgba(0, 0, 0, 0.12);
}

/* Info */
.cart-item__info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.cart-item__name {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text);
  line-height: 1.3;
  cursor: pointer;
  word-break: break-word;
}

.cart-item__price-per-unit {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.cart-item__bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 4px;
}

/* Quantity */
.cart-item__qty {
  display: flex;
  align-items: center;
  gap: 2px;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  overflow: hidden;
}

.cart-item__qty-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-white);
  color: var(--color-text);
  transition: background 0.15s;
}

.cart-item__qty-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.cart-item__qty-btn:active:not(:disabled) {
  background: var(--color-bg);
}

.cart-item__qty-value {
  min-width: 32px;
  text-align: center;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
}

/* Line Total */
.cart-item__total {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-text);
}

/* Stock Warning */
.cart-item__stock-warning {
  font-size: 12px;
  color: var(--color-danger);
}

/* Desktop Remove */
.cart-item__remove-desktop {
  display: none;
  width: 36px;
  height: 36px;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  color: var(--color-text-secondary);
  background: transparent;
  transition: background 0.15s, color 0.15s;
  flex-shrink: 0;
}

.cart-item__remove-desktop:hover {
  background: #fff0f0;
  color: var(--color-danger);
}

@media (min-width: 640px) {
  .cart-item__remove-desktop {
    display: flex;
  }
}

/* Mobile Swipe Delete */
.cart-item__delete-bg {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 80px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  background: var(--color-danger);
  color: #fff;
  font-size: 12px;
  font-weight: 500;
  border: none;
  border-radius: 0 14px 14px 0;
  z-index: -1;
}

@media (min-width: 640px) {
  .cart-item__delete-bg {
    display: none;
  }
}

/* Summary */
.cart__summary {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

@media (min-width: 768px) {
  .cart__summary {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    align-items: start;
  }
}

.cart__summary-section {
  background: var(--color-bg-white);
  border-radius: 14px;
  padding: 16px;
}

.cart__summary-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 14px;
}

.cart__summary-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  color: var(--color-text);
  padding: 6px 0;
}

.cart__summary-free {
  color: #0d7a3e;
  font-weight: 500;
}

/* Delivery selection */
.cart__delivery-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cart__delivery-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-radius: 10px;
  border: 2px solid var(--color-border);
  cursor: pointer;
  transition: border-color 0.2s;
}

.cart__delivery-option--active {
  border-color: var(--color-primary);
}

.cart__delivery-radio {
  width: 18px;
  height: 18px;
  accent-color: var(--color-primary);
  flex-shrink: 0;
}

.cart__delivery-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.cart__delivery-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
}

.cart__delivery-days {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.cart__delivery-price {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  white-space: nowrap;
}

.cart__summary-divider {
  height: 1px;
  background: var(--color-border);
  margin: 8px 0;
}

.cart__summary-row--total {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text);
}

/* Recipient */
.cart__recipient {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--color-border);
}

.cart__recipient-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 10px;
}

.cart__recipient-fields {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.cart__recipient-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.cart__recipient-field label {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.cart__recipient-field input {
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-white);
  font-size: 15px;
  color: var(--color-text);
  width: 100%;
}

.cart__recipient-field input:focus {
  outline: none;
  border-color: var(--color-primary);
}

/* Sticky Checkout Bar */
.cart__checkout-bar {
  position: fixed;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: 800px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px calc(12px + var(--bottom-nav-height, 56px));
  background: var(--color-bg-white);
  border-top: 1px solid var(--color-border);
  z-index: 50;
}

@media (min-width: 768px) {
  .cart__checkout-bar {
    position: static;
    transform: none;
    margin-top: 20px;
    padding: 16px;
    border-radius: 14px;
    border: none;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  }
}

.cart__checkout-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.cart__checkout-label {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.cart__checkout-price {
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text);
}

.cart__checkout-btn {
  flex: 1;
  max-width: 220px;
  padding: 14px 20px;
  border-radius: 12px;
  background: var(--color-primary);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  transition: opacity 0.15s;
}

.cart__checkout-btn:disabled {
  background: #cccccc;
  cursor: not-allowed;
}

@media (min-width: 768px) {
  .cart__checkout-btn {
    max-width: 240px;
    font-size: 16px;
  }
}
</style>
