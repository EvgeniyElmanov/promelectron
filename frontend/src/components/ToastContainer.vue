<template>
  <div class="toast-container">
    <TransitionGroup name="toast">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="toast"
        :class="`toast--${toast.type}`"
      >
        <span class="toast__message">{{ toast.message }}</span>
        <button class="toast__close" @click="remove(toast.id)">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { useToast } from '@/composables/useToast';

const { toasts, remove } = useToast();
</script>

<style scoped>
.toast-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 240px;
  width: auto;
}

@media (min-width: 768px) {
  .toast-container {
    max-width: 320px;
  }
}

.toast {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 12px;
  background: var(--color-bg-white);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  font-size: 14px;
  color: var(--color-text);
  animation: slideIn 0.3s ease;
}

.toast--success {
  border-left: 4px solid #34C759;
}

.toast--error {
  border-left: 4px solid var(--color-danger);
}

.toast--info {
  border-left: 4px solid var(--color-primary);
}

.toast__message {
  flex: 1;
  line-height: 1.4;
}

.toast__close {
  color: var(--color-text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2px;
  flex-shrink: 0;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(100%);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(100%);
}
</style>
