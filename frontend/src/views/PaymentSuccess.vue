<template>
  <div class="payment-result" data-testid="payment-success-page">
    <div class="payment-result__icon payment-result__icon--success">
      <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <path d="M9 12l2 2 4-4"/>
      </svg>
    </div>

    <h1 class="payment-result__title">{{ title }}</h1>
    <p class="payment-result__subtitle">
      {{ subtitle }}
    </p>

    <div v-if="error" class="payment-result__error" data-testid="payment-error">
      <p class="payment-result__error-text">{{ error }}</p>
      <AppButton @click="fetchOrder">
        Повторить
      </AppButton>
    </div>

    <div v-else-if="loading || polling || syncing" class="payment-result__loading">
      <div class="payment-result__spinner"></div>
      <p>Проверяем статус заказа...</p>
      <p v-if="pollCount > 0" class="payment-result__poll-info">
        Попытка {{ pollCount }} из {{ maxPolls }}
      </p>
      <p v-if="syncing">Проверяем статус в ЮKassa...</p>
    </div>

    <div v-else-if="order" class="payment-result__details">
      <div class="payment-result__row">
        <span>Статус</span>
        <span
          class="payment-result__badge"
          :class="badgeClass"
        >
          {{ displayStatus }}
        </span>
      </div>
      <div class="payment-result__row">
        <span>Сумма</span>
        <span class="payment-result__amount">{{ formatPrice(order.total_price) }} ₽</span>
      </div>
    </div>

    <div v-if="!loading && !polling && !syncing && order && order.status !== 'paid'" class="payment-result__notice">
      <p>
        Если вы уже оплатили заказ, нажмите кнопку ниже для проверки статуса.
      </p>
      <AppButton
        block
        :disabled="syncing"
        @click="checkPaymentStatus"
      >
        <span v-if="syncing">Проверка...</span>
        <span v-else>Проверить статус оплаты</span>
      </AppButton>
    </div>

    <div class="payment-result__actions">
      <router-link v-if="isAuthenticated" to="/orders" class="payment-result__btn payment-result__btn--primary">
        Мои заказы
      </router-link>
      <router-link to="/catalog" class="payment-result__btn payment-result__btn--secondary">
        В каталог
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuth } from '@/composables/useAuth';
import { getOrder, getGuestOrder } from '@/api/orders';
import { syncPaymentStatusByOrder, confirmMockPayment as confirmMockPaymentApi, confirmGuestMockPayment } from '@/api/payments';
import { formatPrice } from '@/utils/price';
import AppButton from '@/components/ui/AppButton.vue';

const route = useRoute();
const router = useRouter();
const { isAuthenticated } = useAuth();
const orderId = ref(route.query.order_id || route.params.id);
const guestEmail = ref(sessionStorage.getItem('guest_checkout_email') || '');
const isGuest = computed(() => !isAuthenticated.value && Boolean(guestEmail.value));
const order = ref(null);
const loading = ref(true);
const error = ref(null);
const polling = ref(false);
const syncing = ref(false);
const pollCount = ref(0);
const maxPolls = 60;
const pollInterval = 2000; // 2 seconds
const consecutiveErrorCount = ref(0);
const maxConsecutiveErrors = 3;
let pollTimer = null;

const isOrderFailed = (order) => {
  return order && (order.status === 'cancelled' || order.status === 'canceled' || Boolean(order.cancellation_reason));
};

const displayStatus = computed(() => {
  if (!order.value) return '';
  const map = {
    paid: 'Оплачен',
    pending: 'Ожидает оплаты',
    awaiting_payment: 'Ожидает оплаты',
    cancelled: 'Отменён',
    canceled: 'Отменён',
  };
  if (isOrderFailed(order.value)) {
    return 'Отменён';
  }
  return map[order.value.status] || order.value.status;
});

const badgeClass = computed(() => {
  if (!order.value) return '';
  if (isOrderFailed(order.value)) {
    return 'payment-result__badge--error';
  }
  const classes = {
    paid: 'payment-result__badge--success',
    pending: 'payment-result__badge--warning',
    awaiting_payment: 'payment-result__badge--warning',
    cancelled: 'payment-result__badge--error',
    canceled: 'payment-result__badge--error',
  };
  return classes[order.value.status] || '';
});

const title = computed(() => {
  if (error.value) return 'Ошибка';
  if (!order.value) return 'Обработка платежа...';
  if (order.value.status === 'paid') return 'Оплата прошла успешно!';
  if (isOrderFailed(order.value)) return 'Платёж отменён';
  return 'Платёж в обработке';
});

const subtitle = computed(() => {
  if (error.value) return '';
  if (!order.value) return 'Пожалуйста, подождите...';
  if (order.value.status === 'paid') {
    return `Заказ №${orderId.value} оплачен. Мы отправили подтверждение на ваш email.`;
  }
  if (isOrderFailed(order.value)) {
    return `Заказ №${orderId.value} был отменён.`;
  }
  return `Заказ №${orderId.value} ожидает подтверждения оплаты.`;
});

const fetchOrder = async () => {
  if (!orderId.value) {
    loading.value = false;
    error.value = 'Заказ не найден';
    return;
  }
  error.value = null;
  consecutiveErrorCount.value = 0;
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

const startPolling = () => {
  if (pollTimer) return;
  polling.value = true;
  pollCount.value = 0;
  consecutiveErrorCount.value = 0;

  pollTimer = setInterval(async () => {
    pollCount.value += 1;
    try {
      if (!isGuest.value) {
        // Force sync with YooKassa API, then refresh order
        await syncPaymentStatusByOrder(orderId.value);
      }
      await fetchOrder();
      consecutiveErrorCount.value = 0;

      if (order.value && (order.value.status === 'paid' || isOrderFailed(order.value))) {
        stopPolling();
      }
    } catch {
      consecutiveErrorCount.value += 1;
      if (consecutiveErrorCount.value >= maxConsecutiveErrors) {
        error.value = 'Не удалось проверить статус заказа. Пожалуйста, обновите страницу или свяжитесь с поддержкой.';
        stopPolling();
      }
    }

    if (pollCount.value >= maxPolls) {
      stopPolling();
      // Fallback: if the order is still not terminal after max polling,
      // redirect to the failed page so the user sees a meaningful result.
      if (order.value && order.value.status !== 'paid' && !isOrderFailed(order.value)) {
        router.replace(`/payment/failed?order_id=${orderId.value}`);
      }
    }
  }, pollInterval);
};

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
  polling.value = false;
};

onMounted(async () => {
  // Auto-confirm mock payments in dev mode
  if (route.query.mock === '1' && orderId.value) {
    await confirmMockPayment();
  }
  await fetchOrder();

  // If order is still pending, force sync with YooKassa immediately
  if (order.value && order.value.status !== 'paid' && !isOrderFailed(order.value)) {
    await checkPaymentStatus();

    // Start polling only if still pending after forced sync
    if (order.value && order.value.status !== 'paid' && !isOrderFailed(order.value)) {
      startPolling();
    }
  }
});

const checkPaymentStatus = async () => {
  if (!orderId.value) return;
  syncing.value = true;
  try {
    if (!isGuest.value) {
      await syncPaymentStatusByOrder(orderId.value);
    }
    await fetchOrder();
    if (isOrderFailed(order.value)) {
      router.replace(`/payment/failed?order_id=${orderId.value}`);
    }
  } catch {
    // Silent sync errors
  } finally {
    syncing.value = false;
  }
};

const confirmMockPayment = async () => {
  if (!orderId.value) return;
  syncing.value = true;
  try {
    if (isGuest.value) {
      await confirmGuestMockPayment(orderId.value, guestEmail.value);
    } else {
      await confirmMockPaymentApi(orderId.value);
    }
  } catch (err) {
    if (import.meta.env.DEV) {
      console.error('Mock payment confirmation failed:', err);
    }
  } finally {
    syncing.value = false;
  }
};

// Redirect to /payment/failed if order was cancelled or YooKassa reported a cancellation reason
watch(order, (newOrder) => {
  if (newOrder && isOrderFailed(newOrder)) {
    router.replace(`/payment/failed?order_id=${orderId.value}`);
  }
});

onUnmounted(() => {
  stopPolling();
});
</script>

<style scoped>
.payment-result {
  max-width: 480px;
  margin: 0 auto;
  padding: 40px 16px calc(24px + var(--bottom-nav-height, 56px) + env(safe-area-inset-bottom, 0px));
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

.payment-result__icon--success {
  background: #e6f4ea;
  color: #0d7a3e;
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

.payment-result__poll-info {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-top: 8px;
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

.payment-result__badge {
  padding: 4px 10px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
}

.payment-result__badge--success {
  background: #e6f4ea;
  color: #0d7a3e;
}

.payment-result__badge--warning {
  background: #fff8e1;
  color: #b78900;
}

.payment-result__badge--error {
  background: #fce8e6;
  color: #c5221f;
}

.payment-result__amount {
  font-weight: 700;
  font-size: 16px;
}

.payment-result__notice {
  background: var(--color-bg-white);
  border-radius: 12px;
  padding: 14px 16px;
  margin-bottom: 24px;
  text-align: left;
  font-size: 14px;
  color: var(--color-text-secondary);
  line-height: 1.4;
}

.payment-result__error {
  text-align: center;
  padding: 40px 20px;
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
</style>
