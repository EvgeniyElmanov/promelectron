<template>
  <div class="home">
    <SearchBar v-model="searchQuery" class="home__search-bar" />
    <CategoryChips @select="handleCategorySelect" />
    <PromoBanner />

    <div class="home__section">
      <div class="home__filters">
        <select
          v-model="selectedSort"
          class="home__sort-select"
          data-testid="sort-select"
          @change="applyFilters"
        >
          <option value="">По умолчанию</option>
          <option value="price_asc">Цена: по возрастанию</option>
          <option value="price_desc">Цена: по убыванию</option>
          <option value="rating_desc">По рейтингу</option>
          <option value="newest">Сначала новые</option>
          <option value="name_asc">По названию (А-Я)</option>
        </select>

        <div class="home__price-filter">
          <input
            v-model.number="minPrice"
            type="number"
            placeholder="От"
            class="home__price-input"
            data-testid="min-price-input"
            min="0"
          />
          <span class="home__price-sep">—</span>
          <input
            v-model.number="maxPrice"
            type="number"
            placeholder="До"
            class="home__price-input"
            data-testid="max-price-input"
            min="0"
          />
          <button class="home__price-btn" data-testid="apply-price-btn" @click="applyFilters">
            OK
          </button>
        </div>
      </div>

      <div class="home__rating-filter">
        <span class="home__rating-label">Рейтинг:</span>
        <button
          v-for="n in 5"
          :key="n"
          class="home__rating-btn"
          :class="{ 'home__rating-btn--active': minRating === n }"
          :data-testid="`rating-filter-${n}`"
          @click="toggleRatingFilter(n)"
        >
          {{ n }}★
        </button>
        <button
          v-if="minRating !== null"
          class="home__rating-clear"
          data-testid="rating-clear"
          @click="minRating = null; applyFilters()"
        >
          ✕
        </button>
      </div>

      <div class="home__header-row">
        <h2 class="home__section-title" data-testid="products-section-title">Популярные товары</h2>
        <span class="home__count" data-testid="products-count">
          <template v-if="total !== null">{{ total }} товаров</template>
          <template v-else>&nbsp;</template>
        </span>
      </div>

      <!-- Skeleton grid replaces product grid during initial load -->
      <div v-if="loading && products.length === 0" class="home__grid">
        <SkeletonProductCard v-for="i in 8" :key="'sk' + i" />
      </div>

      <div v-else-if="products.length === 0 && !loading" class="home__empty" data-testid="products-empty">
        Товары не найдены
      </div>

      <div v-else class="home__grid">
        <ProductCard
          v-for="product in products"
          :key="product.id"
          :product="product"
        />
      </div>

      <!-- Inline spinner for infinite scroll append loading -->
      <div v-if="loading && products.length > 0" class="home__loading-more">
        <div class="home__spinner" />
      </div>

      <!-- Intersection Observer target for infinite scroll -->
      <div ref="loadMoreTrigger" class="home__load-trigger" />

      <button
        v-if="hasMore && !loading && products.length > 0"
        class="home__load-more"
        data-testid="load-more-btn"
        @click="loadMore"
      >
        Показать ещё
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import { useRoute } from 'vue-router';
import ProductCard from '@/components/ProductCard.vue';
import SearchBar from '@/components/SearchBar.vue';
import CategoryChips from '@/components/CategoryChips.vue';
import PromoBanner from '@/components/PromoBanner.vue';
import SkeletonProductCard from '@/components/SkeletonProductCard.vue';
import api from '@/services/api';

const route = useRoute();
const products = ref([]);
const searchQuery = ref('');
const selectedCategory = ref(null);
const selectedSort = ref('');
const minPrice = ref(null);
const maxPrice = ref(null);
const minRating = ref(null);
const loading = ref(false);
const skip = ref(0);
const limit = 20;
const total = ref(null);
const loadMoreTrigger = ref(null);

const hasMore = computed(() => total.value === null || products.value.length < total.value);

let searchTimeout = null;
let abortController = null;
let fetchId = 0;

const fetchProducts = async (append = false) => {
  // Cancel previous request
  if (abortController) {
    abortController.abort();
  }
  abortController = new AbortController();
  const currentFetchId = ++fetchId;

  loading.value = true;
  try {
    const params = { skip: skip.value, limit };
    if (searchQuery.value.trim()) params.q = searchQuery.value.trim();
    if (selectedCategory.value) params.category_id = selectedCategory.value;
    if (selectedSort.value) params.sort_by = selectedSort.value;
    if (minPrice.value !== null && minPrice.value !== '') params.min_price = minPrice.value;
    if (maxPrice.value !== null && maxPrice.value !== '') params.max_price = maxPrice.value;
    if (minRating.value !== null) params.min_rating = minRating.value;

    const { data } = await api.get('/products/', { params, signal: abortController.signal });
    // Ignore stale responses
    if (currentFetchId !== fetchId) return;

    if (append) {
      products.value.push(...data.items);
    } else {
      products.value = data.items;
    }
    total.value = data.total;
  } catch (err) {
    if (err.name !== 'AbortError' && err.code !== 'ERR_CANCELED') {
      console.error('Failed to fetch products:', err);
    }
  } finally {
    if (currentFetchId === fetchId) {
      loading.value = false;
    }
  }
};

const loadMore = () => {
  if (!hasMore.value || loading.value) return;
  skip.value += limit;
  fetchProducts(true);
};

const handleCategorySelect = (categoryId) => {
  selectedCategory.value = categoryId;
  skip.value = 0;
  fetchProducts();
};

const applyFilters = () => {
  skip.value = 0;
  fetchProducts();
};

const toggleRatingFilter = (rating) => {
  minRating.value = minRating.value === rating ? null : rating;
  applyFilters();
};

watch(searchQuery, () => {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    skip.value = 0;
    fetchProducts();
  }, 300);
});

onMounted(async () => {
  if (route.query.q) {
    searchQuery.value = String(route.query.q);
  }
  await fetchProducts();

  // Infinite scroll via IntersectionObserver
  if (loadMoreTrigger.value && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && hasMore.value && !loading.value && products.value.length > 0) {
        loadMore();
      }
    }, { rootMargin: '100px' });
    observer.observe(loadMoreTrigger.value);
  }
});
</script>

<style scoped>
.home {
  background: var(--color-bg);
}

@media (min-width: 768px) {
  .home__search-bar {
    display: none;
  }
}

.home__section {
  padding: 12px;
}

.home__filters {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 12px;
}

.home__sort-select {
  width: 100%;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-white);
  font-size: 14px;
  color: var(--color-text);
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23666' d='M6 8L1 3h10z'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
}

.home__price-filter {
  display: flex;
  align-items: center;
  gap: 8px;
}

.home__price-input {
  flex: 1;
  min-width: 0;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-white);
  font-size: 14px;
  color: var(--color-text);
}

.home__price-input::placeholder {
  color: var(--color-text-secondary);
}

.home__price-sep {
  color: var(--color-text-secondary);
  font-size: 14px;
}

.home__price-btn {
  padding: 10px 16px;
  border-radius: 10px;
  background: var(--color-primary);
  color: var(--color-white);
  font-size: 14px;
  font-weight: 500;
  border: none;
  flex-shrink: 0;
}

@media (min-width: 768px) {
  .home__filters {
    flex-direction: row;
    align-items: center;
  }

  .home__sort-select {
    width: auto;
    min-width: 220px;
  }

  .home__price-filter {
    flex: 1;
    justify-content: flex-end;
  }
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

.home__loading-more {
  display: flex;
  justify-content: center;
  padding: 16px;
}

.home__spinner {
  width: 24px;
  height: 24px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: home-spinner 0.8s linear infinite;
}

@keyframes home-spinner {
  to { transform: rotate(360deg); }
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

.home__rating-filter {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.home__rating-label {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin-right: 4px;
}

.home__rating-btn {
  padding: 6px 12px;
  border-radius: 20px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-white);
  font-size: 13px;
  color: var(--color-text-secondary);
  transition: all 0.15s;
}

.home__rating-btn--active {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

.home__rating-clear {
  padding: 6px 10px;
  border-radius: 20px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-white);
  font-size: 13px;
  color: var(--color-text-secondary);
}

.home__header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.home__count {
  font-size: 14px;
  color: var(--color-text-secondary);
}

.home__load-trigger {
  height: 20px;
  margin-top: 8px;
}
</style>
