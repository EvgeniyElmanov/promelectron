<template>
  <header class="header">
    <div class="header__left">
      <div class="header__logo" data-testid="header-logo" @click="$router.push('/')">Promelectron</div>
      
      <!-- Desktop Navigation -->
      <nav class="header__nav">
        <router-link v-if="isSupplier" to="/supplier-dashboard" class="header__nav-link" :class="{ 'header__nav-link--active': $route.path.startsWith('/supplier-dashboard') }">Дашборд</router-link>
        <router-link v-if="isSupplier" to="/my-products" class="header__nav-link" :class="{ 'header__nav-link--active': $route.path.startsWith('/my-products') }">Мои товары</router-link>
        <router-link v-if="isSupplier" to="/supplier-orders" class="header__nav-link" :class="{ 'header__nav-link--active': $route.path.startsWith('/supplier-orders') }">Мои заказы</router-link>
      </nav>
    </div>

    <div class="header__actions">
      <!-- Notifications -->
      <div v-if="isAuthenticated" class="header__action-item header__notif-wrap">
        <button class="header__icon header__icon--notif" data-testid="notifications-btn" title="Уведомления" @click="toggleNotif">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/>
            <path d="M13.73 21a2 2 0 01-3.46 0"/>
          </svg>
          <span v-if="unreadCount > 0" class="header__notif-badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
        </button>
        <span class="header__action-label">Уведомления</span>
        <!-- Dropdown -->
        <div v-if="notifOpen" class="notif-dropdown" v-click-outside="closeNotif">
          <div class="notif-dropdown__header">
            <span class="notif-dropdown__title">Уведомления</span>
            <button v-if="unreadCount > 0" class="notif-dropdown__read-all" @click="markAllAsRead">Прочитать все</button>
          </div>
          <div v-if="unreadNotifications.length === 0" class="notif-dropdown__empty">Нет новых уведомлений</div>
          <div v-else class="notif-dropdown__list">
            <div
              v-for="n in unreadNotifications.slice(0, 5)"
              :key="n.id"
              class="notif-dropdown__item notif-dropdown__item--unread"
              @click="onNotifClick(n)"
            >
              <div class="notif-dropdown__item-title">{{ n.title }}</div>
              <div class="notif-dropdown__item-msg">{{ n.message }}</div>
              <div class="notif-dropdown__item-time">{{ formatTime(n.created_at) }}</div>
            </div>
          </div>
          <router-link to="/notifications" class="notif-dropdown__footer" @click="closeNotif">Все уведомления</router-link>
        </div>
      </div>

      <router-link to="/orders" class="header__action-item">
        <div class="header__icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
        </div>
        <span class="header__action-label">Заказы</span>
      </router-link>

      <router-link to="/favorites" class="header__action-item">
        <div class="header__icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/>
          </svg>
          <span v-if="favoritesCount > 0" class="header__notif-badge">{{ favoritesCount > 99 ? '99+' : favoritesCount }}</span>
        </div>
        <span class="header__action-label">Избранное</span>
      </router-link>

      <router-link to="/cart" class="header__action-item" data-testid="cart-link">
        <div class="header__icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4H6z"/>
            <line x1="3" y1="6" x2="21" y2="6"/>
            <path d="M16 10a4 4 0 01-8 0"/>
          </svg>
          <span v-if="cartCount > 0" class="header__notif-badge">{{ cartCount > 99 ? '99+' : cartCount }}</span>
        </div>
        <span class="header__action-label">Корзина</span>
      </router-link>

      <router-link v-if="isAuthenticated" to="/profile" class="header__action-item" data-testid="profile-link">
        <div class="header__icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="8" r="4"/>
            <path d="M4 20c0-4 4-7 8-7s8 3 8 7"/>
          </svg>
        </div>
        <span class="header__action-label">Профиль</span>
      </router-link>

      <router-link v-else to="/login" class="header__action-item" data-testid="login-link">
        <div class="header__icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="8" r="4"/>
            <path d="M4 20c0-4 4-7 8-7s8 3 8 7"/>
          </svg>
        </div>
        <span class="header__action-label">Войти</span>
      </router-link>
    </div>
    <ToastContainer class="header__toast" />
  </header>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useAuth } from '@/composables/useAuth';
import { useCart } from '@/composables/useCart';
import { useNotifications } from '@/composables/useNotifications';
import ToastContainer from '@/components/ToastContainer.vue';
import api from '@/services/api';

const { isAuthenticated, isSupplier } = useAuth();
const { cartCount } = useCart();
const favoritesCount = ref(0);

const fetchFavoritesCount = async () => {
  if (!isAuthenticated.value) {
    favoritesCount.value = 0;
    return;
  }
  try {
    const { data } = await api.get('/favorites/');
    favoritesCount.value = Array.isArray(data) ? data.length : 0;
  } catch {
    favoritesCount.value = 0;
  }
};

onMounted(fetchFavoritesCount);
watch(isAuthenticated, fetchFavoritesCount);
const notifOpen = ref(false);
const router = useRouter();

// Always call useNotifications — it handles auth internally
const notifApi = useNotifications();
const notifications = computed(() => notifApi.notifications.value);
const unreadCount = computed(() => notifApi.unreadCount.value);
const unreadNotifications = computed(() => notifications.value.filter((n) => !n.is_read));

function toggleNotif(e) {
  e.stopPropagation();
  notifOpen.value = !notifOpen.value;
}

function closeNotif() {
  notifOpen.value = false;
}

function markAllAsRead() {
  notifApi.markAllAsRead?.();
}

function onNotifClick(n) {
  if (!n.is_read) {
    notifApi.markAsRead?.(n.id);
  }
  closeNotif();
  if (n.order_id) {
    router.push(`/orders/${n.order_id}`);
  }
}

function formatTime(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
}

// Simple click-outside directive (captures, so it runs before bubble)
const vClickOutside = {
  mounted(el, binding) {
    el._clickOutside = (e) => {
      if (!el.contains(e.target) && !el.previousElementSibling?.contains(e.target)) {
        binding.value();
      }
    };
    document.addEventListener('click', el._clickOutside);
  },
  unmounted(el) {
    document.removeEventListener('click', el._clickOutside);
  },
};
</script>

<style scoped>
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  background: var(--color-bg-white);
  position: sticky;
  top: 0;
  z-index: 100;
  border-bottom: 1px solid var(--color-border);
}

.header__left {
  display: flex;
  align-items: center;
  gap: 32px;
}

.header__logo {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-primary);
  cursor: pointer;
  letter-spacing: -0.5px;
  flex-shrink: 0;
}

.header__nav {
  display: none;
}

@media (min-width: 768px) {
  .header__nav {
    display: flex;
    align-items: center;
    gap: 4px;
  }
}

.header__nav-link {
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text);
  transition: background 0.15s, color 0.15s;
}

.header__nav-link:hover {
  background: var(--color-bg);
}

.header__nav-link--active {
  color: var(--color-primary);
  background: var(--color-primary-light);
}

.header__nav-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  margin-left: 6px;
  border-radius: 9px;
  background: var(--color-danger);
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  line-height: 1;
  vertical-align: middle;
}

.header__actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header__action-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  text-decoration: none;
  color: inherit;
}

.header__action-label {
  display: none;
  font-size: 12px;
  color: #999;
  line-height: 1;
}

@media (min-width: 768px) {
  .header__actions {
    gap: 20px;
  }
  .header__action-label {
    display: block;
  }
}

.header__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  color: var(--color-text);
  transition: background 0.15s;
}

.header__icon:hover {
  background: var(--color-bg);
}

.header__icon--notif {
  position: relative;
}

.header__notif-badge {
  position: absolute;
  top: -2px;
  right: -2px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 9px;
  background: var(--color-danger);
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}

.header__notif-wrap {
  position: relative;
}

.notif-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 320px;
  max-height: 400px;
  background: var(--color-bg-white);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.12);
  z-index: 150;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.notif-dropdown__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid var(--color-border);
}

.notif-dropdown__title {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
}

.notif-dropdown__read-all {
  font-size: 12px;
  color: var(--color-primary);
  background: none;
  border: none;
  cursor: pointer;
  font-weight: 500;
}

.notif-dropdown__list {
  overflow-y: auto;
  flex: 1;
}

.notif-dropdown__empty {
  padding: 24px;
  text-align: center;
  color: var(--color-text-secondary);
  font-size: 14px;
}

.notif-dropdown__item {
  padding: 12px 16px;
  border-bottom: 1px solid var(--color-border);
  cursor: pointer;
  transition: background 0.15s;
}

.notif-dropdown__item:hover {
  background: var(--color-bg);
}

.notif-dropdown__item--unread {
  background: #f0f7ff;
}

.notif-dropdown__item--unread:hover {
  background: #e0efff;
}

.notif-dropdown__item-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 2px;
}

.notif-dropdown__item-msg {
  font-size: 12px;
  color: var(--color-text-secondary);
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.notif-dropdown__item-time {
  font-size: 11px;
  color: var(--color-text-secondary);
  margin-top: 4px;
}

.notif-dropdown__footer {
  padding: 12px;
  text-align: center;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-primary);
  text-decoration: none;
  border-top: 1px solid var(--color-border);
}

.header__toast {
  position: absolute;
  top: calc(100% + 8px);
  right: 12px;
  z-index: 200;
}
</style>
