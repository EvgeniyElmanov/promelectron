<template>
  <div class="product-card">
    <h3>{{ product.name }}</h3>
    <p>{{ product.description }}</p>
    <p>Price: ${{ product.price }}</p>
    <p>Stock: {{ product.stock }}</p>
    <button @click="addToCart">Add to Cart</button>
  </div>
</template>

<script setup>
import { defineProps } from 'vue';
import api from '@/services/api';

const props = defineProps({
  product: Object,
});

const addToCart = async () => {
  try {
    await api.post('/cart/add', {
      product_id: props.product.id,
      quantity: 1,
    });
    alert('Added to cart');
  } catch (err) {
    console.error(err);
  }
};
</script>

<style scoped>
.product-card {
  border: 1px solid #ccc;
  padding: 1rem;
  border-radius: 4px;
}
</style>
