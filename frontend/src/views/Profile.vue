<template>
  <div class="profile-page" data-testid="profile-page">
    <!-- Header -->
    <div class="profile-header">
      <h1 class="profile-title" data-testid="profile-title">Профиль</h1>
    </div>

    <!-- Loading -->
    <SkeletonProfile v-if="loading" />

    <!-- Error -->
    <div v-else-if="error" class="profile-error">
      <p>{{ error }}</p>
      <button @click="fetchUserProfile" class="retry-btn">Попробовать снова</button>
    </div>

    <!-- Content -->
    <div v-else-if="user" class="profile-content">
      <!-- Avatar Card -->
      <div class="profile-card profile-card--avatar">
        <div class="avatar" data-testid="profile-avatar">
          <img v-if="user.avatar_url" :src="user.avatar_url" class="avatar__img" alt="" />
          <span v-else>{{ initials }}</span>
        </div>
        <div class="avatar-info">
          <p class="avatar-name">{{ displayName }}</p>
          <p class="avatar-email" data-testid="profile-email">{{ user.email }}</p>
        </div>
      </div>

      <!-- Details Card -->
      <div class="profile-card">
        <h2 class="card-title">Личные данные</h2>
        <div class="detail-list">
          <div class="detail-item">
            <span class="detail-label">Имя</span>
            <span class="detail-value">{{ user.full_name || 'Не указано' }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Email</span>
            <span class="detail-value">{{ user.email }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Роль</span>
            <span class="detail-value">
              <span class="role-badge" :class="user.role" data-testid="profile-role">
                {{ roleLabel }}
              </span>
            </span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Дата регистрации</span>
            <span class="detail-value" data-testid="profile-date">{{ formatDate(user.created_at) }}</span>
          </div>
        </div>
      </div>

      <!-- Actions Card -->
      <div class="profile-card">
        <h2 class="card-title">Действия</h2>
        <div class="action-list">
          <button
            class="action-btn action-btn--primary"
            data-testid="profile-edit-btn"
            @click="$router.push('/profile/edit')"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
            <span>Редактировать профиль</span>
          </button>

          <router-link to="/orders" class="action-btn">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4H6z"/>
              <line x1="3" y1="6" x2="21" y2="6"/>
              <path d="M16 10a4 4 0 01-8 0"/>
            </svg>
            <span>Мои заказы</span>
            <svg class="action-chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 18l6-6-6-6"/>
            </svg>
          </router-link>

          <router-link to="/profile/recipients" class="action-btn" data-testid="profile-recipients-link">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/>
              <circle cx="12" cy="7" r="4"/>
            </svg>
            <span>Получатели</span>
            <svg class="action-chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 18l6-6-6-6"/>
            </svg>
          </router-link>

          <router-link to="/favorites" class="action-btn">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/>
            </svg>
            <span>Избранное</span>
            <svg class="action-chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 18l6-6-6-6"/>
            </svg>
          </router-link>

          <router-link v-if="isAdmin" to="/admin" class="action-btn action-btn--primary" data-testid="profile-admin-link">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="7" height="7" rx="1"/>
              <rect x="14" y="3" width="7" height="7" rx="1"/>
              <rect x="3" y="14" width="7" height="7" rx="1"/>
              <rect x="14" y="14" width="7" height="7" rx="1"/>
            </svg>
            <span>Админ-панель</span>
            <svg class="action-chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 18l6-6-6-6"/>
            </svg>
          </router-link>

          <router-link v-if="isSupplier" to="/my-products" class="action-btn action-btn--primary" data-testid="profile-supplier-link">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M2 17l10 5 10-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M2 12l10 5 10-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span>Мои товары</span>
            <svg class="action-chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 18l6-6-6-6"/>
            </svg>
          </router-link>

          <button class="action-btn action-btn--danger" @click="handleLogout" data-testid="logout-button">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/>
              <polyline points="16 17 21 12 16 7"/>
              <line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
            <span>Выйти</span>
          </button>
        </div>
      </div>
    </div>

    <div v-else class="profile-empty">
      <p>Нет данных пользователя</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import SkeletonProfile from '@/components/SkeletonProfile.vue';
import api from '@/services/api';
import { useAuth } from '@/composables/useAuth';

const router = useRouter();
const { user: authUser, logout, isAdmin, isSupplier } = useAuth();

const localUser = ref(null);
const loading = ref(true);
const error = ref(null);

const user = computed(() => localUser.value || authUser.value);

const initials = computed(() => {
  const name = user.value?.full_name || user.value?.email || '?';
  const parts = name.split(' ').filter(Boolean);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return name.charAt(0).toUpperCase();
});

const displayName = computed(() => {
  return user.value?.full_name || user.value?.email || 'Пользователь';
});

const roleLabel = computed(() => {
  const map = { user: 'Покупатель', admin: 'Администратор', supplier: 'Поставщик' };
  return map[user.value?.role] || user.value?.role;
});

const formatDate = (dateString) => {
  if (!dateString) return '—';
  return new Date(dateString).toLocaleDateString('ru-RU', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
};

const fetchUserProfile = async () => {
  try {
    loading.value = true;
    error.value = null;
    const response = await api.get('/auth/profile');
    localUser.value = response.data;
  } catch (err) {
    if (err.response?.status === 401) {
      localStorage.removeItem('access_token');
      router.push('/login');
      return;
    }
    error.value = err.response?.data?.detail || 'Не удалось загрузить профиль';
  } finally {
    loading.value = false;
  }
};

const handleLogout = () => {
  logout();
  router.push('/login');
};

onMounted(fetchUserProfile);
</script>

<style scoped>
.profile-page {
  background: var(--color-bg);
  min-height: 100vh;
  padding: 16px 12px 80px;
}

.profile-header {
  padding: 10px 0 16px;
}

.profile-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text);
}

.profile-loading {
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

.profile-error {
  text-align: center;
  padding: 40px 20px;
  color: var(--color-danger);
  font-size: 14px;
}

.retry-btn {
  margin-top: 12px;
  padding: 10px 20px;
  border-radius: 10px;
  background: var(--color-primary);
  color: #fff;
  font-size: 14px;
  font-weight: 500;
}

.profile-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.profile-card {
  background: var(--color-bg-white);
  border-radius: 14px;
  padding: 18px;
}

.profile-card--avatar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 18px;
}

.avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: var(--color-primary-light);
  color: var(--color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  font-weight: 700;
  flex-shrink: 0;
  user-select: none;
  overflow: hidden;
}

.avatar__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center top;
}

.avatar-info {
  min-width: 0;
}

.avatar-name {
  font-size: 17px;
  font-weight: 600;
  color: var(--color-text);
  line-height: 1.3;
  word-break: break-word;
}

.avatar-email {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin-top: 2px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 14px;
}

.detail-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.detail-label {
  font-size: 14px;
  color: var(--color-text-secondary);
}

.detail-value {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text);
  text-align: right;
}

.role-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
}

.role-badge.user {
  background: #e8f4fd;
  color: #0066cc;
}

.role-badge.admin {
  background: #e6f7ed;
  color: #0d7a3e;
}

.role-badge.supplier {
  background: #f3e8ff;
  color: #7c3aed;
}

.action-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 500;
  color: var(--color-text);
  background: transparent;
  transition: background 0.15s;
  text-align: left;
}

.action-btn:hover {
  background: var(--color-bg);
}

.action-btn--primary {
  color: var(--color-primary);
}

.action-btn--danger {
  color: var(--color-danger);
}

.action-chevron {
  margin-left: auto;
  color: var(--color-text-secondary);
}

.profile-empty {
  text-align: center;
  padding: 60px 20px;
  color: var(--color-text-secondary);
  font-size: 15px;
}

/* Desktop */
@media (min-width: 768px) {
  .profile-page {
    padding: 24px 20px 40px;
  }
  
  .profile-content {
    display: grid;
    grid-template-columns: 300px 1fr;
    gap: 16px;
    align-items: start;
  }
  
  .profile-card--avatar {
    grid-column: 1;
    flex-direction: column;
    text-align: center;
    padding: 28px 20px;
  }
  
  .avatar {
    width: 80px;
    height: 80px;
    font-size: 28px;
  }
  
  .profile-card:not(.profile-card--avatar) {
    grid-column: 2;
  }
}
</style>
