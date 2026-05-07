<template>
  <div class="product-card">
    <h3>{{ product.name }}</h3>
    <p>{{ product.description }}</p>
    <p>Price: ${{ product.price }}</p>
    <p>Stock: {{ product.stock }}</p>
    <button :disabled="isLoading" @click="addToCart">
      {{ isLoading ? 'Adding...' : 'Add to Cart' }}
    </button>
  </div>
</template>

<script setup>
import { defineProps, ref } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/services/api';

const props = defineProps({
  product: Object,
});

const router = useRouter();
const isLoading = ref(false);

const addToCart = async () => {
  if (isLoading.value) {
    return;
  }

  isLoading.value = true;

  try {
    await api.post('/cart/add', {
      product_id: props.product.id,
      quantity: 1,
    });
    alert('Added to cart');
  } catch (err) {
    if (err?.response?.status === 401) {
      alert('Session expired. Please log in again.');
      router.push('/login');
      return;
    }

    alert('Failed to add item to cart. Please try again.');
  } finally {
    isLoading.value = false;
  }
};
</script>

<style scoped>
.product-card {
  border: 1px solid #ccc;
  padding: 1rem;
  border-radius: 4px;
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>