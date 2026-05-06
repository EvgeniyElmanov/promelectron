<template>
  <div class="orders-container">
    <h2>My Orders</h2>
    <div v-if="orders.length === 0">
      <p>You haven't placed any orders yet.</p>
    </div>
    <div v-else>
      <ul>
        <li v-for="order in orders" :key="order.id" class="order-item">
          <p>Order #{{ order.id }} - Status: {{ order.status }}</p>
          <p>Total: ${{ order.total_price }}</p>
          <p>Date: {{ order.created_at }}</p>
          <ul>
            <li v-for="item in order.items" :key="item.id">
              {{ item.product.name }} x {{ item.quantity }} - ${{ item.price_at_time }}
            </li>
          </ul>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import api from '@/services/api';

const orders = ref([]);

const fetchOrders = async () => {
  try {
    const response = await api.get('/orders/');
    orders.value = response.data;
  } catch (err) {
    console.error(err);
  }
};

onMounted(fetchOrders);
</script>

<style scoped>
.order-item {
  border: 1px solid #ccc;
  padding: 1rem;
  margin-bottom: 1rem;
  border-radius: 4px;
}
</style>
