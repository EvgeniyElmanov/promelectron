<template>
  <div class="checkout" data-testid="checkout-page">
    <div class="checkout__header">
      <button class="checkout__back" @click="router.back()">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 12H5M12 19l-7-7 7-7"/>
        </svg>
      </button>
      <h1 class="checkout__title">Оплата заказа №{{ orderId }}</h1>
    </div>

    <div v-if="loading" class="checkout__loading">Загрузка...</div>

    <div v-else-if="error" class="checkout__error">
      <p>{{ error }}</p>
      <button class="checkout__retry" @click="fetchOrder">Повторить</button>
    </div>

    <template v-else-if="order">
      <!-- Order Summary -->
      <div class="checkout__card">
        <div class="checkout__section-title">Сумма к оплате</div>
        <div class="checkout__amount">{{ formatPrice(order.total_price) }} ₽</div>
        <div class="checkout__items-count">{{ order.items?.length || 0 }} товаров</div>
        <div v-if="order.delivery_method" class="checkout__delivery-info">
          <div class="checkout__delivery-row">
            <span>Доставка: {{ order.delivery_method.name }}</span>
            <span>{{ Number(order.delivery_method.base_price) > 0 ? formatPrice(order.delivery_method.base_price) + ' ₽' : 'Бесплатно' }}</span>
          </div>
          <div v-if="order.delivery_method.estimated_days" class="checkout__delivery-days">
            Срок: {{ order.delivery_method.estimated_days }} {{ order.delivery_method.estimated_days === 1 ? 'день' : order.delivery_method.estimated_days < 5 ? 'дня' : 'дней' }}
          </div>
        </div>
      </div>

      <!-- Payment Form -->
      <div class="checkout__card">
        <div class="checkout__section-title">Данные карты</div>

        <div class="field">
          <label class="field__label">Номер карты</label>
          <input
            v-model="cardNumber"
            class="field__input"
            placeholder="0000 0000 0000 0000"
            maxlength="19"
            inputmode="numeric"
            data-testid="card-number"
            @input="formatCardNumber"
          />
        </div>

        <div class="checkout__row">
          <div class="field">
            <label class="field__label">Срок действия</label>
            <input
              v-model="cardExpiry"
              class="field__input"
              placeholder="MM/YY"
              maxlength="5"
              inputmode="numeric"
              data-testid="card-expiry"
              @input="formatExpiry"
            />
          </div>
          <div class="field">
            <label class="field__label">CVV</label>
            <input
              v-model="cardCvv"
              class="field__input"
              placeholder="123"
              maxlength="3"
              inputmode="numeric"
              data-testid="card-cvv"
              @input="formatCvv"
            />
          </div>
        </div>

        <div class="field">
          <label class="field__label">Имя держателя</label>
          <input
            v-model="cardHolder"
            class="field__input"
            placeholder="IVAN IVANOV"
            data-testid="card-holder"
          />
        </div>
      </div>

      <!-- Security Note -->
      <div class="checkout__security">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
          <path d="M7 11V7a5 5 0 0110 0v4"/>
        </svg>
        <span>Тестовый платёж. Данные карты не сохраняются.</span>
      </div>

      <!-- Pay Button -->
      <button
        class="checkout__pay-btn"
        :disabled="!isFormValid || processing"
        data-testid="pay-button"
        @click="processPayment"
      >
        <span v-if="processing">Обработка...</span>
        <span v-else>Оплатить {{ formatPrice(order.total_price) }} ₽</span>
      </button>

      <!-- Cancel -->
      <button class="checkout__cancel" @click="cancelPayment" :disabled="processing">
        Отменить
      </button>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import api from '@/services/api';
import { useToast } from '@/composables/useToast';
import { useCart } from '@/composables/useCart';

const route = useRoute();
const router = useRouter();
const { add: toast } = useToast();
const { syncCartCount } = useCart();

const orderId = computed(() => route.params.id);

const order = ref(null);
const loading = ref(true);
const error = ref(null);
const processing = ref(false);

const cardNumber = ref('');
const cardExpiry = ref('');
const cardCvv = ref('');
const cardHolder = ref('');

const isFormValid = computed(() => {
  return (
    cardNumber.value.replace(/\s/g, '').length === 16 &&
    cardExpiry.value.length === 5 &&
    cardCvv.value.length >= 3 &&
    cardHolder.value.trim().length >= 3
  );
});

function formatPrice(value) {
  return Number(value).toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

function formatCardNumber(e) {
  let v = e.target.value.replace(/\D/g, '');
  v = v.substring(0, 16);
  const parts = [];
  for (let i = 0; i < v.length; i += 4) {
    parts.push(v.substring(i, i + 4));
  }
  cardNumber.value = parts.join(' ');
}

function formatExpiry(e) {
  let v = e.target.value.replace(/\D/g, '').substring(0, 4);
  if (v.length >= 2) {
    v = v.substring(0, 2) + '/' + v.substring(2);
  }
  cardExpiry.value = v;
}

function formatCvv(e) {
  cardCvv.value = e.target.value.replace(/\D/g, '').substring(0, 3);
}

const fetchOrder = async () => {
  loading.value = true;
  error.value = null;
  try {
    const { data } = await api.get(`/orders/${orderId.value}`);
    order.value = data;
    if (data.status !== 'pending') {
      await router.replace(`/orders/${orderId.value}`);
      return;
    }
  } catch (err) {
    error.value = err.response?.data?.detail || 'Не удалось загрузить заказ';
  } finally {
    loading.value = false;
  }
};

const processPayment = async () => {
  if (!isFormValid.value || processing.value) return;
  processing.value = true;

  try {
    // Step 1: Create payment
    const { data: paymentData } = await api.post(`/payments/${orderId.value}`);
    const paymentId = paymentData.payment_id;

    // Simulate processing delay for UX
    await new Promise((resolve) => setTimeout(resolve, 1200));

    // Step 2: Confirm payment (mock gateway callback)
    await api.post(`/payments/${paymentId}/confirm`);

    toast('Оплата прошла успешно!', 'success');
    await syncCartCount();
    await new Promise((resolve) => setTimeout(resolve, 600));
    await router.push(`/orders/${orderId.value}`);
  } catch (err) {
    const detail = err.response?.data?.detail;
    toast(detail || 'Ошибка при оплате', 'error');
  } finally {
    processing.value = false;
  }
};

const cancelPayment = () => {
  if (confirm('Отменить оплату? Заказ останется в ожидании.')) {
    router.push(`/orders/${orderId.value}`);
  }
};

onMounted(fetchOrder);
</script>

<style scoped>
.checkout {
  max-width: 480px;
  margin: 0 auto;
  padding: 16px 16px calc(24px + var(--bottom-nav-height, 56px));
  min-height: 100vh;
  background: var(--color-bg);
}

.checkout__header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.checkout__back {
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

.checkout__title {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text);
}

.checkout__card {
  background: var(--color-bg-white);
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 12px;
}

.checkout__section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  margin-bottom: 10px;
}

.checkout__amount {
  font-size: 28px;
  font-weight: 700;
  color: var(--color-text);
  line-height: 1.2;
}

.checkout__items-count {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin-top: 4px;
}

.checkout__row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 12px;
}

.field__label {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text);
}

.field__input {
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-white);
  font-size: 16px;
  color: var(--color-text);
  width: 100%;
  font-family: monospace;
  letter-spacing: 1px;
}

.field__input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.checkout__security {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border-radius: 10px;
  background: #e8f0fe;
  color: #1a73e8;
  font-size: 13px;
  margin-bottom: 16px;
}

.checkout__pay-btn {
  width: 100%;
  padding: 16px;
  border-radius: 14px;
  background: var(--color-primary);
  color: #fff;
  font-size: 17px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  margin-bottom: 10px;
}

.checkout__pay-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.checkout__cancel {
  width: 100%;
  padding: 14px;
  border-radius: 14px;
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 15px;
  font-weight: 500;
  border: none;
  cursor: pointer;
}

.checkout__loading,
.checkout__error {
  text-align: center;
  padding: 40px 20px;
  color: var(--color-text-secondary);
}

.checkout__error {
  color: var(--color-danger);
}

.checkout__retry {
  margin-top: 12px;
  padding: 10px 20px;
  border-radius: 10px;
  background: var(--color-primary);
  color: #fff;
  border: none;
  font-size: 15px;
  cursor: pointer;
}

.checkout__delivery-info {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border);
}

.checkout__delivery-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  color: var(--color-text);
}

.checkout__delivery-days {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-top: 4px;
}
</style>
