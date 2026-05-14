<template>
  <div class="profile-edit-page">
    <!-- Header -->
    <div class="profile-edit-header">
      <button class="back-btn" @click="$router.back()">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M15 18l-6-6 6-6"/>
        </svg>
      </button>
      <h1 class="profile-edit-title">Редактирование профиля</h1>
      <div class="header-spacer"></div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="profile-edit-loading">
      <div class="spinner"></div>
      <span>Загрузка...</span>
    </div>

    <!-- Content -->
    <div v-else class="profile-edit-content">
      <!-- Personal Data Card -->
      <div class="edit-card">
        <h2 class="edit-card-title">Личные данные</h2>
        <form @submit.prevent="handleSaveProfile" class="edit-form">
          <div class="field">
            <label class="field-label">Имя</label>
            <input
              v-model="form.full_name"
              type="text"
              placeholder="Ваше имя"
              class="field-input"
              :class="{ 'field-input--error': errors.full_name }"
              data-testid="edit-profile-name"
            />
            <span v-if="errors.full_name" class="field-error">{{ errors.full_name }}</span>
          </div>

          <div class="field">
            <label class="field-label">Email <span class="required">*</span></label>
            <input
              v-model="form.email"
              type="email"
              placeholder="example@mail.ru"
              class="field-input"
              :class="{ 'field-input--error': errors.email }"
              data-testid="edit-profile-email"
            />
            <span v-if="errors.email" class="field-error">{{ errors.email }}</span>
          </div>

          <button
            type="submit"
            class="save-btn"
            :disabled="savingProfile"
            data-testid="edit-profile-save"
          >
            {{ savingProfile ? 'Сохранение...' : 'Сохранить изменения' }}
          </button>
        </form>

        <p v-if="profileSuccess" class="success-msg">Данные успешно обновлены</p>
        <p v-if="profileError" class="error-msg">{{ profileError }}</p>
      </div>

      <!-- Password Card -->
      <div class="edit-card">
        <h2 class="edit-card-title">Смена пароля</h2>
        <form @submit.prevent="handleChangePassword" class="edit-form">
          <div class="field">
            <label class="field-label">Текущий пароль <span class="required">*</span></label>
            <div class="field-input-wrapper">
              <input
                v-model="passwordForm.old_password"
                :type="showOld ? 'text' : 'password'"
                placeholder="Введите текущий пароль"
                class="field-input"
                :class="{ 'field-input--error': passwordErrors.old_password }"
                data-testid="edit-profile-old-password"
              />
              <button type="button" class="field-toggle" @click="showOld = !showOld" tabindex="-1">
                <svg v-if="showOld" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>
                <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/>
                  <line x1="1" y1="1" x2="23" y2="23"/>
                </svg>
              </button>
            </div>
            <span v-if="passwordErrors.old_password" class="field-error">{{ passwordErrors.old_password }}</span>
          </div>

          <div class="field">
            <label class="field-label">Новый пароль <span class="required">*</span></label>
            <div class="field-input-wrapper">
              <input
                v-model="passwordForm.new_password"
                :type="showNew ? 'text' : 'password'"
                placeholder="Минимум 6 символов"
                class="field-input"
                :class="{ 'field-input--error': passwordErrors.new_password }"
                data-testid="edit-profile-new-password"
              />
              <button type="button" class="field-toggle" @click="showNew = !showNew" tabindex="-1">
                <svg v-if="showNew" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>
                <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/>
                  <line x1="1" y1="1" x2="23" y2="23"/>
                </svg>
              </button>
            </div>
            <span v-if="passwordErrors.new_password" class="field-error">{{ passwordErrors.new_password }}</span>
          </div>

          <div class="field">
            <label class="field-label">Повторите новый пароль <span class="required">*</span></label>
            <div class="field-input-wrapper">
              <input
                v-model="passwordForm.confirm_password"
                :type="showConfirm ? 'text' : 'password'"
                placeholder="Повторите пароль"
                class="field-input"
                :class="{ 'field-input--error': passwordErrors.confirm_password }"
                data-testid="edit-profile-confirm-password"
              />
              <button type="button" class="field-toggle" @click="showConfirm = !showConfirm" tabindex="-1">
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
            <span v-if="passwordErrors.confirm_password" class="field-error">{{ passwordErrors.confirm_password }}</span>
          </div>

          <button
            type="submit"
            class="save-btn"
            :disabled="savingPassword"
            data-testid="edit-profile-password-save"
          >
            {{ savingPassword ? 'Смена пароля...' : 'Сменить пароль' }}
          </button>
        </form>

        <p v-if="passwordSuccess" class="success-msg">Пароль успешно изменён</p>
        <p v-if="passwordError" class="error-msg">{{ passwordError }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/services/api';
import { useAuth } from '@/composables/useAuth';

const router = useRouter();
const { user: authUser, setAuth } = useAuth();

const loading = ref(true);
const savingProfile = ref(false);
const savingPassword = ref(false);
const profileSuccess = ref(false);
const profileError = ref('');
const passwordSuccess = ref(false);
const passwordError = ref('');

const form = ref({ full_name: '', email: '' });
const passwordForm = ref({ old_password: '', new_password: '', confirm_password: '' });
const errors = ref({});
const passwordErrors = ref({});
const showOld = ref(false);
const showNew = ref(false);
const showConfirm = ref(false);

const fetchProfile = async () => {
  loading.value = true;
  try {
    const { data } = await api.get('/auth/profile');
    form.value.full_name = data.full_name || '';
    form.value.email = data.email || '';
  } catch {
    // silently fail
  } finally {
    loading.value = false;
  }
};

function validateProfile() {
  const e = {};
  if (!form.value.email.trim()) {
    e.email = 'Введите email';
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.value.email)) {
    e.email = 'Некорректный email';
  }
  errors.value = e;
  return Object.keys(e).length === 0;
}

async function handleSaveProfile() {
  profileSuccess.value = false;
  profileError.value = '';
  if (!validateProfile()) return;

  savingProfile.value = true;
  try {
    const payload = {};
    if (form.value.full_name.trim()) payload.full_name = form.value.full_name.trim();
    if (form.value.email.trim()) payload.email = form.value.email.trim();

    const { data } = await api.patch('/me', payload);
    setAuth(localStorage.getItem('access_token'), data);
    profileSuccess.value = true;
    setTimeout(() => (profileSuccess.value = false), 3000);
  } catch (err) {
    profileError.value = err.response?.data?.detail || 'Не удалось сохранить изменения';
  } finally {
    savingProfile.value = false;
  }
}

function validatePassword() {
  const e = {};
  if (!passwordForm.value.old_password) {
    e.old_password = 'Введите текущий пароль';
  }
  if (!passwordForm.value.new_password) {
    e.new_password = 'Введите новый пароль';
  } else if (passwordForm.value.new_password.length < 6) {
    e.new_password = 'Минимум 6 символов';
  }
  if (passwordForm.value.new_password !== passwordForm.value.confirm_password) {
    e.confirm_password = 'Пароли не совпадают';
  }
  passwordErrors.value = e;
  return Object.keys(e).length === 0;
}

async function handleChangePassword() {
  passwordSuccess.value = false;
  passwordError.value = '';
  if (!validatePassword()) return;

  savingPassword.value = true;
  try {
    await api.patch('/me/password', {
      old_password: passwordForm.value.old_password,
      new_password: passwordForm.value.new_password,
    });
    passwordSuccess.value = true;
    passwordForm.value = { old_password: '', new_password: '', confirm_password: '' };
    setTimeout(() => (passwordSuccess.value = false), 3000);
  } catch (err) {
    passwordError.value = err.response?.data?.detail || 'Не удалось сменить пароль';
  } finally {
    savingPassword.value = false;
  }
}

onMounted(fetchProfile);
</script>

<style scoped>
.profile-edit-page {
  background: var(--color-bg);
  min-height: 100vh;
  padding: 16px 12px 80px;
}

.profile-edit-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 0 16px;
}

.back-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  color: var(--color-text);
  flex-shrink: 0;
}

.profile-edit-title {
  flex: 1;
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text);
  text-align: center;
}

.header-spacer {
  width: 36px;
  flex-shrink: 0;
}

.profile-edit-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 12px;
  color: var(--color-text-secondary);
  font-size: 14px;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.profile-edit-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.edit-card {
  background: var(--color-bg-white);
  border-radius: 14px;
  padding: 20px;
}

.edit-card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 16px;
}

.edit-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
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

.save-btn {
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

.save-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.success-msg {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  background: #e6f7ed;
  color: #0d7a3e;
  font-size: 14px;
  text-align: center;
}

.error-msg {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  background: #fff0f0;
  color: var(--color-danger);
  font-size: 14px;
  text-align: center;
}

/* Desktop */
@media (min-width: 768px) {
  .profile-edit-page {
    padding: 24px 20px 40px;
  }
  
  .profile-edit-content {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    align-items: start;
  }
}
</style>
