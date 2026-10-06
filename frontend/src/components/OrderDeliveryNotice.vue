<template>
  <div
    v-if="notice"
    class="delivery-notice"
    :class="`delivery-notice--${notice.type}`"
    role="alert"
    :data-testid="notice.type === 'price-update' ? 'delivery-price-update-notice' : 'delivery-unavailable-notice'"
  >
    <template v-if="notice.type === 'price-update'">
      <p class="delivery-notice__text">
        Стоимость доставки изменилась:
        <strong>{{ formatPrice(notice.oldPrice) }} ₽ → {{ formatPrice(notice.newPrice) }} ₽</strong>
      </p>
      <p class="delivery-notice__hint">Проверьте новую цену и подтвердите заказ.</p>
      <div class="delivery-notice__actions">
        <AppButton
          variant="primary"
          size="sm"
          data-testid="delivery-price-update-confirm"
          @click="$emit('confirm')"
        >
          Оформить по новой цене
        </AppButton>
        <AppButton
          variant="secondary"
          size="sm"
          data-testid="delivery-notice-dismiss"
          @click="$emit('dismiss')"
        >
          Отмена
        </AppButton>
      </div>
    </template>

    <template v-else>
      <p class="delivery-notice__text">
        Сервис доставки временно недоступен. Попробуйте повторить позже.
      </p>
      <div class="delivery-notice__actions">
        <AppButton
          variant="primary"
          size="sm"
          data-testid="delivery-unavailable-retry"
          @click="$emit('confirm')"
        >
          Повторить
        </AppButton>
        <AppButton
          variant="secondary"
          size="sm"
          data-testid="delivery-notice-dismiss"
          @click="$emit('dismiss')"
        >
          Отмена
        </AppButton>
      </div>
    </template>
  </div>
</template>

<script setup>
import AppButton from '@/components/ui/AppButton.vue';
import { formatPrice } from '@/utils/price';

defineProps({
  notice: { type: Object, default: null },
});

defineEmits(['confirm', 'dismiss']);
</script>

<style scoped>
.delivery-notice {
  padding: 12px 16px;
  border-radius: var(--radius-md, 8px);
  border: 1px solid var(--color-warning, #d97706);
  background: var(--color-warning-bg, #fffbeb);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.delivery-notice--unavailable {
  border-color: var(--color-error, #dc2626);
  background: var(--color-error-bg, #fef2f2);
}

.delivery-notice__text {
  margin: 0;
  font-size: 14px;
  color: var(--color-text);
}

.delivery-notice__hint {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-secondary, #6b7280);
}

.delivery-notice__actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
