<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1 class="auth-title">Новый пароль</h1>
      <p class="auth-subtitle">Придумайте новый пароль для входа в аккаунт</p>

      <form v-if="!isSuccess" @submit.prevent="handleSubmit" class="auth-form" data-testid="reset-password-form">
        <!-- New password -->
        <div class="field">
          <label class="field-label">Новый пароль <span class="required">*</span></label>
          <div class="field-input-wrapper">
            <input
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              placeholder="Минимум 8 символов"
              class="field-input"
              :class="{ 'field-input--error': errors.password }"
              data-testid="reset-password-password"
            />
            <button
              type="button"
              class="field-toggle"
              @click="showPassword = !showPassword"
              tabindex="-1"
            >
              <svg v-if="showPassword" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
              <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/>
                <line x1="1" y1="1" x2="23" y2="23"/>
              </svg>
            </button>
          </div>
          <span v-if="errors.password" class="field-error">{{ errors.password }}</span>
        </div>

        <!-- Confirm password -->
        <div class="field">
          <label class="field-label">Подтвердите пароль <span class="required">*</span></label>
          <div class="field-input-wrapper">
            <input
              v-model="confirmPassword"
              :type="showConfirmPassword ? 'text' : 'password'"
              placeholder="Повторите пароль"
              class="field-input"
              :class="{ 'field-input--error': errors.confirmPassword }"
              data-testid="reset-password-confirm"
            />
            <button
              type="button"
              class="field-toggle"
              @click="showConfirmPassword = !showConfirmPassword"
              tabindex="-1"
            >
              <svg v-if="showConfirmPassword" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
              <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/>
                <line x1="1" y1="1" x2="23" y2="23"/>
              </svg>
            </button>
          </div>
          <span v-if="errors.confirmPassword" class="field-error">{{ errors.confirmPassword }}</span>
        </div>

        <!-- Submit -->
        <AppButton
          type="submit"
          block
          :disabled="isSubmitting || !token"
          data-testid="reset-password-submit"
        >
          {{ isSubmitting ? 'Сохранение...' : 'Сохранить пароль' }}
        </AppButton>
      </form>

      <div v-else class="auth-success" data-testid="reset-password-success">
        <p>Пароль успешно изменён. Теперь вы можете войти.</p>
      </div>

      <!-- Global error -->
      <p v-if="serverError" class="auth-error" data-testid="reset-password-error">{{ serverError }}</p>

      <p class="auth-footer">
        <router-link v-if="isSuccess" to="/login">Войти</router-link>
        <router-link v-else to="/login">Вернуться ко входу</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import api from '@/services/api';
import AppButton from '@/components/ui/AppButton.vue';

const route = useRoute();
const router = useRouter();

const token = ref('');
const password = ref('');
const confirmPassword = ref('');
const showPassword = ref(false);
const showConfirmPassword = ref(false);
const isSubmitting = ref(false);
const isSuccess = ref(false);
const serverError = ref('');
const errors = ref({});

onMounted(() => {
  token.value = route.query.token || '';
  if (!token.value) {
    serverError.value = 'Ссылка для сброса пароля недействительна или устарела.';
  }
});

function validate() {
  const e = {};
  if (!password.value) {
    e.password = 'Введите новый пароль';
  } else if (password.value.length < 8) {
    e.password = 'Пароль должен содержать минимум 8 символов';
  }
  if (!confirmPassword.value) {
    e.confirmPassword = 'Подтвердите пароль';
  } else if (confirmPassword.value !== password.value) {
    e.confirmPassword = 'Пароли не совпадают';
  }
  errors.value = e;
  return Object.keys(e).length === 0;
}

async function handleSubmit() {
  serverError.value = '';
  if (!validate()) return;

  isSubmitting.value = true;
  try {
    await api.post('/auth/password-reset/', {
      token: token.value,
      new_password: password.value,
    });
    isSuccess.value = true;
    setTimeout(() => {
      router.push('/login');
    }, 2000);
  } catch (err) {
    serverError.value = err.response?.data?.detail || 'Не удалось сбросить пароль. Ссылка может быть устаревшей.';
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

.field-input-wrapper {
  position: relative;
}

.field-input {
  width: 100%;
  padding: 12px 14px;
  padding-right: 44px;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  font-size: 15px;
  background: var(--color-bg);
  color: var(--color-text);
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
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

.field-toggle {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  padding: 0;
  color: var(--color-text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
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
