<template>
  <span class="app-badge" :class="`app-badge--${variant}`"><slot>{{ label }}</slot></span>
</template>

<script setup>
/**
 * AppBadge — переиспользуемый бейдж дизайн-системы (§15, D-03).
 *
 * Variants: sale / new / hit / in-stock / out-of-stock.
 * SALE/NEW/ХИТ — только варианты компонента; wiring к данным (is_new,
 * old_price) — отдельная backend-задача, out of scope.
 */
defineProps({
  variant: {
    type: String,
    default: 'out-of-stock',
    validator: (v) => ['sale', 'new', 'hit', 'in-stock', 'out-of-stock'].includes(v),
  },
  label: { type: String, default: '' },
});
</script>

<style scoped>
.app-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px var(--space-2);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-semibold);
  line-height: 1.3;
}

.app-badge--sale {
  background: var(--color-danger);
  color: var(--color-white);
}

.app-badge--out-of-stock {
  background: var(--color-surface-overlay);
  color: var(--color-danger);
}

.app-badge--in-stock {
  background: var(--color-success);
  color: var(--color-white);
}

.app-badge--new {
  background: var(--color-warning);
  color: var(--color-white);
}

.app-badge--hit {
  background: var(--color-primary);
  color: var(--color-white);
}
</style>
