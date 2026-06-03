<template>
  <div class="payment-result" data-testid="payment-success-page">
    <div class="payment-result__icon payment-result__icon--success">
      <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <path d="M9 12l2 2 4-4"/>
      </svg>
    </div>

    <h1 class="payment-result__title">Оплата прошла успешно!</h1>
    <p class="payment-result__subtitle">
      Заказ №{{ orderId }} оплачен. Мы отправили подтверждение на ваш email.
    </p>

    <div v-if="loading" class="payment-result__loading">
      <div class="payment-result__spinner"></div>
      <p>Проверяем статус заказа...</p>
    </div>

    <div v-else-if="order" class="payment-result__details">
      <div class="payment-result__row">
        <span>Статус</span>
        <span class="payment-result__badge payment-result__badge--success">{{ order.status === 'paid' ? 'Оплачен' : order.status }}</span>
      </div>
      <div class="payment-result__row">
        <span>Сумма</span>
        <span class="payment-result__amount">{{ formatPrice(order.total_price) }} ₽</span>
      </div>
    </div>

    <div class="payment-result__actions">
      <router-link to="/orders" class="payment-result__btn payment-result__btn--primary">
        Мои заказы
      </router-link>
      <router-link to="/" class="payment-result__btn payment-result__btn--secondary">
        В каталог
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import api from '@/services/api';

const route = useRoute();
const orderId = ref(route.query.order_id || route.params.id);
const order = ref(null);
const loading = ref(true);

function formatPrice(value) {
  return Number(value).toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

const fetchOrder = async () => {
  if (!orderId.value) {
    loading.value = false;
    return;
  }
  try {
    const { data } = await api.get(`/orders/${orderId.value}`);
    order.value = data;
  } catch (err) {
    console.error('Failed to fetch order:', err);
  } finally {
    loading.value = false;
  }
};

onMounted(fetchOrder);
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

.payment-result__amount {
  font-weight: 700;
  font-size: 16px;
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
