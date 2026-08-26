<template>
  <div class="order-detail" data-testid="order-detail-page">
    <!-- Header -->
    <div class="order-detail__header">
      <button class="order-detail__back" @click="$router.back()">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M15 18l-6-6 6-6"/>
        </svg>
      </button>
      <h1 class="order-detail__title">Заказ №{{ orderId }}</h1>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="order-detail__loading">
      <div class="spinner"></div>
      <span>Загрузка заказа...</span>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="order-detail__error">
      <p>{{ error }}</p>
      <button @click="fetchOrder" class="retry-btn">Повторить</button>
    </div>

    <!-- Content -->
    <div v-else-if="order" class="order-detail__content">
      <!-- Status Timeline -->
      <div class="order-detail__card">
        <h2 class="order-detail__section-title">Статус заказа</h2>
        <div class="timeline">
          <div
            v-for="(step, idx) in statusSteps"
            :key="step.value"
            class="timeline__step"
            :class="{
              'timeline__step--completed': isStepCompleted(step.value),
              'timeline__step--current': order.status === step.value,
            }"
          >
            <div class="timeline__dot">
              <svg v-if="isStepCompleted(step.value) && order.status !== step.value" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
              <span v-else class="timeline__dot-inner"></span>
            </div>
            <div class="timeline__info">
              <span class="timeline__label">{{ step.label }}</span>
              <span v-if="order.status === step.value" class="timeline__current">Текущий статус</span>
            </div>
            <div v-if="idx < statusSteps.length - 1" class="timeline__line" />
          </div>
        </div>
      </div>

      <!-- Order Info -->
      <div class="order-detail__card">
        <h2 class="order-detail__section-title">Информация о заказе</h2>
        <div class="info-list">
          <div class="info-row">
            <span class="info-label">Номер заказа</span>
            <span class="info-value">№{{ order.id }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Дата создания</span>
            <span class="info-value">{{ formatDate(order.created_at) }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Статус</span>
            <span class="info-value">
              <span class="status-badge" :class="'status-badge--' + order.status">{{ statusLabel }}</span>
            </span>
          </div>
          <div v-if="order.shipping_address" class="info-row">
            <span class="info-label">Адрес доставки</span>
            <span class="info-value">{{ order.shipping_address }}</span>
          </div>
          <div v-if="order.delivery_method" class="info-row">
            <span class="info-label">Способ доставки</span>
            <span class="info-value">
              {{ order.delivery_method.name }}
              <span v-if="order.delivery_method.estimated_days" class="delivery-days">
                ({{ order.delivery_method.estimated_days }} {{ order.delivery_method.estimated_days === 1 ? 'день' : order.delivery_method.estimated_days < 5 ? 'дня' : 'дней' }})
              </span>
            </span>
          </div>
          <div v-if="order.delivery_price !== null && order.delivery_price !== undefined" class="info-row">
            <span class="info-label">Стоимость доставки</span>
            <span class="info-value">{{ Number(order.delivery_price) > 0 ? formatPrice(order.delivery_price) + ' ₽' : 'Бесплатно' }}</span>
          </div>
          <div v-if="order.tracking_number" class="info-row">
            <span class="info-label">Трек-номер</span>
            <span class="info-value">{{ order.tracking_number }}</span>
          </div>
          <div v-if="canCancel" class="info-row info-row--action">
            <router-link v-if="order.status === 'pending'" :to="`/checkout/${order.id}`" class="order-pay-btn">
              Оплатить {{ formatPrice(order.total_price) }} ₽
            </router-link>
            <button class="order-cancel-btn" data-testid="order-cancel-btn" @click="handleCancelOrder">
              Отменить заказ
            </button>
          </div>
        </div>
      </div>

      <!-- CDEK Delivery -->
      <div v-if="order.cdek_order" class="order-detail__card" data-testid="cdek-order-card">
        <h2 class="order-detail__section-title">Доставка CDEK</h2>
        <div class="info-list">
          <div class="info-row">
            <span class="info-label">Статус CDEK</span>
            <span class="info-value">
              <span class="status-badge" :class="cdekStatusClass">
                {{ order.cdek_order.cdek_status_name || order.cdek_order.cdek_status }}
              </span>
            </span>
          </div>
          <div v-if="order.cdek_order.tracking_number" class="info-row">
            <span class="info-label">Трек-номер</span>
            <span class="info-value">{{ order.cdek_order.tracking_number }}</span>
          </div>
          <div v-if="order.cdek_order.tracking_url" class="info-row">
            <span class="info-label">Отследить</span>
            <a
              :href="order.cdek_order.tracking_url"
              target="_blank"
              rel="noopener noreferrer"
              class="order-cdek-track-link"
              data-testid="cdek-tracking-link"
            >
              Перейти к отслеживанию
            </a>
          </div>
        </div>

        <div v-if="cdekStatusHistory.length" class="cdek-history" data-testid="cdek-status-history">
          <h3 class="cdek-history__title">История статусов</h3>
          <div class="timeline">
            <div
              v-for="(entry, idx) in cdekStatusHistory"
              :key="entry.id"
              class="timeline__step"
              :class="{ 'timeline__step--current': idx === 0 }"
            >
              <div class="timeline__dot">
                <span class="timeline__dot-inner"></span>
              </div>
              <div class="timeline__info">
                <span class="timeline__label">{{ entry.cdek_status_name || entry.cdek_status }}</span>
                <span v-if="entry.status_date_time" class="timeline__current">{{ formatDate(entry.status_date_time) }}</span>
                <span v-if="entry.city" class="timeline__current">{{ entry.city }}</span>
              </div>
              <div v-if="idx < cdekStatusHistory.length - 1" class="timeline__line" />
            </div>
          </div>
        </div>
      </div>

      <!-- Items -->
      <div class="order-detail__card">
        <h2 class="order-detail__section-title">Товары ({{ order.items.length }})</h2>
        <div class="order-items">
          <div v-for="item in order.items" :key="item.id" class="order-item">
            <div class="order-item__info">
              <span class="order-item__name">{{ item.product?.name || 'Товар' }}</span>
              <span class="order-item__meta">{{ item.quantity }} шт. × {{ formatPrice(item.price_at_time) }} ₽</span>
            </div>
            <span class="order-item__total">{{ formatPrice(item.price_at_time * item.quantity) }} ₽</span>
          </div>
        </div>
        <div class="order-detail__total">
          <span>Итого</span>
          <span>{{ formatPrice(order.total_price) }} ₽</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRoute } from 'vue-router';
import api from '@/services/api';
import { formatDate } from '@/utils/date';
import { useToast } from '@/composables/useToast';
import { cancelOrder } from '@/api/orders';

const route = useRoute();
const { add: toast } = useToast();

const orderId = computed(() => Number(route.params.id));
const order = ref(null);
const loading = ref(true);
const error = ref(null);

const statusSteps = [
  { value: 'pending', label: 'Ожидает оплаты' },
  { value: 'paid', label: 'Оплачен' },
  { value: 'shipped', label: 'Отправлен' },
  { value: 'delivered', label: 'Доставлен' },
];

const statusLabels = {
  pending: 'Ожидает оплаты',
  paid: 'Оплачен',
  shipped: 'Отправлен',
  delivered: 'Доставлен',
  cancelled: 'Отменён',
};

const statusLabel = computed(() => statusLabels[order.value?.status] || order.value?.status);

const canCancel = computed(() => ['pending', 'paid'].includes(order.value?.status));

const cdekStatusHistory = computed(() => {
  const history = order.value?.cdek_order?.status_history || [];
  return [...history].sort((a, b) => {
    if (!a.status_date_time) return 1;
    if (!b.status_date_time) return -1;
    return new Date(b.status_date_time) - new Date(a.status_date_time);
  });
});

const cdekStatusClass = computed(() => {
  const status = order.value?.cdek_order?.cdek_status;
  if (!status) return 'status-badge--shipped';
  const statusLower = status.toLowerCase();
  if (statusLower.includes('cancel') || statusLower.includes('return') || statusLower.includes('not_delivered')) {
    return 'status-badge--cancelled';
  }
  if (statusLower.includes('delivered')) {
    return 'status-badge--delivered';
  }
  if (statusLower.includes('created') || statusLower.includes('accepted_at_shipment')) {
    return 'status-badge--pending';
  }
  // In transit / out for delivery / warehouse statuses
  return 'status-badge--shipped';
});

const isStepCompleted = (stepValue) => {
  const stepOrder = ['pending', 'paid', 'shipped', 'delivered'];
  const currentIdx = stepOrder.indexOf(order.value?.status);
  const stepIdx = stepOrder.indexOf(stepValue);
  return stepIdx <= currentIdx && currentIdx >= 0;
};

const formatPrice = (price) => {
  return Number(price).toLocaleString('ru-RU');
};

const fetchOrder = async () => {
  loading.value = true;
  error.value = null;
  try {
    const response = await api.get(`/orders/${orderId.value}`);
    order.value = response.data;
  } catch (err) {
    error.value = err.response?.data?.detail || 'Не удалось загрузить заказ';
    toast(error.value, 'error');
  } finally {
    loading.value = false;
  }
};

const handleCancelOrder = async () => {
  let message = 'Отменить заказ?';
  if (order.value?.status === 'paid') {
    message = 'Заказ уже оплачен. При отмене деньги будут автоматически возвращены на ваш счёт в течение нескольких рабочих дней. Отменить заказ?';
  }
  if (!confirm(message)) return;
  try {
    const response = await cancelOrder(orderId.value);
    order.value = response.data;
    toast('Заказ отменён', 'info');
  } catch (err) {
    toast(err.response?.data?.detail || 'Не удалось отменить заказ', 'error');
  }
};

onMounted(fetchOrder);
</script>

<style scoped>
.order-detail {
  max-width: 800px;
  margin: 0 auto;
  padding: 12px 12px calc(20px + var(--bottom-nav-height, 56px) + env(safe-area-inset-bottom, 0px));
}

@media (min-width: 768px) {
  .order-detail {
    padding: 20px 20px 40px;
  }
}

.order-detail__header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0 16px;
}

.order-detail__back {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  color: var(--color-text);
  flex-shrink: 0;
}

@media (max-width: 767px) {
  .order-detail__back {
    min-width: 40px;
    min-height: 40px;
  }
}

.order-detail__title {
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text);
}

.order-detail__loading,
.order-detail__error {
  text-align: center;
  padding: 60px 20px;
  color: var(--color-text-secondary);
}

.order-detail__loading .spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 12px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.order-detail__content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.order-detail__card {
  background: var(--color-bg-white);
  border-radius: 14px;
  padding: 16px;
}

.order-detail__section-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 14px;
}

/* Timeline */
.timeline {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.timeline__step {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding-bottom: 20px;
}

.timeline__step:last-child {
  padding-bottom: 0;
}

.timeline__dot {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--color-bg);
  border: 2px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-secondary);
  flex-shrink: 0;
  z-index: 1;
}

.timeline__step--completed .timeline__dot {
  background: #e6f7ed;
  border-color: #0d7a3e;
  color: #0d7a3e;
}

.timeline__step--current .timeline__dot {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: #fff;
}

.timeline__dot-inner {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}

.timeline__info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-top: 2px;
}

.timeline__label {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-secondary);
}

.timeline__step--completed .timeline__label,
.timeline__step--current .timeline__label {
  color: var(--color-text);
  font-weight: 600;
}

.timeline__current {
  font-size: 12px;
  color: var(--color-primary);
  font-weight: 500;
}

.timeline__line {
  position: absolute;
  left: 11px;
  top: 24px;
  bottom: 0;
  width: 2px;
  background: var(--color-border);
}

.timeline__step--completed .timeline__line {
  background: #0d7a3e;
}

/* Info List */
.info-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.info-label {
  font-size: 14px;
  color: var(--color-text-secondary);
}

.info-value {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text);
  text-align: right;
}

.status-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge--pending {
  background: #fff8e1;
  color: #b28704;
}

.status-badge--paid {
  background: #e8f0fe;
  color: #005bff;
}

.status-badge--shipped {
  background: #e3f2fd;
  color: #0066cc;
}

.status-badge--delivered {
  background: #e6f7ed;
  color: #0d7a3e;
}

.status-badge--cancelled {
  background: #fff0f0;
  color: var(--color-danger);
}

.info-row--action {
  margin-top: 12px;
  justify-content: flex-end;
}

.order-pay-btn {
  display: inline-block;
  padding: 12px 24px;
  border-radius: 12px;
  background: var(--color-primary);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  text-decoration: none;
  text-align: center;
}

.order-cancel-btn {
  display: inline-block;
  padding: 12px 24px;
  border-radius: 12px;
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 15px;
  font-weight: 500;
  border: 1px solid var(--color-border);
  cursor: pointer;
  text-align: center;
}

.order-cancel-btn:hover {
  background: #fff0f0;
  color: var(--color-danger);
  border-color: #ffcdd2;
}

/* Items */
.order-items {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.order-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--color-border);
}

.order-item:last-child {
  border-bottom: none;
}

.order-item__info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.order-item__name {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text);
}

.order-item__meta {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.order-item__total {
  font-size: 15px;
  font-weight: 700;
  color: var(--color-text);
  flex-shrink: 0;
}

.order-detail__total {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border);
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text);
}

.delivery-days {
  color: var(--color-text-secondary);
  font-size: 13px;
}

.cdek-history {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--color-border);
}

.cdek-history__title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 12px;
}

.order-cdek-track-link {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-primary);
  text-decoration: none;
}

.order-cdek-track-link:hover {
  text-decoration: underline;
}
</style>
