<template>
  <div class="guest-success" data-testid="guest-order-success-page">
    <div class="guest-success__icon">
      <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
        <polyline points="22 4 12 14.01 9 11.01"/>
      </svg>
    </div>
    <h1 class="guest-success__title">Заказ оформлен!</h1>
    <p class="guest-success__subtitle">
      Спасибо за покупку. Мы отправили подтверждение на email.
    </p>

    <div class="guest-success__card">
      <div class="guest-success__row">
        <span class="guest-success__label">Номер заказа</span>
        <span class="guest-success__value" data-testid="success-order-id">№{{ orderId }}</span>
      </div>
      <div class="guest-success__row">
        <span class="guest-success__label">Email</span>
        <span class="guest-success__value" data-testid="success-email">{{ email }}</span>
      </div>
    </div>

    <p class="guest-success__hint">
      Вы можете отслеживать статус заказа по ссылке из письма.
    </p>

    <router-link to="/" class="guest-success__btn">
      Вернуться в каталог
    </router-link>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();
const orderId = computed(() => route.params.id);
const email = computed(() => route.query.email || '');
</script>

<style scoped>
.guest-success {
  max-width: 480px;
  margin: 0 auto;
  padding: 40px 20px calc(24px + var(--bottom-nav-height, 56px) + env(safe-area-inset-bottom, 0px));
  text-align: center;
  min-height: 100vh;
  background: var(--color-bg);
}

.guest-success__icon {
  color: #0d7a3e;
  margin-bottom: 20px;
}

.guest-success__title {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 8px;
}

.guest-success__subtitle {
  font-size: 15px;
  color: var(--color-text-secondary);
  margin-bottom: 28px;
}

.guest-success__card {
  background: var(--color-bg-white);
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 20px;
  text-align: left;
}

.guest-success__row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
}

.guest-success__row:first-child {
  border-bottom: 1px solid var(--color-border);
}

.guest-success__label {
  font-size: 14px;
  color: var(--color-text-secondary);
}

.guest-success__value {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
}

.guest-success__hint {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-bottom: 24px;
}

.guest-success__btn {
  display: inline-block;
  width: 100%;
  padding: 14px 20px;
  border-radius: 12px;
  background: var(--color-primary);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
}
</style>
