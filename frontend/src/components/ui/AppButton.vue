<template>
  <button
    type="button"
    class="app-button"
    :class="[
      `app-button--${variant}`,
      `app-button--${size}`,
      { 'app-button--block': block, 'app-button--loading': loading },
    ]"
    :disabled="disabled || loading"
  >
    <slot />
  </button>
</template>

<script setup>
/**
 * AppButton — базовая кнопка дизайн-системы (§10, D-02).
 *
 * Props:
 *   - variant: 'primary' | 'secondary' | 'ghost'
 *   - size: 'md' (48px) | 'sm' (40px, для плотных мест вроде карточки товара)
 *   - loading: блокирует кнопку (вместе с disabled)
 *   - disabled
 *   - block: full-width (mobile CTA)
 *
 * `click` не объявлен в emits — listeners (включая @click.stop) проваливаются
 * на корневой <button> как нативные, чтобы .stop работал (карточка товара).
 */
defineProps({
  variant: {
    type: String,
    default: 'primary',
    validator: (v) => ['primary', 'secondary', 'ghost'].includes(v),
  },
  size: {
    type: String,
    default: 'md',
    validator: (v) => ['md', 'sm'].includes(v),
  },
  loading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  block: { type: Boolean, default: false },
});
</script>

<style scoped>
.app-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: 0 var(--space-4);
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-medium);
  font-family: inherit;
  cursor: pointer;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}

.app-button--md {
  height: 48px;
  padding: 0 var(--space-5);
}

.app-button--sm {
  height: 40px;
  font-size: var(--font-size-body-sm);
}

.app-button--block {
  width: 100%;
}

.app-button--primary {
  background: var(--color-primary);
  color: var(--color-white);
}

.app-button--primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.app-button--primary:active:not(:disabled) {
  background: var(--color-primary-hover);
}

.app-button--secondary {
  background: var(--color-bg-white);
  border: 1px solid var(--color-border);
  color: var(--color-text);
}

.app-button--secondary:hover:not(:disabled) {
  background: var(--color-bg);
}

.app-button--ghost {
  background: transparent;
  color: var(--color-primary);
}

.app-button--ghost:hover:not(:disabled) {
  background: var(--color-primary-light);
}

.app-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
