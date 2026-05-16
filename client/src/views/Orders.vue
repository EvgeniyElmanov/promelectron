<template>
  <div class="orders-container" data-testid="orders-page">
    <h2 data-testid="orders-title">Мои заказы</h2>

    <div v-if="loading" class="loading">
      <p>Загрузка заказов...</p>
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
      <div v-for="order in orders" :key="order.id" class="order-card" data-testid="order-card">
        <div class="order-header">
          <span class="order-id">Заказ №{{ order.id }}</span>
          <span class="order-date">{{ formatDate(order.created_at) }}</span>
        </div>
        <div class="order-body">
          <p>Статус: <strong>{{ order.status }}</strong></p>
          <p>Сумма: <strong>{{ order.total_price }} ₽</strong></p>
          <p v-if="order.shipping_address">Адрес доставки: <strong>{{ order.shipping_address }}</strong></p>
          <div v-if="order.items && order.items.length" class="order-items">
            <p>Товары:</p>
            <ul>
              <li v-for="item in order.items" :key="item.id">
                {{ item.product?.name || 'Товар' }} × {{ item.quantity }} — {{ item.price_at_time }} ₽
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import api from '@/services/api';

const orders = ref([]);
const loading = ref(true);
const error = ref(null);

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

.order-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1rem;
  background-color: #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.order-header {
  display: flex;
  justify-content: space-between;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid #e2e8f0;
  margin-bottom: 0.75rem;
}

.order-id {
  font-weight: bold;
  font-size: 1.1rem;
}

.order-date {
  color: #718096;
  font-size: 0.9rem;
}

.order-body p {
  margin: 0.5rem 0;
}

.order-items {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px dashed #e2e8f0;
}

.order-items ul {
  padding-left: 1.25rem;
  margin: 0.5rem 0 0;
}

.order-items li {
  margin-bottom: 0.25rem;
  color: #4a5568;
}

button {
  background-color: #007bff;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  margin-top: 0.5rem;
}

a {
  color: #007bff;
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}
</style>
