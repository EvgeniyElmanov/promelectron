<template>
  <div class="orders-container" data-testid="orders-page">
    <h2 data-testid="orders-title">Мои заказы</h2>

    <div v-if="loading" class="orders-list">
      <SkeletonOrderCard v-for="i in 2" :key="'sk' + i" />
    </div>

    <div v-else-if="error" class="error">
      <p>Ошибка загрузки: {{ error }}</p>
      <button @click="fetchOrders">Повторить</button>
    </div>

    <div v-else-if="orders.length === 0" class="empty">
      <p>У вас пока нет заказов.</p>
      <router-link to="/">Перейти в каталог</router-link>
    </div>

    <div v-else class="orders-list">
      <router-link
        v-for="order in orders"
        :key="order.id"
        :to="`/orders/${order.id}`"
        class="order-card"
        data-testid="order-card"
      >
        <div class="order-header">
          <span class="order-id">Заказ №{{ order.id }}</span>
          <span class="order-date">{{ formatDate(order.created_at) }}</span>
        </div>
        <div class="order-body">
          <div class="order-row">
            <span class="order-label">Сумма</span>
            <span class="order-value">{{ Number(order.total_price).toLocaleString('ru-RU') }} ₽</span>
          </div>
          <div class="order-row">
            <span class="order-label">Статус</span>
            <span class="status-badge" :class="'status-badge--' + order.status">{{ statusLabel(order.status) }}</span>
          </div>
          <div v-if="order.status === 'pending'" class="order-row order-row--action">
            <router-link :to="`/checkout/${order.id}`" class="order-pay-btn">
              Оплатить
            </router-link>
          </div>
          <div v-if="order.shipping_address" class="order-row">
            <span class="order-label">Адрес</span>
            <span class="order-value order-value--address">{{ order.shipping_address }}</span>
          </div>
          <div class="order-row">
            <span class="order-label">Товаров</span>
            <span class="order-value">{{ order.items?.length || 0 }} шт.</span>
          </div>
        </div>
        <div class="order-footer">
          <span class="order-detail-link">Подробнее →</span>
        </div>
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import api from '@/services/api';
import SkeletonOrderCard from '@/components/SkeletonOrderCard.vue';

const orders = ref([]);
const loading = ref(true);
const error = ref(null);

const statusLabel = (status) => {
  const labels = {
    pending: 'Ожидает оплаты',
    paid: 'Оплачен',
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
    const response = await api.get('/orders/');
    orders.value = response.data;
  } catch (err) {
    console.error('Ошибка загрузки заказов:', err);
    error.value = err.response?.data?.detail || err.message || 'Не удалось загрузить заказы';
  } finally {
    loading.value = false;
  }
};

onMounted(fetchOrders);
</script>

<style scoped>
.orders-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 1rem;
}

@media (min-width: 768px) {
  .orders-container {
    padding: 2rem;
  }
}

.loading,
.error,
.empty {
  text-align: center;
  padding: 2rem;
}

.error {
  color: #e53e3e;
  background-color: #fff5f5;
  border: 1px solid #feb2b2;
  border-radius: 8px;
}

.orders-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.order-card {
  display: block;
  border-radius: 14px;
  padding: 16px;
  background: var(--color-bg-white);
  color: var(--color-text);
  text-decoration: none;
  transition: box-shadow 0.2s, transform 0.2s;
}

.order-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  transform: translateY(-1px);
}

.order-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 10px;
}

.order-id {
  font-weight: 700;
  font-size: 16px;
  color: var(--color-text);
}

.order-date {
  color: var(--color-text-secondary);
  font-size: 13px;
}

.order-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.order-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.order-label {
  font-size: 14px;
  color: var(--color-text-secondary);
}

.order-value {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text);
}

.order-value--address {
  max-width: 60%;
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-badge {
  display: inline-block;
  padding: 3px 10px;
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

.order-row--action {
  margin-top: 8px;
  justify-content: flex-end;
}

.order-pay-btn {
  display: inline-block;
  padding: 10px 20px;
  border-radius: 12px;
  background: var(--color-primary);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
  text-align: center;
}

.order-footer {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--color-border);
  text-align: right;
}

.order-detail-link {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-primary);
}

button {
  background-color: var(--color-primary);
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  cursor: pointer;
  margin-top: 0.5rem;
}
</style>
