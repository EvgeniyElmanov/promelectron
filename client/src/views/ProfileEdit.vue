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
      <!-- Avatar Card -->
      <div class="edit-card edit-card--avatar">
        <div class="avatar-section">
          <div class="avatar-preview">
            <img v-if="avatarUrl" :src="avatarUrl" class="avatar-preview__img" alt="" />
            <span v-else class="avatar-preview__fallback">{{ initials }}</span>
          </div>
          <label class="avatar-upload-btn">
            <input type="file" accept="image/*" @change="onAvatarChange" hidden />
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z"/>
              <circle cx="12" cy="13" r="4"/>
            </svg>
            <span>Сменить фото</span>
          </label>
        </div>
        <div v-if="avatarUploading" class="avatar-progress">
          <div class="avatar-progress__bar">
            <div class="avatar-progress__fill" :style="{ width: avatarProgress + '%' }"></div>
          </div>
          <span class="avatar-progress__text">{{ avatarProgress }}%</span>
        </div>
      </div>

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

          <AddressForm
            v-model="form.shipping_address"
            label="Адрес доставки"
            testid-prefix="edit-profile-"
          />

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
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/services/api';
import { useAuth } from '@/composables/useAuth';
import AddressForm from '@/components/AddressForm.vue';

const router = useRouter();
const { user: authUser, setAuth } = useAuth();

const loading = ref(true);
const savingProfile = ref(false);
const savingPassword = ref(false);
const profileSuccess = ref(false);
const profileError = ref('');
const passwordSuccess = ref(false);
const passwordError = ref('');

const form = ref({
  full_name: '',
  email: '',
  shipping_address: { region: '', district: '', city: '', street: '', house: '', apartment: '' },
});
const passwordForm = ref({ old_password: '', new_password: '', confirm_password: '' });
const errors = ref({});
const passwordErrors = ref({});
const showOld = ref(false);
const showNew = ref(false);
const showConfirm = ref(false);
const avatarUrl = ref('');
const avatarUploading = ref(false);
const avatarProgress = ref(0);

const initials = computed(() => {
  const name = form.value.full_name || form.value.email || '?';
  const parts = name.split(' ').filter(Boolean);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return name.charAt(0).toUpperCase();
});

const onAvatarChange = async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  if (!file.type.startsWith('image/')) return;

  avatarUploading.value = true;
  avatarProgress.value = 0;
  try {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await api.post('/me/avatar', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        const percent = progressEvent.total
          ? Math.round((progressEvent.loaded * 100) / progressEvent.total)
          : 0;
        avatarProgress.value = percent;
      },
    });
    avatarUrl.value = data.avatar_url || '';
    // Update auth user
    setAuth(localStorage.getItem('access_token'), data);
  } catch (err) {
    passwordError.value = err.response?.data?.detail || 'Ошибка загрузки фото';
  } finally {
    // Доводим до 100% и показываем минимум 500мс, даже если загрузка моментальная
    avatarProgress.value = 100;
    await new Promise((r) => setTimeout(r, 500));
    avatarUploading.value = false;
    avatarProgress.value = 0;
    e.target.value = '';
  }
};

const fetchProfile = async () => {
  loading.value = true;
  try {
    const { data } = await api.get('/auth/profile');
    form.value.full_name = data.full_name || '';
    form.value.email = data.email || '';
    form.value.shipping_address = data.shipping_address || {
      region: '', district: '', city: '', street: '', house: '', apartment: '',
    };
    avatarUrl.value = data.avatar_url || '';
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

    const addr = form.value.shipping_address;
    const hasAny = addr && (addr.region || addr.district || addr.city || addr.street || addr.house || addr.apartment);
    payload.shipping_address = hasAny ? { ...addr } : null;

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

.edit-card--avatar {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.avatar-preview {
  width: 96px;
  height: 96px;
  border-radius: 50%;
  background: var(--color-primary-light);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36px;
  font-weight: 700;
  overflow: hidden;
  user-select: none;
}

.avatar-preview__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-upload-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: 10px;
  background: var(--color-bg);
  color: var(--color-text);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}

.avatar-upload-btn:hover {
  background: var(--color-border);
}

.avatar-progress {
  width: 100%;
  max-width: 200px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.avatar-progress__bar {
  flex: 1;
  height: 6px;
  background: var(--color-border);
  border-radius: 3px;
  overflow: hidden;
}

.avatar-progress__fill {
  height: 100%;
  background: var(--color-primary);
  border-radius: 3px;
  transition: width 0.2s ease;
}

.avatar-progress__text {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-primary);
  min-width: 36px;
  text-align: right;
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
