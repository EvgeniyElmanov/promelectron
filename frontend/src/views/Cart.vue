<template>
  <div class="cart" data-testid="cart-page">
    <!-- Header -->
    <div class="cart__header">
      <h1 class="cart__title" data-testid="cart-title">
        Корзина
        <span v-if="itemCount > 0" class="cart__count">{{ itemCount }}</span>
      </h1>
      <label
        v-if="cart.items && cart.items.length > 0"
        class="cart__select-all"
        data-testid="cart-select-all"
      >
        <input
          type="checkbox"
          :checked="areAllSelected"
          :indeterminate.prop="isPartiallySelected"
          @change="toggleSelectAll"
        />
        <span>Выбрать все</span>
      </label>
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
      <AppButton variant="primary" @click="router.push('/catalog')">Перейти в каталог</AppButton>
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
          @touchcancel="handleTouchCancel(item.id)"
        >
          <!-- Mobile Swipe Delete Background (static layer under content) -->
          <button
            class="cart-item__delete-bg"
            :tabindex="swipedItemId === item.id ? 0 : -1"
            :aria-hidden="swipedItemId === item.id ? null : 'true'"
            @click="removeItem(item.id)"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
            </svg>
            <span>Удалить</span>
          </button>

          <!-- Swipeable Content -->
          <div class="cart-item__content">
            <!-- Item selection checkbox -->
            <label class="cart-item__select" data-testid="cart-item-select">
              <input
                type="checkbox"
                :checked="item.selected !== false"
                aria-label="Выбрать товар"
                @change="toggleItemSelection(item)"
              />
            </label>

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
                    aria-label="Уменьшить количество"
                    :disabled="item.quantity <= 1 || updatingId === item.id"
                    @click="updateQuantity(item.id, item.quantity - 1)"
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/></svg>
                  </button>
                  <span class="cart-item__qty-value">{{ item.quantity }}</span>
                  <button
                    class="cart-item__qty-btn"
                    aria-label="Увеличить количество"
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
          </div>
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
          <h4 class="cart__step-title">Шаг 1. Доставка</h4>
          <CdekDeliveryWidget
            v-model="selectedDelivery"
            :items="selectedItems"
            :supplier-city-code="supplierCityCode"
            :is-fallback="isFallback"
          />

          <div class="cart__recipient">
            <div class="cart__recipient-header">
              <h4 class="cart__step-title">Шаг 2. Получатель</h4>
              <router-link to="/profile/recipients" class="cart__recipient-manage">
                Управлять
              </router-link>
            </div>

            <div v-if="recipientsLoading" class="cart__recipient-loading">Загрузка...</div>

            <div v-else-if="recipients.length > 0" class="cart__recipient-select">
              <select
                v-model="selectedRecipientId"
                class="field__input"
                data-testid="recipient-select"
              >
                <option
                  v-for="recipient in recipients"
                  :key="recipient.id"
                  :value="recipient.id"
                >
                  {{ recipient.last_name }} {{ recipient.first_name }}
                  <template v-if="recipient.patronymic">{{ recipient.patronymic }}</template>
                  {{ recipient.phone }}
                  <template v-if="recipient.is_default">(по умолчанию)</template>
                </option>
              </select>
              <AppButton
                v-if="isSelectedRecipient"
                variant="secondary"
                size="sm"
                class="cart__recipient-new-button"
                data-testid="recipient-new-button"
                @click="selectedRecipientId = null; applyRecipient(null)"
              >
                Новый получатель
              </AppButton>
            </div>

            <div class="cart__recipient-fields">
              <div class="cart__recipient-field field">
                <label class="field__label" for="recipient-first-name">Имя <span class="field__required">*</span></label>
                <input
                  id="recipient-first-name"
                  v-model="recipientFirstName"
                  type="text"
                  class="field__input"
                  placeholder="Иван"
                  :disabled="isSelectedRecipient"
                  data-testid="recipient-first-name"
                />
              </div>
              <div class="cart__recipient-field field">
                <label class="field__label" for="recipient-last-name">Фамилия <span class="field__required">*</span></label>
                <input
                  id="recipient-last-name"
                  v-model="recipientLastName"
                  type="text"
                  class="field__input"
                  placeholder="Иванов"
                  :disabled="isSelectedRecipient"
                  data-testid="recipient-last-name"
                />
              </div>
              <div class="cart__recipient-field field">
                <label class="field__label" for="recipient-country-code">Страна <span class="field__required">*</span></label>
                <select
                  id="recipient-country-code"
                  v-model="recipientCountryCode"
                  class="field__input"
                  :disabled="isSelectedRecipient"
                  data-testid="recipient-country-code"
                >
                  <option value="RU">Россия</option>
                  <option value="KZ">Казахстан</option>
                  <option value="BY">Беларусь</option>
                </select>
              </div>
              <div v-if="recipientCountryCode === 'RU'" class="cart__recipient-field field">
                <label class="field__label" for="recipient-patronymic">Отчество</label>
                <input
                  id="recipient-patronymic"
                  v-model="recipientPatronymic"
                  type="text"
                  class="field__input"
                  placeholder="Иванович"
                  :disabled="isSelectedRecipient"
                  data-testid="recipient-patronymic"
                />
              </div>
              <div class="cart__recipient-field cart__recipient-field--wide field">
                <label class="field__label" for="recipient-phone">Телефон <span class="field__required">*</span></label>
                <input
                  id="recipient-phone"
                  v-model="recipientPhone"
                  type="tel"
                  class="field__input"
                  placeholder="+7 (999) 000-00-00"
                  :disabled="isSelectedRecipient"
                  data-testid="recipient-phone"
                />
              </div>
            </div>
            <div v-if="recipientError" class="cart__recipient-error">{{ recipientError }}</div>
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
      <AppButton
        variant="primary"
        block
        class="cart__checkout-btn"
        data-testid="checkout-button"
        :loading="creatingOrder"
        :disabled="creatingOrder || selectedItems.length === 0 || (isAuthenticated && (!isDeliveryValid || !isRecipientValid))"
        @click="createOrder"
      >
        {{ creatingOrder ? 'Оформление...' : 'Оформить заказ' }}
      </AppButton>
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
import { useRecipients } from '@/composables/useRecipients';
import { getSupplierCityCode } from '@/api/cdek';
import { selectCartItem, selectAllCartItems, deselectAllCartItems } from '@/api/cart';
import { normalizePhone } from '@/composables/useGuestCheckout';
import { formatPrice } from '@/utils/price';
import CdekDeliveryWidget from '@/components/CdekDeliveryWidget.vue';
import SkeletonCartItem from '@/components/SkeletonCartItem.vue';
import AppButton from '@/components/ui/AppButton.vue';

const PHONE_REGEX = /^\+7\d{10}$/;
const NAME_REGEX = /^[A-Za-zА-Яа-яЁё\- ]+$/;

const cart = ref({ items: [] });
const loading = ref(true);
const creatingOrder = ref(false);
const updatingId = ref(null);
const selectedDelivery = ref(null);
const selectedRecipientId = ref(null);
const hasUserSelectedRecipient = ref(false);
const recipientFirstName = ref('');
const recipientLastName = ref('');
const recipientPatronymic = ref('');
const recipientPhone = ref('');
const recipientCountryCode = ref('RU');
const recipientError = ref('');
const supplierCityCode = ref(44);
const isFallback = ref(false);
const router = useRouter();
const { add: toast } = useToast();
const { isAuthenticated } = useAuth();
const {
  getGuestCartItems,
  selectItem: selectGuestItem,
  selectAll: selectAllGuestItems,
  deselectAll: deselectAllGuestItems,
  updateQuantity: updateGuestQuantity,
  removeFromCart: removeGuestItem,
  syncCartCount,
} = useCart();
const { recipients, loading: recipientsLoading, loadRecipients, defaultRecipient } = useRecipients();

// Swipe state
const touchStartX = ref(0);
const touchStartY = ref(0);
const swipedItemId = ref(null);

const selectedItems = computed(() => {
  return (cart.value.items || []).filter((item) => item.selected !== false);
});

const areAllSelected = computed(() => {
  const items = cart.value.items || [];
  return items.length > 0 && items.every((item) => item.selected !== false);
});

const isPartiallySelected = computed(() => {
  return selectedItems.value.length > 0 && !areAllSelected.value;
});

const toggleItemSelection = async (item) => {
  const newValue = item.selected === false;
  if (isAuthenticated.value) {
    // Оптимистичное обновление; при ошибке — откат через fetchCart()
    item.selected = newValue;
    try {
      await selectCartItem(item.id, newValue);
    } catch {
      toast('Не удалось изменить выбор товара', 'error');
      await fetchCart();
    }
    return;
  }
  try {
    await selectGuestItem(item.product_id, newValue);
    await fetchCart();
  } catch {
    toast('Не удалось изменить выбор товара', 'error');
  }
};

const toggleSelectAll = async () => {
  const target = !areAllSelected.value;
  if (isAuthenticated.value) {
    cart.value.items.forEach((item) => {
      item.selected = target;
    });
    try {
      if (target) {
        await selectAllCartItems();
      } else {
        await deselectAllCartItems();
      }
    } catch {
      toast('Не удалось изменить выбор товаров', 'error');
      await fetchCart();
    }
    return;
  }
  try {
    if (target) {
      await selectAllGuestItems();
    } else {
      await deselectAllGuestItems();
    }
    await fetchCart();
  } catch {
    toast('Не удалось изменить выбор товаров', 'error');
  }
};

const isDeliveryValid = computed(() => {
  return selectedDelivery.value && selectedDelivery.value.tariff_code;
});

const isSelectedRecipient = computed(() => selectedRecipientId.value !== null);

const isRecipientValid = computed(() => {
  if (isSelectedRecipient.value) {
    return true;
  }
  const firstName = recipientFirstName.value.trim();
  const lastName = recipientLastName.value.trim();
  const phone = normalizePhone(recipientPhone.value);
  const patronymic = recipientPatronymic.value.trim();
  if (!firstName || !NAME_REGEX.test(firstName)) return false;
  if (!lastName || !NAME_REGEX.test(lastName)) return false;
  if (recipientCountryCode.value === 'RU' && patronymic && !NAME_REGEX.test(patronymic)) return false;
  return PHONE_REGEX.test(phone);
});

const supplierId = computed(() => {
  const firstItem = selectedItems.value?.[0] ?? cart.value.items?.[0];
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
  return selectedItems.value.reduce((sum, item) => sum + (item.quantity || 0), 0);
});

const itemsTotal = computed(() => {
  return selectedItems.value.reduce((total, item) => {
    return total + (item.product?.price || 0) * (item.quantity || 0);
  }, 0);
});

const deliveryPrice = computed(() => {
  return selectedDelivery.value ? Number(selectedDelivery.value.price) : 0;
});

const orderTotal = computed(() => itemsTotal.value + deliveryPrice.value);

// Сигнатура выбранного состава: тариф CDEK зависит от набора товаров и количества (вес).
const selectionSignature = computed(() =>
  selectedItems.value.map((item) => `${item.id}:${item.quantity}`).join(',')
);

// F002: инвалидация выбранной доставки при смене состава выбранных или поставщика.
// Сброс только если доставка уже выбрана — первичная загрузка корзины её не трогает.
watch([selectionSignature, supplierId], () => {
  if (selectedDelivery.value) {
    selectedDelivery.value = null;
  }
});

const applyRecipient = (recipient) => {
  if (!recipient) {
    recipientFirstName.value = '';
    recipientLastName.value = '';
    recipientPatronymic.value = '';
    recipientPhone.value = '';
    recipientCountryCode.value = 'RU';
    return;
  }
  recipientFirstName.value = recipient.first_name || '';
  recipientLastName.value = recipient.last_name || '';
  recipientPatronymic.value = recipient.patronymic || '';
  recipientPhone.value = recipient.phone || '';
  recipientCountryCode.value = recipient.country_code || 'RU';
};

watch(selectedRecipientId, (id) => {
  recipientError.value = '';
  hasUserSelectedRecipient.value = true;
  if (id === null) {
    applyRecipient(null);
    return;
  }
  const recipient = recipients.value.find((r) => r.id === id);
  applyRecipient(recipient);
});

watch(defaultRecipient, (recipient) => {
  if (
    recipient &&
    selectedRecipientId.value === null &&
    recipients.value.length > 0 &&
    !hasUserSelectedRecipient.value
  ) {
    selectedRecipientId.value = recipient.id;
    applyRecipient(recipient);
  }
}, { immediate: false });

const fetchCart = async () => {
  loading.value = true;
  try {
    if (isAuthenticated.value) {
      const { data } = await api.get('/cart/');
      cart.value = data;
      await loadRecipients();
      if (defaultRecipient.value && !hasUserSelectedRecipient.value) {
        selectedRecipientId.value = defaultRecipient.value.id;
        applyRecipient(defaultRecipient.value);
      }
    } else {
      const items = getGuestCartItems();
      cart.value = {
        id: 0,
        user_id: 0,
        items: items.map(item => ({
          id: `guest-${item.product_id}`,
          product_id: item.product_id,
          quantity: item.quantity,
          selected: item.selected !== false,
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

const buildOrderPayload = () => {
  const payload = {
    cdek_delivery: { ...selectedDelivery.value },
  };

  if (isSelectedRecipient.value) {
    payload.recipient_id = selectedRecipientId.value;
    return payload;
  }

  payload.recipient_first_name = recipientFirstName.value.trim();
  payload.recipient_last_name = recipientLastName.value.trim();
  payload.recipient_phone = normalizePhone(recipientPhone.value);
  payload.recipient_country_code = recipientCountryCode.value;
  if (recipientCountryCode.value === 'RU' && recipientPatronymic.value.trim()) {
    payload.recipient_patronymic = recipientPatronymic.value.trim();
  }
  return payload;
};

const createOrder = async () => {
  if (creatingOrder.value) return;
  if (!isAuthenticated.value) {
    router.push('/login?redirect=/cart');
    return;
  }
  if (selectedItems.value.length === 0) {
    toast('Выберите товары для оформления', 'error');
    return;
  }
  if (!isDeliveryValid.value) {
    toast('Выберите доставку СДЭК', 'error');
    return;
  }
  if (!isRecipientValid.value) {
    toast('Укажите корректные данные получателя', 'error');
    return;
  }
  creatingOrder.value = true;
  recipientError.value = '';
  try {
    const payload = buildOrderPayload();
    const { data: order } = await api.post('/orders/create/', payload);
    toast('Заказ успешно создан!', 'success');
    await syncCartCount();
    await router.push(`/checkout/${order.id}`);
  } catch (err) {
    const detail = err.response?.data?.detail;
    recipientError.value = detail || 'Не удалось создать заказ';
    toast(recipientError.value, 'error');
  } finally {
    creatingOrder.value = false;
  }
};

// Swipe handlers
const handleTouchStart = (event, itemId) => {
  touchStartX.value = event.touches[0].clientX;
  touchStartY.value = event.touches[0].clientY;
  if (swipedItemId.value !== itemId) swipedItemId.value = null;
};

const handleTouchMove = (event, itemId) => {
  if (!touchStartX.value || !touchStartY.value) return;
  const diffX = touchStartX.value - event.touches[0].clientX;
  const diffY = touchStartY.value - event.touches[0].clientY;
  // Vertical scroll wins: ignore the gesture when |dy| > |dx|
  if (Math.abs(diffY) > Math.abs(diffX)) return;
  if (diffX > 60) {
    swipedItemId.value = itemId;
  } else if (diffX < -40) {
    swipedItemId.value = null;
  }
};

const handleTouchEnd = () => {
  touchStartX.value = 0;
  touchStartY.value = 0;
};

const handleTouchCancel = () => {
  touchStartX.value = 0;
  touchStartY.value = 0;
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
  padding: 12px 12px calc(100px + var(--bottom-nav-height, 56px) + env(safe-area-inset-bottom, 0px));
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
  font-size: var(--font-size-h3);
  font-weight: var(--font-weight-bold);
  color: var(--color-text);
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.cart__count {
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  background: var(--color-bg);
  padding: 2px 10px;
  border-radius: var(--radius-pill);
}

.cart__select-all {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: var(--space-2);
  font-size: var(--font-size-body-sm);
  color: var(--color-text);
  cursor: pointer;
}

.cart__select-all input {
  width: 18px;
  height: 18px;
  accent-color: var(--color-primary);
  flex-shrink: 0;
}

@media (min-width: 768px) {
  .cart__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .cart__select-all {
    margin-top: 0;
  }
}

/* Empty */
.cart__empty {
  text-align: center;
  padding: 60px 20px;
}

.cart__empty-icon {
  color: var(--color-border);
  margin-bottom: var(--space-4);
}

.cart__empty-text {
  font-size: var(--font-size-body);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-5);
}

/* Items */
.cart__items {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.cart-item {
  position: relative;
  border-radius: var(--radius-lg);
  overflow: hidden;
  touch-action: pan-y;
}

.cart-item__content {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-3);
  background: var(--color-bg-white);
  border-radius: var(--radius-lg);
  transition: transform 0.2s ease;
}

.cart-item--swiped .cart-item__content {
  transform: translateX(-80px);
}

.cart-item__select {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  /* touch-target ~44x36px: 20px чекбокс + padding */
  padding: 24px 8px 0;
}

.cart-item__select input {
  width: 20px;
  height: 20px;
  accent-color: var(--color-primary);
  cursor: pointer;
}

/* Image */
.cart-item__image {
  width: 72px;
  height: 72px;
  border-radius: var(--radius-md);
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
  font-size: var(--font-size-h3);
  font-weight: var(--font-weight-bold);
  color: var(--color-text-muted);
}

/* Info */
.cart-item__info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.cart-item__name {
  font-size: var(--font-size-body-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text);
  line-height: 1.3;
  cursor: pointer;
  word-break: break-word;
}

.cart-item__price-per-unit {
  font-size: var(--font-size-caption);
  color: var(--color-text-secondary);
}

.cart-item__bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: var(--space-1);
}

/* Quantity */
.cart-item__qty {
  display: flex;
  align-items: center;
  gap: 2px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
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

@media (max-width: 767px) {
  .cart-item__qty-btn {
    min-width: 40px;
    min-height: 40px;
  }
}

.cart-item__qty-value {
  min-width: 32px;
  text-align: center;
  font-size: var(--font-size-body-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text);
}

/* Line Total */
.cart-item__total {
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-bold);
  color: var(--color-text);
}

/* Stock Warning */
.cart-item__stock-warning {
  font-size: var(--font-size-caption);
  color: var(--color-danger);
}

/* Desktop Remove */
.cart-item__remove-desktop {
  display: none;
  width: 36px;
  height: 36px;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  background: transparent;
  transition: background 0.15s, color 0.15s;
  flex-shrink: 0;
}

.cart-item__remove-desktop:hover {
  background: color-mix(in srgb, var(--color-danger) 8%, transparent);
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
  gap: var(--space-1);
  background: var(--color-danger);
  color: var(--color-white);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-medium);
  border: none;
  border-radius: 0 var(--radius-lg) var(--radius-lg) 0;
  z-index: 0;
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
  border-radius: var(--radius-lg);
  padding: var(--space-4);
}

.cart__summary-title {
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-bold);
  color: var(--color-text);
  margin-bottom: 14px;
}

.cart__summary-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: var(--font-size-body-sm);
  color: var(--color-text);
  padding: 6px 0;
}

.cart__summary-divider {
  height: 1px;
  background: var(--color-border);
  margin: 8px 0;
}

.cart__summary-row--total {
  font-size: var(--font-size-body-lg);
  font-weight: var(--font-weight-bold);
  color: var(--color-text);
}

/* Recipient */
.cart__recipient {
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-border);
}

.cart__recipient-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-2);
}

.cart__step-title {
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  margin: 0 0 var(--space-3);
}

.cart__recipient-manage {
  font-size: var(--font-size-caption);
  color: var(--color-primary);
  text-decoration: none;
}

.cart__recipient-loading {
  font-size: var(--font-size-body-sm);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-2);
}

.cart__recipient-select {
  margin-bottom: var(--space-2);
}

.cart__recipient-new-button {
  margin-top: var(--space-2);
}

.cart__recipient-fields {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-2);
}

@media (max-width: 480px) {
  .cart__recipient-fields {
    grid-template-columns: 1fr;
  }
}

.cart__recipient-field--wide {
  grid-column: 1 / -1;
}

.cart__recipient-error {
  margin-top: var(--space-2);
  font-size: var(--font-size-caption);
  color: var(--color-error);
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
  padding: 12px 16px calc(12px + var(--bottom-nav-height, 56px) + env(safe-area-inset-bottom, 0px));
  background: var(--color-bg-white);
  border-top: 1px solid var(--color-border);
  z-index: 50;
}

@media (min-width: 768px) {
  .cart__checkout-bar {
    position: static;
    transform: none;
    margin-top: 20px;
    padding: var(--space-4);
    border-radius: var(--radius-lg);
    border: none;
    box-shadow: var(--shadow-card);
  }
}

.cart__checkout-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.cart__checkout-label {
  font-size: var(--font-size-caption);
  color: var(--color-text-secondary);
}

.cart__checkout-price {
  font-size: var(--font-size-h3);
  font-weight: var(--font-weight-bold);
  color: var(--color-text);
}

.cart__checkout-btn {
  flex: 1;
  max-width: 220px;
}

@media (min-width: 768px) {
  .cart__checkout-btn {
    max-width: 240px;
  }
}
</style>
