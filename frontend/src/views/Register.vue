<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1 class="auth-title">Регистрация</h1>
      <p class="auth-subtitle">Создайте аккаунт, чтобы начать покупки</p>

      <form @submit.prevent="handleRegister" class="auth-form" data-testid="register-form">
        <!-- Full Name -->
        <div class="field">
          <label class="field-label">Имя</label>
          <input
            v-model="fullName"
            type="text"
            placeholder="Как вас зовут?"
            class="field-input"
            :class="{ 'field-input--error': errors.fullName }"
            data-testid="register-name"
          />
          <span v-if="errors.fullName" class="field-error">{{ errors.fullName }}</span>
        </div>

        <!-- Email -->
        <div class="field">
          <label class="field-label">Email <span class="required">*</span></label>
          <input
            v-model="email"
            type="email"
            placeholder="example@mail.ru"
            class="field-input"
            :class="{ 'field-input--error': errors.email }"
            data-testid="register-email"
          />
          <span v-if="errors.email" class="field-error">{{ errors.email }}</span>
        </div>

        <!-- Password -->
        <div class="field">
          <label class="field-label">Пароль <span class="required">*</span></label>
          <div class="field-input-wrapper">
            <input
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              placeholder="Минимум 6 символов"
              class="field-input"
              :class="{ 'field-input--error': errors.password }"
              data-testid="register-password"
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
          <!-- Password strength -->
          <div v-if="password" class="password-strength">
            <div class="password-strength__bar">
              <div
                class="password-strength__fill"
                :style="{ width: strengthPercent + '%', background: strengthColor }"
              />
            </div>
            <span class="password-strength__text" :style="{ color: strengthColor }">
              {{ strengthText }}
            </span>
          </div>
          <span v-if="errors.password" class="field-error">{{ errors.password }}</span>
        </div>

        <!-- Role Selector -->
        <div class="field">
          <label class="field-label">Тип аккаунта</label>
          <div class="role-selector">
            <button
              type="button"
              class="role-option"
              :class="{ 'role-option--active': selectedRole === 'user' }"
              data-testid="role-user"
              @click="selectedRole = 'user'"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
              <span>Покупатель</span>
            </button>
            <button
              type="button"
              class="role-option"
              :class="{ 'role-option--active': selectedRole === 'supplier' }"
              data-testid="role-supplier"
              @click="selectedRole = 'supplier'"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/>
                <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
                <line x1="12" y1="22.08" x2="12" y2="12"/>
              </svg>
              <span>Поставщик</span>
            </button>
          </div>
        </div>

        <!-- Confirm Password -->
        <div class="field">
          <label class="field-label">Повторите пароль <span class="required">*</span></label>
          <div class="field-input-wrapper">
            <input
              v-model="confirmPassword"
              :type="showConfirm ? 'text' : 'password'"
              placeholder="Повторите пароль"
              class="field-input"
              :class="{ 'field-input--error': errors.confirmPassword }"
              data-testid="register-password-confirm"
            />
            <button
              type="button"
              class="field-toggle"
              @click="showConfirm = !showConfirm"
              tabindex="-1"
            >
              <svg v-if="showConfirm" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
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
        <button
          type="submit"
          class="auth-submit"
          :disabled="isSubmitting"
          data-testid="register-submit"
        >
          {{ isSubmitting ? 'Регистрация...' : 'Зарегистрироваться' }}
        </button>
      </form>

      <!-- Success message -->
      <div v-if="registrationSuccess" class="auth-success" data-testid="register-success">
        <p>
          Регистрация прошла успешно! Письмо с подтверждением отправлено на
          <strong>{{ email }}</strong>.
        </p>
        <p class="auth-success__hint">Проверьте почту и перейдите по ссылке в письме.</p>
      </div>

      <!-- Global error -->
      <p v-if="serverError" class="auth-error" data-testid="register-error">{{ serverError }}</p>

      <!-- OAuth -->
      <template v-if="providers.google || providers.yandex">
        <div class="auth-divider">
          <span>или</span>
        </div>

        <div class="oauth-buttons">
          <button v-if="providers.google" @click="loginWithGoogle" class="oauth-button oauth-button--google" data-testid="register-google">
            <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
            <span>Google</span>
          </button>
          <button v-if="providers.yandex" @click="loginWithYandex" class="oauth-button oauth-button--yandex" data-testid="register-yandex">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="#FF0000"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 14.3h-1.86l-2.5-4.68v4.68H10.5V7.7h1.86l2.5 4.68V7.7h1.78v8.6z"/></svg>
            <span>Яндекс</span>
          </button>
        </div>
      </template>

      <p class="auth-footer">
        Уже есть аккаунт? <router-link to="/login">Войти</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/services/api';
import { register as apiRegister } from '@/api/auth';
import { useAuth } from '@/composables/useAuth';

const router = useRouter();
const { setAuth } = useAuth();

let redirectTimeoutId = null;

const fullName = ref('');
const email = ref('');
const password = ref('');
const confirmPassword = ref('');
const selectedRole = ref('user');
const showPassword = ref(false);
const showConfirm = ref(false);
const isSubmitting = ref(false);
const serverError = ref('');
const registrationSuccess = ref(false);
const errors = ref({});
const providers = ref({ google: false, yandex: false });

onMounted(async () => {
  try {
    const { data } = await api.get('/auth/providers/');
    providers.value = {
      google: Boolean(data.google),
      yandex: Boolean(data.yandex),
    };
  } catch {
    providers.value = { google: false, yandex: false };
  }
});

const strengthPercent = computed(() => {
  const p = password.value;
  if (!p) return 0;
  let score = 0;
  if (p.length >= 6) score += 25;
  if (p.length >= 10) score += 25;
  if (/[A-Z]/.test(p)) score += 25;
  if (/[0-9!@#$%^&*]/.test(p)) score += 25;
  return score;
});

const strengthColor = computed(() => {
  const s = strengthPercent.value;
  if (s < 50) return 'var(--color-danger)';
  if (s < 75) return '#FFA800';
  return '#34C759';
});

const strengthText = computed(() => {
  const s = strengthPercent.value;
  if (s < 50) return 'Слабый пароль';
  if (s < 75) return 'Средний пароль';
  return 'Надёжный пароль';
});

function validate() {
  const e = {};
  if (!email.value.trim()) {
    e.email = 'Введите email';
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value)) {
    e.email = 'Некорректный email';
  }
  if (!password.value) {
    e.password = 'Введите пароль';
  } else if (password.value.length < 6) {
    e.password = 'Минимум 6 символов';
  }
  if (!confirmPassword.value) {
    e.confirmPassword = 'Подтвердите пароль';
  } else if (password.value !== confirmPassword.value) {
    e.confirmPassword = 'Пароли не совпадают';
  }
  errors.value = e;
  return Object.keys(e).length === 0;
}

async function handleRegister() {
  serverError.value = '';
  registrationSuccess.value = false;
  if (!validate()) return;

  isSubmitting.value = true;
  try {
    const response = await apiRegister({
      email: email.value,
      password: password.value,
      full_name: fullName.value.trim() || null,
      role: selectedRole.value,
    });
    setAuth(response.data.access_token, response.data.user);
    registrationSuccess.value = true;
    redirectTimeoutId = setTimeout(() => router.push('/'), 3000);
  } catch (err) {
    serverError.value = err.response?.data?.detail || 'Ошибка регистрации. Попробуйте позже.';
  } finally {
    isSubmitting.value = false;
  }
}

onUnmounted(() => {
  if (redirectTimeoutId) {
    clearTimeout(redirectTimeoutId);
  }
});

async function loginWithGoogle() {
  try {
    const response = await api.get('/auth/google/login');
    window.location.href = response.data.url;
  } catch (err) {
    serverError.value = err.response?.data?.detail || 'Ошибка входа через Google';
  }
}

async function loginWithYandex() {
  try {
    const response = await api.get('/auth/yandex/login');
    window.location.href = response.data.url;
  } catch (err) {
    serverError.value = err.response?.data?.detail || 'Ошибка входа через Яндекс';
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
  color: var(--color-danger);
}

.field-input {
  width: 100%;
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  font-size: 15px;
  background: var(--color-bg-white);
  transition: border-color 0.15s;
}

.field-input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.field-input--error {
  border-color: var(--color-danger);
}

.field-input-wrapper {
  position: relative;
}

.field-input-wrapper .field-input {
  padding-right: 44px;
}

.field-toggle {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--color-text-secondary);
  background: none;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px;
}

.field-error {
  font-size: 12px;
  color: var(--color-danger);
}

.password-strength {
  display: flex;
  align-items: center;
  gap: 8px;
}

.password-strength__bar {
  flex: 1;
  height: 4px;
  background: var(--color-border);
  border-radius: 2px;
  overflow: hidden;
}

.password-strength__fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.2s, background 0.2s;
}

.password-strength__text {
  font-size: 12px;
  font-weight: 500;
}

.auth-submit {
  width: 100%;
  padding: 14px;
  border-radius: 12px;
  background: var(--color-primary);
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  margin-top: 4px;
  transition: opacity 0.15s;
}

.auth-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.auth-error {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  background: #fff0f0;
  color: var(--color-danger);
  font-size: 14px;
  text-align: center;
}

.auth-success {
  margin-top: 12px;
  padding: 14px 16px;
  border-radius: 10px;
  background: #e6f7ed;
  color: #0d7a3e;
  font-size: 14px;
  text-align: center;
}

.auth-success__hint {
  margin-top: 6px;
  font-size: 13px;
  color: #0d7a3e;
  opacity: 0.9;
}

.auth-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 20px 0;
  color: var(--color-text-secondary);
  font-size: 14px;
}

.auth-divider::before,
.auth-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--color-border);
}

.oauth-buttons {
  display: flex;
  gap: 10px;
}

.oauth-button {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-white);
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text);
  transition: background 0.15s;
}

.oauth-button:hover {
  background: var(--color-bg);
}

.auth-footer {
  text-align: center;
  margin-top: 20px;
  font-size: 14px;
  color: var(--color-text-secondary);
}

.role-selector {
  display: flex;
  gap: 8px;
}

.role-option {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-white);
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-secondary);
  transition: all 0.15s;
}

.role-option--active {
  border-color: var(--color-primary);
  background: #e8f0fe;
  color: var(--color-primary);
}

/* Desktop */
@media (min-width: 768px) {
  .auth-page {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 40px 20px;
  }
  
  .auth-card {
    width: 100%;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  }
}
</style>
