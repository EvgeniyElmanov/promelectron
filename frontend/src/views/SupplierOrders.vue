<template>
  <div class="supplier-orders" data-testid="supplier-orders-page">
    <h1 class="supplier-orders__title">Мои заказы</h1>

    <div v-if="loading" class="supplier-orders__list">
      <div class="supplier-order-card supplier-order-card--skeleton" v-for="i in 3" :key="'sk' + i">
        <div style="width: 100%; height: 60px; border-radius: 14px; background: linear-gradient(90deg, var(--color-bg) 25%, #e8ecf1 50%, var(--color-bg) 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite;" />
      </div>
    </div>

    <div v-else-if="error" class="supplier-orders__error">
      <p>Ошибка загрузки: {{ error }}</p>
      <button class="supplier-orders__retry" @click="fetchOrders">Повторить</button>
    </div>

    <div v-else-if="orders.length === 0" class="supplier-orders__empty">
      <p>У вас пока нет заказов.</p>
    </div>

    <div v-else class="supplier-orders__list">
      <div
        v-for="order in orders"
        :key="order.id"
        class="supplier-order-card"
        data-testid="supplier-order-card"
      >
        <div class="supplier-order-card__header">
          <div class="supplier-order-card__meta">
            <span class="supplier-order-card__id">Заказ №{{ order.id }}</span>
            <span class="supplier-order-card__date">{{ formatDate(order.created_at) }}</span>
          </div>
          <span class="status-badge" :class="'status-badge--' + order.status">{{ statusLabel(order.status) }}</span>
        </div>

        <div class="supplier-order-card__body">
          <div class="supplier-order-card__row">
            <span class="supplier-order-card__label">Покупатель</span>
            <span class="supplier-order-card__value">{{ order.buyer_name || order.buyer_email }}</span>
          </div>
          <div class="supplier-order-card__row">
            <span class="supplier-order-card__label">Email</span>
            <span class="supplier-order-card__value">{{ order.buyer_email }}</span>
          </div>
          <div class="supplier-order-card__row">
            <span class="supplier-order-card__label">Сумма</span>
            <span class="supplier-order-card__value supplier-order-card__value--price">{{ Number(order.total_amount).toLocaleString('ru-RU') }} ₽</span>
          </div>
        </div>

        <div class="supplier-order-card__items">
          <button class="supplier-order-card__items-toggle" @click="toggleItems(order.id)">
            {{ expandedOrders.has(order.id) ? 'Скрыть товары' : 'Показать товары' }}
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              :style="{ transform: expandedOrders.has(order.id) ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }"
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>

          <div v-if="expandedOrders.has(order.id)" class="supplier-order-card__items-list" data-testid="order-items">
            <div
              v-for="(item, idx) in order.items"
              :key="idx"
              class="supplier-order-card__item"
            >
              <span class="supplier-order-card__item-name">{{ item.product_name }}</span>
              <span class="supplier-order-card__item-qty">{{ item.quantity }} шт.</span>
              <span class="supplier-order-card__item-price">{{ Number(item.price).toLocaleString('ru-RU') }} ₽</span>
            </div>
          </div>
        </div>

        <div v-if="order.status === 'pending'" class="supplier-order-card__actions">
          <button
            class="supplier-order-card__ship-btn"
            :disabled="shippingOrderId === order.id"
            @click="shipOrder(order.id)"
            data-testid="ship-order-btn"
          >
            {{ shippingOrderId === order.id ? 'Отправка...' : 'Отметить отправленным' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import api from '@/services/api';
import { useToast } from '@/composables/useToast';

const orders = ref([]);
const loading = ref(true);
const error = ref(null);
const expandedOrders = ref(new Set());
const shippingOrderId = ref(null);
const { add: toast } = useToast();

const statusLabel = (status) => {
  const labels = {
    pending: 'Ожидает отправки',
    shipped: 'Отправлен',
    delivered: 'Доставлен',
    cancelled: 'Отменён',
  };
  return labels[status] || status;
};

const formatDate = (dateString) => {
  if (!dateString) return '';
  return new Date(dateString).toLocaleDateString('ru-RU', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const fetchOrders = async () => {
  loading.value = true;
  error.value = null;
  try {
    const response = await api.get('/orders/supplier/');
    orders.value = response.data;
  } catch (err) {
    console.error('Ошибка загрузки заказов:', err);
    error.value = err.response?.data?.detail || err.message || 'Не удалось загрузить заказы';
  } finally {
    loading.value = false;
  }
};

const toggleItems = (orderId) => {
  const newSet = new Set(expandedOrders.value);
  if (newSet.has(orderId)) {
    newSet.delete(orderId);
  } else {
    newSet.add(orderId);
  }
  expandedOrders.value = newSet;
};

const shipOrder = async (orderId) => {
  shippingOrderId.value = orderId;
  try {
    await api.patch(`/orders/supplier/${orderId}/ship`);
    toast('Заказ отмечен как отправленный', 'success');
    await fetchOrders();
  } catch (err) {
    toast(err.response?.data?.detail || 'Не удалось отметить заказ как отправленный', 'error');
  } finally {
    shippingOrderId.value = null;
  }
};

onMounted(fetchOrders);
</script>

<style scoped>
.supplier-orders {
  padding: 16px;
  min-height: 100vh;
  background: var(--color-bg);
  max-width: 800px;
  margin: 0 auto;
}

@media (min-width: 768px) {
  .supplier-orders {
    padding: 24px;
  }
}

.supplier-orders__title {
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 16px;
}

.supplier-orders__list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.supplier-orders__error {
  text-align: center;
  padding: 24px;
  color: #e53e3e;
  background-color: #fff5f5;
  border: 1px solid #feb2b2;
  border-radius: 12px;
}

.supplier-orders__retry {
  margin-top: 12px;
  padding: 10px 20px;
  border-radius: 12px;
  background: var(--color-primary);
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  border: none;
  cursor: pointer;
}

.supplier-orders__empty {
  text-align: center;
  padding: 40px 20px;
  color: var(--color-text-secondary);
}

.supplier-order-card {
  background: var(--color-bg-white);
  border-radius: 14px;
  padding: 16px;
  transition: box-shadow 0.2s;
}

.supplier-order-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
}

.supplier-order-card__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--color-border);
}

.supplier-order-card__meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.supplier-order-card__id {
  font-weight: 700;
  font-size: 16px;
  color: var(--color-text);
}

.supplier-order-card__date {
  color: var(--color-text-secondary);
  font-size: 13px;
}

.status-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
}

.status-badge--pending {
  background: #fff8e1;
  color: #b28704;
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

.supplier-order-card__body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.supplier-order-card__row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.supplier-order-card__label {
  font-size: 14px;
  color: var(--color-text-secondary);
}

.supplier-order-card__value {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text);
}

.supplier-order-card__value--price {
  color: var(--color-primary);
  font-weight: 600;
}

.supplier-order-card__items {
  margin-bottom: 12px;
}

.supplier-order-card__items-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  padding: 8px;
  border-radius: 10px;
  background: var(--color-bg);
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 500;
  border: none;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.supplier-order-card__items-toggle:hover {
  background: #e8ecf1;
  color: var(--color-text);
}

.supplier-order-card__items-list {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.supplier-order-card__item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: var(--color-bg);
  border-radius: 10px;
  font-size: 13px;
}

.supplier-order-card__item-name {
  flex: 1;
  font-weight: 500;
  color: var(--color-text);
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.supplier-order-card__item-qty {
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.supplier-order-card__item-price {
  font-weight: 600;
  color: var(--color-text);
  flex-shrink: 0;
  min-width: 60px;
  text-align: right;
}

.supplier-order-card__actions {
  padding-top: 12px;
  border-top: 1px solid var(--color-border);
  display: flex;
  justify-content: flex-end;
}

.supplier-order-card__ship-btn {
  padding: 10px 20px;
  border-radius: 12px;
  background: var(--color-primary);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: opacity 0.15s;
}

.supplier-order-card__ship-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.supplier-order-card__ship-btn:hover:not(:disabled) {
  opacity: 0.9;
}
</style>
