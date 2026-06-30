<template>
  <div class="verify-result-page" data-testid="verify-email-success">
    <div class="verify-result-card verify-result-card--success">
      <div class="verify-result-icon">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#0d7a3e" stroke-width="2">
          <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
          <polyline points="22 4 12 14.01 9 11.01"/>
        </svg>
      </div>
      <h1 class="verify-result-title">Email подтверждён</h1>
      <p class="verify-result-text">
        Ваш email успешно подтверждён. Теперь вы можете пользоваться всеми функциями магазина.
      </p>
      <router-link to="/" class="verify-result-btn verify-result-btn--success">
        На главную
      </router-link>
    </div>
  </div>
</template>

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

.verify-result-card--success {
  border-top: 4px solid #0d7a3e;
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

.verify-result-btn--success {
  background: #0d7a3e;
  color: #fff;
}

.verify-result-btn:hover {
  opacity: 0.9;
}
</style>
