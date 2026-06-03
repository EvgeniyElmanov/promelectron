<template>
  <div class="payment-result" data-testid="payment-failed-page">
    <div class="payment-result__icon payment-result__icon--failed">
      <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <path d="M15 9l-6 6M9 9l6 6"/>
      </svg>
    </div>

    <h1 class="payment-result__title">Оплата не прошла</h1>
    <p class="payment-result__subtitle">
      Что-то пошло не так при оплате заказа №{{ orderId }}. Вы можете попробовать снова.
    </p>

    <div class="payment-result__actions">
      <button
        v-if="orderId"
        class="payment-result__btn payment-result__btn--primary"
        @click="retryPayment"
      >
        Попробовать ещё раз
      </button>
      <router-link to="/orders" class="payment-result__btn payment-result__btn--secondary">
        Мои заказы
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

const route = useRoute();
const router = useRouter();
const orderId = ref(route.query.order_id || route.params.id);

const retryPayment = () => {
  router.push(`/checkout/${orderId.value}`);
};
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
</style>
