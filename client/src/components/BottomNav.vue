<template>
  <nav class="bottom-nav">
    <router-link
      v-for="item in navItems"
      :key="item.to"
      :to="item.to"
      class="bottom-nav__item"
      :class="{ 'bottom-nav__item--active': isActive(item.to) }"
      :data-testid="'nav-' + item.label"
    >
      <span class="bottom-nav__icon" v-html="item.icon"></span>
      <span class="bottom-nav__label">{{ item.label }}</span>
    </router-link>
  </nav>
</template>

<script setup>
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import { useAuth } from '@/composables/useAuth';

const route = useRoute();

const baseNavItems = [
  {
    to: '/',
    label: 'Главная',
    icon: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <path d="M3 12l9-9 9 9" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M5 10v10a1 1 0 001 1h4v-4a2 2 0 014 0v4h4a1 1 0 001-1V10" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`,
  },
  {
    to: '/favorites',
    label: 'Избранное',
    icon: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>`,
  },
  {
    to: '/cart',
    label: 'Корзина',
    icon: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4H6z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      <line x1="3" y1="6" x2="21" y2="6" stroke="currentColor" stroke-width="2"/>
      <path d="M16 10a4 4 0 01-8 0" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    </svg>`,
  },
  {
    to: '/profile',
    label: 'Профиль',
    icon: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="8" r="4" stroke="currentColor" stroke-width="2"/>
      <path d="M4 20c0-4 4-7 8-7s8 3 8 7" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    </svg>`,
  },
];

const navItems = computed(() => {
  return baseNavItems;
});

const isActive = (to) => {
  if (to === '/') return route.path === '/';
  return route.path.startsWith(to);
};
</script>

<style scoped>
.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: 480px;
  height: var(--bottom-nav-height);
  background: var(--color-bg-white);
  border-top: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: space-around;
  z-index: 100;
  padding-bottom: env(safe-area-inset-bottom);
}

.bottom-nav__item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  color: #999;
  transition: color 0.15s;
  padding: 4px 12px;
}

.bottom-nav__item--active {
  color: var(--color-primary);
}

.bottom-nav__icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.bottom-nav__label {
  font-size: 11px;
  line-height: 1;
}

/* Hide on desktop */
@media (min-width: 768px) {
  .bottom-nav {
    display: none;
  }
}
</style>
