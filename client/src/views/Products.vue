<template>
  <div class="products-container">
    <h2>Products</h2>
    <div class="products-grid">
      <ProductCard
        v-for="product in products"
        :key="product.id"
        :product="product"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import ProductCard from '@/components/ProductCard.vue';
import api from '@/services/api';

const products = ref([]);

const fetchProducts = async () => {
  try {
    const response = await api.get('/products/');
    products.value = response.data;
  } catch (err) {
    console.error(err);
  }
};

onMounted(fetchProducts);
</script>

<style scoped>
.products-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 1rem;
}
</style>
