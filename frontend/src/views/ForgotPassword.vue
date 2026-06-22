<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1 class="auth-title">Восстановление пароля</h1>
      <p class="auth-subtitle">Введите email, и мы отправим ссылку для сброса пароля</p>

      <form v-if="!isSent" @submit.prevent="handleSubmit" class="auth-form" data-testid="forgot-password-form">
        <!-- Email -->
        <div class="field">
          <label class="field-label">Email <span class="required">*</span></label>
          <input
            v-model="email"
            type="email"
            placeholder="example@mail.ru"
            class="field-input"
            :class="{ 'field-input--error': errors.email }"
            data-testid="forgot-password-email"
          />
          <span v-if="errors.email" class="field-error">{{ errors.email }}</span>
        </div>

        <!-- Submit -->
        <button
          type="submit"
          class="auth-submit"
          :disabled="isSubmitting"
          data-testid="forgot-password-submit"
        >
          {{ isSubmitting ? 'Отправка...' : 'Отправить ссылку' }}
        </button>
      </form>

      <div v-else class="auth-success" data-testid="forgot-password-success">
        <p>Если указанный email зарегистрирован, ссылка для сброса пароля отправлена.</p>
      </div>

      <!-- Global error -->
      <p v-if="serverError" class="auth-error" data-testid="forgot-password-error">{{ serverError }}</p>

      <p class="auth-footer">
        <router-link to="/login">Вернуться ко входу</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import api from '@/services/api';

const email = ref('');
const isSubmitting = ref(false);
const isSent = ref(false);
const serverError = ref('');
const errors = ref({});

function validate() {
  const e = {};
  if (!email.value.trim()) {
    e.email = 'Введите email';
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value)) {
    e.email = 'Некорректный email';
  }
  errors.value = e;
  return Object.keys(e).length === 0;
}

async function handleSubmit() {
  serverError.value = '';
  if (!validate()) return;

  isSubmitting.value = true;
  try {
    await api.post('/auth/password-reset-request/', { email: email.value.trim() });
    isSent.value = true;
  } catch (err) {
    // Всегда показываем успех, чтобы не раскрывать существование email.
    // Логируем ошибку только в dev-режиме.
    if (import.meta.env.DEV) {
       
      console.error('Password reset request failed:', err);
    }
    isSent.value = true;
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<style scoped>
.auth-page {
  background: var(--color-bg);
  min-height: 100vh;
  padding: 24px 16px 40px;
}

.auth-card {
  background: var(--color-bg-white);
  border-radius: 16px;
  padding: 28px 20px;
  max-width: 420px;
  margin: 0 auto;
}

.auth-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 4px;
}

.auth-subtitle {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin-bottom: 24px;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text);
}

.required {
  color: var(--color-error, #e53935);
}

.field-input {
  padding: 12px 14px;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  font-size: 15px;
  background: var(--color-bg);
  color: var(--color-text);
  outline: none;
  transition: border-color 0.2s;
}

.field-input:focus {
  border-color: var(--color-primary);
}

.field-input--error {
  border-color: var(--color-error, #e53935);
}

.field-error {
  font-size: 13px;
  color: var(--color-error, #e53935);
}

.auth-submit {
  margin-top: 8px;
  padding: 14px;
  border: none;
  border-radius: 10px;
  background: var(--color-primary);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}

.auth-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.auth-error {
  margin-top: 16px;
  padding: 12px;
  border-radius: 10px;
  background: #fce8e6;
  color: #c5221f;
  font-size: 14px;
}

.auth-success {
  margin-top: 8px;
  padding: 16px;
  border-radius: 10px;
  background: #e6f4ea;
  color: #0d7a3e;
  font-size: 14px;
  line-height: 1.5;
}

.auth-footer {
  margin-top: 20px;
  text-align: center;
  font-size: 14px;
  color: var(--color-text-secondary);
}

.auth-footer a {
  color: var(--color-primary);
  text-decoration: none;
}
</style>
