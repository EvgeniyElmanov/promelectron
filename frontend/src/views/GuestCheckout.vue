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

    <!-- Login hint -->
    <div class="guest-checkout__login-hint">
      <span>Уже есть аккаунт?</span>
      <router-link
        to="/login?redirect=/cart"
        class="guest-checkout__login-link"
        data-testid="guest-login-link"
      >
        Войти
      </router-link>
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
      <CdekDeliveryWidget
        v-model="selectedDelivery"
        :items="items"
        :supplier-city-code="supplierCityCode"
        :is-fallback="isFallback"
      />
    </div>

    <!-- Contact -->
    <div v-if="items.length > 0" class="guest-checkout__card">
      <div class="guest-checkout__section-title">Контактные данные</div>
      <div class="field">
        <label class="field__label">Email <span class="field__required">*</span></label>
        <input
          v-model="guestEmail"
          class="field__input"
          :class="{ 'field__input--error': validationErrors.email }"
          type="email"
          placeholder="your@email.com"
          data-testid="guest-email"
        />
        <span v-if="validationErrors.email" class="field__error" data-testid="guest-email-error">{{ validationErrors.email }}</span>
      </div>
      <div class="field">
        <label class="field__label">Имя <span class="field__required">*</span></label>
        <input
          v-model="guestFirstName"
          class="field__input"
          :class="{ 'field__input--error': validationErrors.firstName }"
          placeholder="Иван"
          data-testid="guest-first-name"
        />
        <span v-if="validationErrors.firstName" class="field__error" data-testid="guest-first-name-error">{{ validationErrors.firstName }}</span>
      </div>
      <div class="field">
        <label class="field__label">Фамилия <span class="field__required">*</span></label>
        <input
          v-model="guestLastName"
          class="field__input"
          :class="{ 'field__input--error': validationErrors.lastName }"
          placeholder="Иванов"
          data-testid="guest-last-name"
        />
        <span v-if="validationErrors.lastName" class="field__error" data-testid="guest-last-name-error">{{ validationErrors.lastName }}</span>
      </div>
      <div class="field">
        <label class="field__label">Страна <span class="field__required">*</span></label>
        <select
          v-model="guestCountryCode"
          class="field__input"
          data-testid="guest-country-code"
        >
          <option value="RU">Россия</option>
          <option value="KZ">Казахстан</option>
          <option value="BY">Беларусь</option>
        </select>
      </div>
      <div v-if="guestCountryCode === 'RU'" class="field">
        <label class="field__label">Отчество</label>
        <input
          v-model="guestPatronymic"
          class="field__input"
          :class="{ 'field__input--error': validationErrors.patronymic }"
          placeholder="Иванович"
          data-testid="guest-patronymic"
        />
        <span v-if="validationErrors.patronymic" class="field__error" data-testid="guest-patronymic-error">{{ validationErrors.patronymic }}</span>
      </div>
      <div class="field">
        <label class="field__label">Телефон <span class="field__required">*</span></label>
        <input
          v-model="guestPhone"
          class="field__input"
          :class="{ 'field__input--error': validationErrors.phone }"
          type="tel"
          placeholder="+7 (999) 000-00-00"
          data-testid="guest-phone"
        />
        <span v-if="validationErrors.phone" class="field__error" data-testid="guest-phone-error">{{ validationErrors.phone }}</span>
      </div>

      <!-- Save address -->
      <label class="guest-checkout__save-address" data-testid="guest-save-address-label">
        <input
          v-model="saveAddress"
          type="checkbox"
          data-testid="guest-save-address"
        />
        <span>Сохранить адрес для следующих заказов</span>
      </label>
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
      {{ submitting ? 'Оформление...' : 'Оплатить заказ' }}
    </button>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useCart } from '@/composables/useCart';
import { useToast } from '@/composables/useToast';
import { useGuestCheckout } from '@/composables/useGuestCheckout';
import { getSupplierCityCode } from '@/api/cdek';
import { formatPrice } from '@/utils/price';
import CdekDeliveryWidget from '@/components/CdekDeliveryWidget.vue';

const GUEST_EMAIL_KEY = 'guest_checkout_email';

const router = useRouter();
const { add: toast } = useToast();
const { getGuestCartItems, clearGuestCart } = useCart();
const { submitting, submitGuestCheckout, validateGuestForm } = useGuestCheckout();

const items = ref([]);
const selectedDelivery = ref(null);
const supplierCityCode = ref(44);
const isFallback = ref(false);
const guestEmail = ref('');
const guestFirstName = ref('');
const guestLastName = ref('');
const guestPatronymic = ref('');
const guestPhone = ref('');
const guestCountryCode = ref('RU');
const saveAddress = ref(false);
const validationErrors = ref({});

const supplierId = computed(() => items.value[0]?.supplier_id ?? null);

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

const itemsTotal = computed(() => {
  return items.value.reduce((sum, item) => sum + (item.price || 0) * (item.quantity || 0), 0);
});

const deliveryPrice = computed(() => {
  return selectedDelivery.value ? Number(selectedDelivery.value.price) : 0;
});

const orderTotal = computed(() => itemsTotal.value + deliveryPrice.value);

const isDeliveryValid = computed(() => {
  return selectedDelivery.value && selectedDelivery.value.tariff_code;
});

const canSubmit = computed(() => {
  const errors = validateGuestForm({
    email: guestEmail.value,
    firstName: guestFirstName.value,
    lastName: guestLastName.value,
    patronymic: guestPatronymic.value,
    phone: guestPhone.value,
    countryCode: guestCountryCode.value,
  });
  return Object.keys(errors).length === 0 && isDeliveryValid.value;
});

const loadItems = () => {
  items.value = getGuestCartItems();
};

watch(supplierId, () => {
  loadSupplierCityCode();
}, { immediate: true });

const submitOrder = async () => {
  if (submitting.value) return;
  validationErrors.value = {};

  if (items.value.length === 0) {
    toast('Корзина пуста', 'error');
    return;
  }

  try {
    const { order } = await submitGuestCheckout({
      items: items.value,
      selectedDelivery: selectedDelivery.value,
      email: guestEmail.value,
      firstName: guestFirstName.value,
      lastName: guestLastName.value,
      patronymic: guestPatronymic.value,
      phone: guestPhone.value,
      countryCode: guestCountryCode.value,
      saveAddress: saveAddress.value,
    });

    const email = order.guest_email || guestEmail.value.trim();
    sessionStorage.setItem(GUEST_EMAIL_KEY, email);
    clearGuestCart();
    toast('Заказ создан. Переходим к оплате...', 'success');

    await router.push(`/checkout/${order.id}`);
  } catch (err) {
    if (err.field && err.message) {
      validationErrors.value = { [err.field]: err.message };
      toast(err.message, 'error');
    } else {
      const detail = err.response?.data?.detail;
      toast(detail || err.message || 'Не удалось создать заказ', 'error');
    }
  }
};

onMounted(() => {
  router.replace('/login?redirect=/cart');
  loadItems();
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
  margin-bottom: 12px;
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

.guest-checkout__login-hint {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  background: var(--color-bg-white);
  border-radius: 12px;
  padding: 12px 16px;
  margin-bottom: 12px;
  font-size: 14px;
  color: var(--color-text);
}

.guest-checkout__login-link {
  color: var(--color-primary);
  font-weight: 600;
  text-decoration: none;
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

.field__input--error {
  border-color: var(--color-danger);
}

.field__error {
  font-size: 12px;
  color: var(--color-danger);
}

.guest-checkout__save-address {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
  font-size: 14px;
  color: var(--color-text);
  cursor: pointer;
}

.guest-checkout__save-address input {
  width: 18px;
  height: 18px;
  accent-color: var(--color-primary);
  flex-shrink: 0;
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
