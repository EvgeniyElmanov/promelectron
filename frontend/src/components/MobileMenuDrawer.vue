<template>
  <Teleport to="body">
    <div v-if="open" class="mobile-menu" data-testid="mobile-menu-drawer">
      <div class="mobile-menu__overlay" @click="$emit('close')"></div>
      <nav
        ref="drawerEl"
        class="mobile-menu__drawer"
        aria-label="Мобильное меню"
        tabindex="-1"
        @keydown.esc="$emit('close')"
      >
        <router-link to="/" class="mobile-menu__link" @click="$emit('close')">Каталог</router-link>
        <template v-if="isAuthenticated">
          <router-link to="/orders" class="mobile-menu__link" @click="$emit('close')">Заказы</router-link>
          <router-link to="/notifications" class="mobile-menu__link" @click="$emit('close')">Уведомления</router-link>
          <router-link to="/profile" class="mobile-menu__link" @click="$emit('close')">Профиль</router-link>
        </template>
        <router-link v-else to="/login" class="mobile-menu__link" @click="$emit('close')">Войти</router-link>
        <template v-if="isSupplier">
          <router-link to="/supplier-dashboard" class="mobile-menu__link" @click="$emit('close')">Дашборд</router-link>
          <router-link to="/my-products" class="mobile-menu__link" @click="$emit('close')">Мои товары</router-link>
          <router-link to="/supplier-orders" class="mobile-menu__link" @click="$emit('close')">Мои заказы</router-link>
        </template>
      </nav>
    </div>
  </Teleport>
</template>

<script setup>
/**
 * MobileMenuDrawer — мобильное меню шапки (§11, D-02).
 * Открывается из Header по mobile-menu-btn; закрывается по клику вне,
 * Escape и выбору пункта. Полный focus-trap — issue #225.
 */
import { ref, watch, nextTick } from 'vue';
import { useAuth } from '@/composables/useAuth';

const props = defineProps({
  open: { type: Boolean, default: false },
});

defineEmits(['close']);

const { isAuthenticated, isSupplier } = useAuth();

const drawerEl = ref(null);

watch(
  () => props.open,
  async (open) => {
    if (open) {
      await nextTick();
      drawerEl.value?.focus();
    }
  },
);
</script>

<style scoped>
.mobile-menu {
  position: fixed;
  inset: 0;
  z-index: 300;
}

.mobile-menu__overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
}

.mobile-menu__drawer {
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  width: 280px;
  max-width: 85vw;
  background: var(--color-bg-white);
  box-shadow: var(--shadow-dropdown);
  border-radius: 0 var(--radius-lg) var(--radius-lg) 0;
  padding: var(--space-3) 0;
  display: flex;
  flex-direction: column;
  outline: none;
  overflow-y: auto;
}

.mobile-menu__link {
  display: flex;
  align-items: center;
  min-height: 44px;
  padding: 0 var(--space-4);
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-medium);
  color: var(--color-text);
  text-decoration: none;
}

.mobile-menu__link:hover {
  background: var(--color-bg);
}

.mobile-menu__link.router-link-active {
  color: var(--color-primary);
  background: var(--color-primary-light);
}

@media (min-width: 768px) {
  .mobile-menu {
    display: none;
  }
}
</style>
