<template>
  <header class="header">
    <div class="header__left">
      <div class="header__logo" data-testid="header-logo" @click="$router.push('/')">MyShop</div>
      
      <!-- Desktop Navigation -->
      <nav class="header__nav" v-if="isDesktop">
        <router-link to="/" class="header__nav-link" :class="{ 'header__nav-link--active': $route.path === '/' }">Главная</router-link>
        <router-link to="/favorites" class="header__nav-link" :class="{ 'header__nav-link--active': $route.path.startsWith('/favorites') }">Избранное</router-link>
        <router-link to="/cart" class="header__nav-link" :class="{ 'header__nav-link--active': $route.path.startsWith('/cart') }">Корзина</router-link>
        <router-link to="/orders" class="header__nav-link" :class="{ 'header__nav-link--active': $route.path.startsWith('/orders') }">Заказы</router-link>
      </nav>
    </div>

    <div class="header__actions">
      <router-link to="/cart" class="header__icon" data-testid="cart-link" title="Корзина">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
          <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4H6z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <line x1="3" y1="6" x2="21" y2="6" stroke="currentColor" stroke-width="2"/>
          <path d="M16 10a4 4 0 01-8 0" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
      </router-link>
      <router-link v-if="isAuthenticated" to="/profile" class="header__icon" data-testid="profile-link" title="Профиль">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="8" r="4" stroke="currentColor" stroke-width="2"/>
          <path d="M4 20c0-4 4-7 8-7s8 3 8 7" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
      </router-link>
      <router-link v-else to="/login" class="header__icon" data-testid="login-link" title="Войти">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="8" r="4" stroke="currentColor" stroke-width="2"/>
          <path d="M4 20c0-4 4-7 8-7s8 3 8 7" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
      </router-link>
    </div>
  </header>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { useAuth } from '@/composables/useAuth';

const { isAuthenticated } = useAuth();
const isDesktop = ref(false);

const checkWidth = () => {
  isDesktop.value = window.innerWidth >= 768;
};

onMounted(() => {
  checkWidth();
  window.addEventListener('resize', checkWidth);
});

onUnmounted(() => {
  window.removeEventListener('resize', checkWidth);
});
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
  display: flex;
  align-items: center;
  gap: 4px;
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

.header__actions {
  display: flex;
  align-items: center;
  gap: 12px;
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
</style>
