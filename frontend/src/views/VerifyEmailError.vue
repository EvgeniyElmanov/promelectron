<template>
  <div class="verify-result-page" data-testid="verify-email-error">
    <div class="verify-result-card verify-result-card--error">
      <div class="verify-result-icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--color-danger)" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <line x1="15" y1="9" x2="9" y2="15"/>
          <line x1="9" y1="9" x2="15" y2="15"/>
        </svg>
      </div>
      <h1 class="verify-result-title">Не удалось подтвердить email</h1>
      <p class="verify-result-text">
        {{ errorText }}
      </p>
      <div class="verify-result-actions">
        <router-link to="/profile" class="verify-result-btn verify-result-btn--primary">
          В профиль
        </router-link>
        <router-link to="/" class="verify-result-btn verify-result-btn--secondary">
          На главную
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();
const reason = computed(() => route.query.reason || 'invalid');

const errorText = computed(() => {
  const messages = {
    expired: 'Ссылка для подтверждения истекла. Запросите новое письмо в профиле.',
    invalid: 'Ссылка недействительная или уже использована. Запросите новое письмо в профиле.',
  };
  return messages[reason.value] || messages.invalid;
});
</script>

<style scoped>
.verify-result-page {
  background: var(--color-bg);
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 16px;
}

.verify-result-card {
  background: var(--color-bg-white);
  border-radius: 16px;
  padding: 32px 24px;
  max-width: 420px;
  width: 100%;
  text-align: center;
}

.verify-result-card--error {
  border-top: 4px solid var(--color-danger);
}

.verify-result-icon {
  margin-bottom: 16px;
}

.verify-result-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 8px;
}

.verify-result-text {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin-bottom: 24px;
  line-height: 1.5;
}

.verify-result-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.verify-result-btn {
  display: inline-block;
  width: 100%;
  padding: 14px;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  text-decoration: none;
  transition: opacity 0.15s;
}

.verify-result-btn--primary {
  background: var(--color-primary);
  color: #fff;
}

.verify-result-btn--secondary {
  background: var(--color-bg);
  color: var(--color-text);
}

.verify-result-btn:hover {
  opacity: 0.9;
}
</style>
