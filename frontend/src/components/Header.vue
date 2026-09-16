<template>
  <header class="header">
    <div class="header__mobile-top">
      <button
        class="header__menu-btn"
        data-testid="mobile-menu-btn"
        aria-label="Меню"
        @click="mobileMenuOpen = true"
      >
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="3" y1="6" x2="21" y2="6"/>
          <line x1="3" y1="12" x2="21" y2="12"/>
          <line x1="3" y1="18" x2="21" y2="18"/>
        </svg>
      </button>
      <div class="header__logo" data-testid="header-logo" @click="$router.push('/')">
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
          <rect width="28" height="28" rx="6" fill="var(--color-primary)"/>
          <path d="M15.5 5L8 15h5l-1.5 8L19 12h-5l1.5-7z" fill="#fff"/>
        </svg>
        <span class="header__logo-text">Пром<br />Электрон</span>
      </div>
      <router-link to="/cart" class="header__mobile-cart" data-testid="mobile-cart-link" aria-label="Корзина">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4H6z"/>
          <line x1="3" y1="6" x2="21" y2="6"/>
          <path d="M16 10a4 4 0 01-8 0"/>
        </svg>
        <span v-if="cartCount > 0" class="header__notif-badge">{{ cartCount > 99 ? '99+' : cartCount }}</span>
      </router-link>
    </div>

    <div class="header__left">
      <!-- Desktop: логотип + синяя кнопка «Каталог» (§11, D-09) -->
      <router-link to="/catalog" class="header__catalog-btn" data-testid="catalog-btn">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <line x1="3" y1="6" x2="21" y2="6"/>
          <line x1="3" y1="12" x2="21" y2="12"/>
          <line x1="3" y1="18" x2="21" y2="18"/>
        </svg>
        Каталог
      </router-link>
      <nav v-if="isSupplier" class="header__nav">
        <router-link to="/supplier-dashboard" class="header__nav-link" :class="{ 'header__nav-link--active': $route.path.startsWith('/supplier-dashboard') }">Дашборд</router-link>
        <router-link to="/my-products" class="header__nav-link" :class="{ 'header__nav-link--active': $route.path.startsWith('/my-products') }">Мои товары</router-link>
        <router-link to="/supplier-orders" class="header__nav-link" :class="{ 'header__nav-link--active': $route.path.startsWith('/supplier-orders') }">Мои заказы</router-link>
      </nav>
    </div>

    <div class="header__search-desktop">
      <SearchBar v-model="headerSearchQuery" data-testid="header-search-bar" @submit="onSearchSubmit" />
    </div>

    <div class="header__phone">
      <a class="header__phone-number" href="tel:88005004585">8 (800) 500-45-85</a>
      <span class="header__phone-hours">Ежедневно 9:00–21:00</span>
    </div>

    <div class="header__actions">
      <!-- Сравнение: функции нет — неактивный элемент с tooltip (D-09) -->
      <span
        class="header__action-item header__action-item--disabled"
        data-testid="compare-link"
        title="Сравнение скоро появится"
        aria-disabled="true"
      >
        <div class="header__icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M10 3H4a1 1 0 00-1 1v16a1 1 0 001 1h6"/>
            <path d="M14 21h6a1 1 0 001-1V4a1 1 0 00-1-1h-6"/>
            <line x1="12" y1="3" x2="12" y2="21"/>
          </svg>
        </div>
        <span class="header__action-label">Сравнение</span>
      </span>

      <!-- Notifications -->
      <div v-if="isAuthenticated" class="header__action-item header__notif-wrap">
        <button class="header__icon header__icon--notif" data-testid="notifications-btn" title="Уведомления" @click="toggleNotif">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
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
              <div class="notif-dropdown__item-time">{{ formatDateTime(n.created_at) }}</div>
            </div>
          </div>
          <router-link to="/notifications" class="notif-dropdown__footer" @click="closeNotif">Все уведомления</router-link>
        </div>
      </div>

      <router-link to="/orders" class="header__action-item">
        <div class="header__icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
        </div>
        <span class="header__action-label">Заказы</span>
      </router-link>

      <router-link to="/favorites" class="header__action-item">
        <div class="header__icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/>
          </svg>
          <span v-if="favoritesCount > 0" class="header__notif-badge">{{ favoritesCount > 99 ? '99+' : favoritesCount }}</span>
        </div>
        <span class="header__action-label">Избранное</span>
      </router-link>

      <router-link to="/cart" class="header__action-item" data-testid="cart-link">
        <div class="header__icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
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
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="8" r="4"/>
            <path d="M4 20c0-4 4-7 8-7s8 3 8 7"/>
          </svg>
        </div>
        <span class="header__action-label">Профиль</span>
      </router-link>

      <router-link v-else to="/login" class="header__action-item" data-testid="login-link">
        <div class="header__icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="8" r="4"/>
            <path d="M4 20c0-4 4-7 8-7s8 3 8 7"/>
          </svg>
        </div>
        <span class="header__action-label">Войти</span>
      </router-link>
    </div>

    <ToastContainer class="header__toast" />

    <div class="header__mobile-search">
      <SearchBar v-model="headerSearchQuery" data-testid="header-search-bar-mobile" @submit="onSearchSubmit" />
    </div>

    <MobileMenuDrawer :open="mobileMenuOpen" @close="mobileMenuOpen = false" />
  </header>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useAuth } from '@/composables/useAuth';
import { useCart } from '@/composables/useCart';
import { useNotifications } from '@/composables/useNotifications';
import { formatDateTime } from '@/utils/date';
import ToastContainer from '@/components/ToastContainer.vue';
import SearchBar from '@/components/SearchBar.vue';
import MobileMenuDrawer from '@/components/MobileMenuDrawer.vue';
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
const headerSearchQuery = ref('');
const mobileMenuOpen = ref(false);

const onSearchSubmit = (q) => {
  const query = (q || headerSearchQuery.value).trim();
  router.push({ path: '/catalog', query: query ? { q: query } : undefined });
};

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
  flex-wrap: wrap;
  background: var(--color-bg-white);
  position: sticky;
  top: 0;
  z-index: 100;
  border-bottom: 1px solid var(--color-border);
}

.header__mobile-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-height: 56px;
  padding: 0 16px;
}

.header__menu-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--color-text);
  cursor: pointer;
}

.header__menu-btn:hover {
  background: var(--color-bg);
}

.header__mobile-cart {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 8px;
  color: var(--color-text);
}

.header__mobile-cart:hover {
  background: var(--color-bg);
}

.header__mobile-search {
  width: 100%;
  padding: 0 16px 12px;
}

.header__left {
  display: flex;
  align-items: center;
  gap: 32px;
}

.header__logo {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
  flex-shrink: 0;
}

.header__logo-text {
  font-size: var(--font-size-body-sm);
  font-weight: var(--font-weight-bold);
  color: var(--color-text);
  line-height: 1.1;
}

.header__catalog-btn {
  display: none;
}

.header__phone {
  display: none;
}

.header__action-item--disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.header__action-item--disabled .header__icon:hover {
  background: transparent;
}

.header__nav {
  display: none;
}

@media (min-width: 1024px) {
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
  border-radius: var(--radius-pill);
  background: var(--color-danger);
  color: var(--color-white);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-semibold);
  line-height: 1;
  vertical-align: middle;
}

.header__actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

@media (max-width: 1023px) {
  .header__actions {
    display: none;
  }
}

.header__search-desktop {
  display: none;
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
  font-size: var(--font-size-caption);
  color: var(--color-text-muted);
  line-height: 1;
}

@media (min-width: 1024px) {
  .header {
    height: 72px;
    padding: 0 var(--space-4);
  }
  .header__mobile-top {
    display: contents;
  }
  .header__menu-btn,
  .header__mobile-cart,
  .header__mobile-search {
    display: none;
  }
  .header__left {
    margin-left: 32px;
    gap: var(--space-4);
  }
  .header__catalog-btn {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    height: 48px;
    padding: 0 var(--space-4);
    border-radius: var(--radius-md);
    background: var(--color-primary);
    color: var(--color-white);
    font-size: var(--font-size-body-sm);
    font-weight: var(--font-weight-medium);
    text-decoration: none;
    transition: background 0.15s;
  }
  .header__catalog-btn:hover {
    background: var(--color-primary-hover);
  }
  .header__search-desktop {
    display: block;
    flex: 1;
    max-width: 600px;
    margin: 0 24px;
  }
  .header__actions {
    gap: 20px;
  }
  .header__action-label {
    display: block;
  }
}

@media (min-width: 1280px) {
  .header__phone {
    display: flex;
    flex-direction: column;
    margin-right: var(--space-4);
    flex-shrink: 0;
  }
  .header__phone-number {
    font-size: var(--font-size-body-sm);
    font-weight: var(--font-weight-semibold);
    color: var(--color-text);
    text-decoration: none;
    white-space: nowrap;
  }
  .header__phone-hours {
    font-size: var(--font-size-caption);
    color: var(--color-text-secondary);
    white-space: nowrap;
  }
}

.header__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
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
  border-radius: var(--radius-pill);
  background: var(--color-danger);
  color: var(--color-white);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-semibold);
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
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-dropdown);
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
  background: var(--color-primary-light);
}

.notif-dropdown__item--unread:hover {
  background: color-mix(in srgb, var(--color-primary-light) 80%, var(--color-primary));
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
