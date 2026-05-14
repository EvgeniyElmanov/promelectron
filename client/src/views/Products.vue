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

      <div v-if="products.length === 0 && !loading" class="home__empty">
        Товары не найдены
      </div>

      <button
        v-if="hasMore && !loading && products.length > 0"
        class="home__load-more"
        @click="loadMore"
      >
        Показать ещё
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import ProductCard from '@/components/ProductCard.vue';
import SearchBar from '@/components/SearchBar.vue';
import CategoryChips from '@/components/CategoryChips.vue';
import PromoBanner from '@/components/PromoBanner.vue';
import api from '@/services/api';

const products = ref([]);
const searchQuery = ref('');
const selectedCategory = ref(null);
const loading = ref(false);
const skip = ref(0);
const limit = 20;
const total = ref(null);

const hasMore = computed(() => total.value === null || skip.value < total.value);

let searchTimeout = null;

const fetchProducts = async (append = false) => {
  loading.value = true;
  try {
    const params = { skip: skip.value, limit };
    if (searchQuery.value.trim()) params.q = searchQuery.value.trim();
    if (selectedCategory.value) params.category_id = selectedCategory.value;

    const { data } = await api.get('/products/', { params });
    if (append) {
      products.value.push(...data);
    } else {
      products.value = data;
    }
    if (data.length < limit) {
      total.value = skip.value + data.length;
    } else {
      total.value = null;
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

const handleCategorySelect = (categoryId) => {
  selectedCategory.value = categoryId;
  skip.value = 0;
  fetchProducts();
};

watch(searchQuery, () => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    skip.value = 0;
    fetchProducts();
  }, 300);
});

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

@media (min-width: 768px) {
  .home__grid {
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
  }
  
  .home__section {
    padding: 16px;
  }
}

@media (min-width: 1024px) {
  .home__grid {
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
  }
}

@media (min-width: 1280px) {
  .home__grid {
    grid-template-columns: repeat(5, 1fr);
    gap: 16px;
  }
}

.home__loading {
  text-align: center;
  padding: 16px;
  color: var(--color-text-secondary);
  font-size: 14px;
}

.home__empty {
  text-align: center;
  padding: 40px 20px;
  color: var(--color-text-secondary);
  font-size: 15px;
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
