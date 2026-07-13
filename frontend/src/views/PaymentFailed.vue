<template>
  <div class="payment-result" data-testid="payment-failed-page">
    <div class="payment-result__icon payment-result__icon--failed">
      <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <path d="M15 9l-6 6M9 9l6 6"/>
      </svg>
    </div>

    <h1 class="payment-result__title">{{ title }}</h1>
    <p class="payment-result__subtitle">
      {{ subtitle }}
    </p>

    <div v-if="loading" class="payment-result__loading">
      <div class="payment-result__spinner"></div>
      <p>Загрузка данных заказа...</p>
    </div>

    <div v-else-if="error" class="payment-result__error">
      <p class="payment-result__error-text">{{ error }}</p>
      <button class="payment-result__btn payment-result__btn--primary" @click="fetchOrder">
        Повторить
      </button>
    </div>

    <div v-else-if="order" class="payment-result__details">
      <div class="payment-result__row">
        <span>Заказ</span>
        <span>№{{ orderId }}</span>
      </div>
      <div class="payment-result__row">
        <span>Сумма</span>
        <span class="payment-result__amount">{{ formatPrice(order.total_price) }} ₽</span>
      </div>
      <div class="payment-result__row">
        <span>Статус</span>
        <span class="payment-result__badge payment-result__badge--error">{{ displayStatus }}</span>
      </div>
      <div v-if="cancellationReason" class="payment-result__row" data-testid="cancellation-reason">
        <span>Причина</span>
        <span class="payment-result__reason">{{ cancellationReason }}</span>
      </div>
      <div v-if="order.items?.length" class="payment-result__items">
        <div
          v-for="item in order.items"
          :key="item.id"
          class="payment-result__item"
        >
          <span class="payment-result__item-name">{{ item.product?.name || 'Товар' }}</span>
          <span class="payment-result__item-qty">×{{ item.quantity }}</span>
        </div>
      </div>
    </div>

    <div class="payment-result__actions">
      <button
        v-if="orderId && !loading"
        class="payment-result__btn payment-result__btn--primary"
        @click="retryPayment"
      >
        Попробовать ещё раз
      </button>
      <router-link v-if="isAuthenticated" to="/orders" class="payment-result__btn payment-result__btn--secondary">
        Мои заказы
      </router-link>
      <router-link to="/" class="payment-result__btn payment-result__btn--ghost">
        В каталог
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuth } from '@/composables/useAuth';
import { getOrder, getGuestOrder } from '@/api/orders';
import { formatPrice } from '@/utils/price';

const route = useRoute();
const router = useRouter();
const { isAuthenticated } = useAuth();
const orderId = ref(route.query.order_id || route.params.id);
const guestEmail = ref(sessionStorage.getItem('guest_checkout_email') || '');
const isGuest = computed(() => !isAuthenticated.value && Boolean(guestEmail.value));
const order = ref(null);
const loading = ref(true);
const error = ref(null);

const title = computed(() => {
  if (error.value) return 'Ошибка';
  return 'Оплата не прошла';
});

const subtitle = computed(() => {
  if (error.value) return '';
  if (!orderId.value) return 'Заказ не найден. Пожалуйста, проверьте историю заказов.';
  return `Что-то пошло не так при оплате заказа №${orderId.value}. Вы можете попробовать снова или выбрать другой способ оплаты.`;
});

const cancellationReasonMap = {
  insufficient_funds: 'Недостаточно средств на карте',
  invalid_csc: 'Неверный код безопасности карты',
  card_expired: 'Истёк срок действия карты',
  fraud_suspected: 'Платёж отклонён по соображениям безопасности',
  general_decline: 'Платёж отклонён банком',
};

const displayStatus = computed(() => {
  if (!order.value) return '';
  const map = {
    pending: 'Ожидает оплаты',
    awaiting_payment: 'Ожидает оплаты',
    cancelled: 'Отменён',
    canceled: 'Отменён',
  };
  return map[order.value.status] || order.value.status;
});

const cancellationReason = computed(() => {
  const reason = order.value?.cancellation_reason;
  if (!reason) return '';
  return cancellationReasonMap[reason] || reason;
});

const fetchOrder = async () => {
  if (!orderId.value) {
    loading.value = false;
    error.value = 'Заказ не найден';
    return;
  }
  error.value = null;
  loading.value = true;
  try {
    const { data } = isGuest.value
      ? await getGuestOrder(orderId.value, guestEmail.value)
      : await getOrder(orderId.value);
    order.value = data;
  } catch (err) {
    if (err.response?.status === 404) {
      error.value = 'Заказ не найден или был удалён';
    } else {
      error.value = 'Не удалось загрузить заказ';
    }
  } finally {
    loading.value = false;
  }
};

const retryPayment = () => {
  const target = `/checkout/${orderId.value}`;
  router.push(target);
};

onMounted(() => {
  fetchOrder();
});
</script>

<style scoped>
.payment-result {
  max-width: 480px;
  margin: 0 auto;
  padding: 40px 16px calc(24px + var(--bottom-nav-height, 56px));
  min-height: 100vh;
  background: var(--color-bg);
  text-align: center;
}

.payment-result__icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
}

.payment-result__icon--failed {
  background: #fce8e8;
  color: #c5221f;
}

.payment-result__title {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 8px;
}

.payment-result__subtitle {
  font-size: 15px;
  color: var(--color-text-secondary);
  margin-bottom: 24px;
  line-height: 1.4;
}

.payment-result__loading {
  padding: 20px;
}

.payment-result__spinner {
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

.payment-result__details {
  background: var(--color-bg-white);
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 24px;
  text-align: left;
}

.payment-result__row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  font-size: 15px;
  color: var(--color-text);
  border-bottom: 1px solid var(--color-border);
}

.payment-result__row:last-child {
  border-bottom: none;
}

.payment-result__amount {
  font-weight: 700;
  font-size: 16px;
}

.payment-result__badge {
  padding: 4px 10px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
}

.payment-result__badge--error {
  background: #fce8e6;
  color: #c5221f;
}

.payment-result__items {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--color-border);
}

.payment-result__item {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  color: var(--color-text-secondary);
  padding: 4px 0;
}

.payment-result__item-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.payment-result__item-qty {
  margin-left: 8px;
  flex-shrink: 0;
}

.payment-result__error {
  text-align: center;
  padding: 20px;
  color: var(--color-danger);
  margin-bottom: 24px;
}

.payment-result__error-text {
  margin-bottom: 16px;
  font-size: 15px;
}

.payment-result__actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.payment-result__btn {
  display: block;
  width: 100%;
  padding: 14px;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  text-align: center;
  text-decoration: none;
  border: none;
  cursor: pointer;
}

.payment-result__btn--primary {
  background: var(--color-primary);
  color: #fff;
}

.payment-result__btn--secondary {
  background: var(--color-bg-white);
  color: var(--color-text);
  border: 1px solid var(--color-border);
}

.payment-result__btn--ghost {
  background: transparent;
  color: var(--color-text-secondary);
}
</style>
