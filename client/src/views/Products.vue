<template>
  <div class="home">
    <SearchBar v-model="searchQuery" />
    <CategoryChips @select="handleCategorySelect" />
    <PromoBanner />

    <div class="home__section">
      <h2 class="home__section-title" data-testid="products-section-title">Популярные товары</h2>
      <div class="home__grid">
        <ProductCard
          v-for="product in products"
          :key="product.id"
          :product="product"
        />
      </div>

      <div v-if="loading" class="home__loading">Загрузка...</div>

      <button
        v-if="hasMore && !loading"
        class="home__load-more"
        @click="loadMore"
      >
        Показать ещё
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import ProductCard from '@/components/ProductCard.vue';
import SearchBar from '@/components/SearchBar.vue';
import CategoryChips from '@/components/CategoryChips.vue';
import PromoBanner from '@/components/PromoBanner.vue';
import api from '@/services/api';

const products = ref([]);
const searchQuery = ref('');
const loading = ref(false);
const skip = ref(0);
const limit = 20;
const total = ref(null);

const hasMore = computed(() => total.value === null || skip.value < total.value);

const fetchProducts = async (append = false) => {
  loading.value = true;
  try {
    const { data } = await api.get('/products/', { params: { skip: skip.value, limit } });
    if (append) {
      products.value.push(...data);
    } else {
      products.value = data;
    }
    // Guess total based on result size — API doesn't return count
    if (data.length < limit) {
      total.value = skip.value + data.length;
    }
  } catch {
    // silently fail
  } finally {
    loading.value = false;
  }
};

const loadMore = () => {
  skip.value += limit;
  fetchProducts(true);
};

const handleCategorySelect = (_categoryId) => {
  // Placeholder: backend doesn't support category filter yet
};

onMounted(() => fetchProducts());
</script>

<style scoped>
.home {
  background: var(--color-bg);
}

.home__section {
  padding: 12px;
}

.home__section-title {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 10px;
  color: var(--color-text);
}

.home__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.home__loading {
  text-align: center;
  padding: 16px;
  color: var(--color-text-secondary);
  font-size: 14px;
}

.home__load-more {
  display: block;
  width: 100%;
  margin-top: 12px;
  padding: 12px;
  border-radius: 12px;
  background: var(--color-bg-white);
  color: var(--color-primary);
  font-size: 15px;
  font-weight: 500;
  transition: background 0.15s;
}

.home__load-more:hover {
  background: #e8f0fe;
}
</style>