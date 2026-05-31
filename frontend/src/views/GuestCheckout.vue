<template>
  <div class="guest-checkout" data-testid="guest-checkout-page">
    <div class="guest-checkout__header">
      <button class="guest-checkout__back" @click="router.back()">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 12H5M12 19l-7-7 7-7"/>
        </svg>
      </button>
      <h1 class="guest-checkout__title">Оформление заказа</h1>
    </div>

    <!-- Items -->
    <div class="guest-checkout__card">
      <div class="guest-checkout__section-title">Товары</div>
      <div v-if="items.length === 0" class="guest-checkout__empty">
        Корзина пуста. <router-link to="/">В каталог</router-link>
      </div>
      <div v-else class="guest-checkout__items">
        <div v-for="item in items" :key="item.product_id" class="guest-checkout__item">
          <span class="guest-checkout__item-name">{{ item.name }}</span>
          <span class="guest-checkout__item-qty">× {{ item.quantity }}</span>
          <span class="guest-checkout__item-price">{{ formatPrice(item.price * item.quantity) }} ₽</span>
        </div>
      </div>
      <div v-if="items.length > 0" class="guest-checkout__items-total">
        <span>Товары</span>
        <span>{{ formatPrice(itemsTotal) }} ₽</span>
      </div>
    </div>

    <!-- Delivery -->
    <div v-if="items.length > 0" class="guest-checkout__card">
      <div class="guest-checkout__section-title">Способ доставки</div>
      <div class="guest-checkout__delivery-list">
        <label
          v-for="method in deliveryMethods"
          :key="method.id"
          class="guest-checkout__delivery-option"
          :class="{ 'guest-checkout__delivery-option--active': selectedDeliveryMethodId === method.id }"
        >
          <input
            v-model="selectedDeliveryMethodId"
            type="radio"
            :value="method.id"
            class="guest-checkout__delivery-radio"
          />
          <div class="guest-checkout__delivery-info">
            <span class="guest-checkout__delivery-name">{{ method.name }}</span>
            <span v-if="method.estimated_days" class="guest-checkout__delivery-days">
              {{ method.estimated_days }} {{ method.estimated_days === 1 ? 'день' : method.estimated_days < 5 ? 'дня' : 'дней' }}
            </span>
          </div>
          <span class="guest-checkout__delivery-price">
            {{ Number(method.base_price) > 0 ? formatPrice(method.base_price) + ' ₽' : 'Бесплатно' }}
          </span>
        </label>
      </div>
    </div>

    <!-- Contact -->
    <div v-if="items.length > 0" class="guest-checkout__card">
      <div class="guest-checkout__section-title">Контактные данные</div>
      <div class="field">
        <label class="field__label">Email <span class="field__required">*</span></label>
        <input
          v-model="guestEmail"
          class="field__input"
          type="email"
          placeholder="your@email.com"
          data-testid="guest-email"
        />
      </div>
      <div class="field">
        <label class="field__label">Имя</label>
        <input
          v-model="guestName"
          class="field__input"
          placeholder="Иван Иванов"
          data-testid="guest-name"
        />
      </div>
      <div class="field">
        <label class="field__label">Телефон</label>
        <input
          v-model="guestPhone"
          class="field__input"
          type="tel"
          placeholder="+7 (999) 000-00-00"
          data-testid="guest-phone"
        />
      </div>
    </div>

    <!-- Address -->
    <div v-if="items.length > 0" class="guest-checkout__card">
      <AddressForm
        v-model="shippingAddress"
        label="Адрес доставки"
        testid-prefix="guest-"
      />
    </div>

    <!-- Total -->
    <div v-if="items.length > 0" class="guest-checkout__total">
      <span>Итого</span>
      <span>{{ formatPrice(orderTotal) }} ₽</span>
    </div>

    <!-- Submit -->
    <button
      v-if="items.length > 0"
      class="guest-checkout__submit"
      data-testid="guest-checkout-submit"
      :disabled="!canSubmit || submitting"
      @click="submitOrder"
    >
      {{ submitting ? 'Оформление...' : 'Оформить заказ' }}
    </button>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/services/api';
import { useCart } from '@/composables/useCart';
import { useToast } from '@/composables/useToast';
import AddressForm from '@/components/AddressForm.vue';

const router = useRouter();
const { add: toast } = useToast();
const { getGuestCartItems, clearGuestCart } = useCart();

const items = ref([]);
const deliveryMethods = ref([]);
const selectedDeliveryMethodId = ref(null);
const guestEmail = ref('');
const guestName = ref('');
const guestPhone = ref('');
const shippingAddress = ref({
  region: '', district: '', city: '', street: '', house: '', apartment: ''
});
const submitting = ref(false);

const itemsTotal = computed(() => {
  return items.value.reduce((sum, item) => sum + (item.price || 0) * (item.quantity || 0), 0);
});

const deliveryPrice = computed(() => {
  const method = deliveryMethods.value.find(m => m.id === selectedDeliveryMethodId.value);
  return method ? Number(method.base_price) : 0;
});

const orderTotal = computed(() => itemsTotal.value + deliveryPrice.value);

const isAddressValid = computed(() => {
  return shippingAddress.value.city?.trim()
    && shippingAddress.value.street?.trim()
    && shippingAddress.value.house?.trim();
});

const canSubmit = computed(() => {
  return guestEmail.value.trim().length > 0 && isAddressValid.value;
});

const formatPrice = (price) => {
  return Number(price).toLocaleString('ru-RU');
};

const loadItems = () => {
  items.value = getGuestCartItems();
};

const fetchDeliveryMethods = async () => {
  try {
    const { data } = await api.get('/delivery-methods/');
    deliveryMethods.value = data;
    if (data.length > 0 && !selectedDeliveryMethodId.value) {
      selectedDeliveryMethodId.value = data[0].id;
    }
  } catch (err) {
    console.error('Failed to fetch delivery methods:', err);
  }
};

const submitOrder = async () => {
  if (submitting.value) return;
  if (!guestEmail.value.trim()) {
    toast('Укажите email', 'error');
    return;
  }
  if (!isAddressValid.value) {
    toast('Заполните город, улицу и дом', 'error');
    return;
  }
  if (items.value.length === 0) {
    toast('Корзина пуста', 'error');
    return;
  }

  submitting.value = true;
  try {
    const payload = {
      items: items.value.map(i => ({ product_id: i.product_id, quantity: i.quantity })),
      shipping_address: { ...shippingAddress.value },
      delivery_method_id: selectedDeliveryMethodId.value,
      guest_email: guestEmail.value.trim(),
      guest_name: guestName.value.trim() || null,
      guest_phone: guestPhone.value.trim() || null,
    };
    const { data: order } = await api.post('/orders/create-guest', payload);
    clearGuestCart();
    toast('Заказ успешно создан!', 'success');
    await router.push(`/guest-order-success/${order.id}?email=${encodeURIComponent(order.guest_email)}`);
  } catch (err) {
    console.error('Failed to create guest order:', err);
    const detail = err.response?.data?.detail;
    toast(detail || 'Не удалось создать заказ', 'error');
  } finally {
    submitting.value = false;
  }
};

onMounted(() => {
  loadItems();
  fetchDeliveryMethods();
});
</script>

<style scoped>
.guest-checkout {
  max-width: 600px;
  margin: 0 auto;
  padding: 16px 16px calc(24px + var(--bottom-nav-height, 56px));
  min-height: 100vh;
  background: var(--color-bg);
}

.guest-checkout__header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.guest-checkout__back {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: none;
  background: var(--color-bg-white);
  color: var(--color-text);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.guest-checkout__title {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text);
}

.guest-checkout__card {
  background: var(--color-bg-white);
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 12px;
}

.guest-checkout__section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  margin-bottom: 12px;
}

.guest-checkout__empty {
  font-size: 14px;
  color: var(--color-text-secondary);
}

.guest-checkout__empty a {
  color: var(--color-primary);
  text-decoration: underline;
}

.guest-checkout__items {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.guest-checkout__item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--color-text);
}

.guest-checkout__item-name {
  flex: 1;
  min-width: 0;
  word-break: break-word;
}

.guest-checkout__item-qty {
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.guest-checkout__item-price {
  font-weight: 600;
  white-space: nowrap;
}

.guest-checkout__items-total {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border);
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
}

.guest-checkout__delivery-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.guest-checkout__delivery-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-radius: 10px;
  border: 2px solid var(--color-border);
  cursor: pointer;
  transition: border-color 0.2s;
}

.guest-checkout__delivery-option--active {
  border-color: var(--color-primary);
}

.guest-checkout__delivery-radio {
  width: 18px;
  height: 18px;
  accent-color: var(--color-primary);
  flex-shrink: 0;
}

.guest-checkout__delivery-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.guest-checkout__delivery-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
}

.guest-checkout__delivery-days {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.guest-checkout__delivery-price {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  white-space: nowrap;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 12px;
}

.field:last-child {
  margin-bottom: 0;
}

.field__label {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text);
}

.field__required {
  color: var(--color-danger);
}

.field__input {
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-white);
  font-size: 16px;
  color: var(--color-text);
  width: 100%;
}

.field__input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.guest-checkout__total {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: var(--color-bg-white);
  border-radius: 16px;
  margin-bottom: 12px;
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text);
}

.guest-checkout__submit {
  width: 100%;
  padding: 16px;
  border-radius: 14px;
  background: var(--color-primary);
  color: #fff;
  font-size: 17px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  margin-bottom: 16px;
}

.guest-checkout__submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
