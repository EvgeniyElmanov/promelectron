<template>
  <div class="home">
    <HeroBanner @cta-click="scrollToListing" @show-new="onShowNew" />
    <BenefitsStrip />
    <SearchBar v-model="searchQuery" class="home__search-bar" @submit="onSearchSubmit" />
    <PopularCategories @select="onCategoryCardSelect" @view-all="scrollToListing" />
    <CategoryChips @select="handleCategorySelect" />

    <div class="home__section">
      <AppBreadcrumbs :items="catalogCrumbs" class="home__breadcrumbs" />
      <h1 class="home__title">Каталог</h1>

      <div class="home__filters">
        <select
          v-model="currentSort"
          class="home__sort-select"
          data-testid="sort-select"
        >
          <option value="">По умолчанию</option>
          <option value="price_asc">Цена: по возрастанию</option>
          <option value="price_desc">Цена: по убыванию</option>
          <option v-if="!searchAvailable" value="rating_desc">По рейтингу</option>
          <option value="newest">Сначала новые</option>
          <option value="name_asc">По названию (А-Я)</option>
        </select>

        <div v-if="!searchAvailable" class="home__price-filter">
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
          <AppButton size="sm" data-testid="apply-price-btn" class="home__price-btn" @click="applyFilters">
            OK
          </AppButton>
        </div>
      </div>

      <div v-if="!searchAvailable" class="home__rating-filter">
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

      <div class="home__catalog" :class="{ 'home__catalog--search': searchAvailable }">
        <details
          v-if="searchAvailable"
          class="home__filter-panel-wrap"
          :open="filtersOpen"
          @toggle="onFiltersToggle"
        >
          <summary class="home__filter-panel-summary">Фильтры</summary>
          <FilterPanel
            :facets="facets"
            :selected="catalog.selected"
            :price-range="catalog.priceRange"
            :category-id="categoryId"
            :category-options="allCategories"
            @toggle="catalog.toggleFacetValue"
            @price="onFilterPrice"
            @range="onFilterRange"
            @category="catalog.setCategory"
            @reset="catalog.reset"
          />
        </details>

        <div class="home__listing">
          <div class="home__tabs">
            <button
              class="home__tab"
              :class="{ 'home__tab--active': currentSort === '' }"
              data-testid="products-tab-hits"
              :aria-pressed="currentSort === ''"
              @click="setProductsTab('')"
            >
              Хиты продаж
            </button>
            <button
              class="home__tab"
              :class="{ 'home__tab--active': currentSort === 'newest' }"
              data-testid="products-tab-new"
              :aria-pressed="currentSort === 'newest'"
              @click="setProductsTab('newest')"
            >
              Новинки
            </button>
          </div>

          <div class="home__header-row">
            <h2 ref="listingTitle" class="home__section-title" data-testid="products-section-title">Популярные товары</h2>
            <span class="home__count" data-testid="products-count">
              <template v-if="displayTotal !== null">{{ displayTotal }} товаров</template>
              <template v-else>&nbsp;</template>
            </span>
          </div>

          <!-- Skeleton grid replaces product grid during initial load -->
          <div v-if="displayLoading && displayProducts.length === 0" class="home__grid">
            <SkeletonProductCard v-for="i in 8" :key="'sk' + i" />
          </div>

          <div v-else-if="displayProducts.length === 0 && !displayLoading" class="home__empty" data-testid="products-empty">
            Товары не найдены
          </div>

          <div v-else class="home__grid">
            <ProductCard
              v-for="product in displayProducts"
              :key="product.id"
              :product="product"
            />
          </div>

          <!-- Inline spinner for infinite scroll append loading -->
          <div v-if="displayLoading && displayProducts.length > 0" class="home__loading-more">
            <div class="home__spinner" />
          </div>

          <!-- Intersection Observer target for infinite scroll -->
          <div ref="loadMoreTrigger" class="home__load-trigger" />

          <AppButton
            v-if="displayHasMore && !displayLoading && displayProducts.length > 0"
            variant="secondary"
            block
            class="home__load-more"
            data-testid="load-more-btn"
            @click="onLoadMore"
          >
            Показать ещё
          </AppButton>
        </div>
      </div>
    </div>

    <AppFooter />
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import ProductCard from '@/components/ProductCard.vue';
import SearchBar from '@/components/SearchBar.vue';
import CategoryChips from '@/components/CategoryChips.vue';
import SkeletonProductCard from '@/components/SkeletonProductCard.vue';
import FilterPanel from '@/components/FilterPanel.vue';
import HeroBanner from '@/components/home/HeroBanner.vue';
import BenefitsStrip from '@/components/home/BenefitsStrip.vue';
import PopularCategories from '@/components/home/PopularCategories.vue';
import AppFooter from '@/components/AppFooter.vue';
import AppBreadcrumbs from '@/components/ui/AppBreadcrumbs.vue';
import AppButton from '@/components/ui/AppButton.vue';
import { useCatalogSearch } from '@/composables/useCatalogSearch';
import { useCategories } from '@/composables/useCategories';
import api from '@/services/api';

const route = useRoute();
const router = useRouter();
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
const listingTitle = ref(null);

// Фильтры каталога: на мобилке (<768px) свёрнуты по умолчанию, на десктопе развёрнуты.
// Только initial-состояние; дальше пользователь управляет <details> сам (@toggle синкает ref,
// чтобы re-render не сбрасывал ручное переключение).
const filtersOpen = ref(
  typeof window !== 'undefined' && typeof window.matchMedia === 'function'
    ? window.matchMedia('(min-width: 768px)').matches
    : true
);
const onFiltersToggle = (event) => {
  // toggle всплывает от вложенных <details> внутри FilterPanel — реагируем только на внешний
  if (event.target !== event.currentTarget) return;
  filtersOpen.value = event.currentTarget.open;
};

// Search-режим (feature flag `catalog_search_meilisearch`, D-01/D-05):
// probe решает, работаем ли через /api/v1/search/ или legacy /products/.
const catalog = useCatalogSearch();
const { searchAvailable, facets, categoryId } = catalog;
const { allCategories, fetchAllCategories } = useCategories();

const hasMore = computed(() => total.value === null || products.value.length < total.value);

// Крошки каталога (§21): Главная / Каталог [ / <категория> ].
// Имя категории доступно только в search-режиме (allCategories грузится при probe,
// legacy-режим знает только id) — без имени звено не добавляем (D-02).
const catalogCrumbs = computed(() => {
  const crumbs = [{ label: 'Главная', to: '/' }];
  let categoryName = null;
  if (searchAvailable.value && categoryId.value) {
    const category = allCategories.value.find((c) => c.id === categoryId.value);
    if (category) categoryName = category.name;
  }
  crumbs.push(categoryName ? { label: 'Каталог', to: '/' } : { label: 'Каталог' });
  if (categoryName) crumbs.push({ label: categoryName });
  return crumbs;
});

// Унифицированные значения для шаблона: активный источник (search или legacy).
const displayProducts = computed(() => (searchAvailable.value ? catalog.items.value : products.value));
const displayTotal = computed(() => (searchAvailable.value ? catalog.total.value : total.value));
const displayLoading = computed(() => (searchAvailable.value ? catalog.loading.value : loading.value));
const displayHasMore = computed(() => (searchAvailable.value ? catalog.hasMore.value : hasMore.value));

// Селектор сортировки делегирует в активный режим
// (`rating_desc` в search-режиме недоступен — backend его не поддерживает).
const currentSort = computed({
  get: () => (searchAvailable.value ? catalog.sort.value : selectedSort.value),
  set: (value) => {
    if (searchAvailable.value) {
      catalog.setSort(value);
    } else {
      selectedSort.value = value;
      applyFilters();
    }
  },
});

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

const onLoadMore = () => {
  if (searchAvailable.value) {
    catalog.loadMore();
  } else {
    loadMore();
  }
};

const handleCategorySelect = (categoryIdValue) => {
  if (searchAvailable.value) {
    catalog.setCategory(categoryIdValue);
    return;
  }
  selectedCategory.value = categoryIdValue;
  skip.value = 0;
  fetchProducts();
};

const scrollToListing = () => {
  const el = listingTitle.value;
  if (el && typeof el.scrollIntoView === 'function') {
    el.scrollIntoView({ behavior: 'smooth' });
  }
};

// Клик по CategoryCard — тот же фильтр, что даёт CategoryChips (S-02),
// плюс скролл к листингу.
const onCategoryCardSelect = (categoryIdValue) => {
  handleCategorySelect(categoryIdValue);
  scrollToListing();
};

// Табы «Хиты продаж / Новинки» — UI над currentSort (D-07), без нового fetch-механизма.
const setProductsTab = (sort) => {
  currentSort.value = sort;
};

const onShowNew = () => {
  setProductsTab('newest');
  scrollToListing();
};

const onFilterPrice = ({ min, max }) => catalog.setPrice(min, max);
const onFilterRange = (code, { min, max }) => catalog.setRange(code, min, max);

const applyFilters = () => {
  skip.value = 0;
  fetchProducts();
};

const toggleRatingFilter = (rating) => {
  minRating.value = minRating.value === rating ? null : rating;
  applyFilters();
};

watch(searchQuery, () => {
  if (searchAvailable.value) {
    catalog.setQuery(searchQuery.value);
    return;
  }
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    skip.value = 0;
    fetchProducts();
  }, 300);
});

const onSearchSubmit = (q) => {
  clearTimeout(searchTimeout);
  router.push({ path: '/', query: q ? { q } : undefined });
};

// React to URL query changes (e.g. from header search)
watch(
  () => route.query.q,
  (newQ) => {
    const q = newQ ? String(newQ) : '';
    if (q !== searchQuery.value) {
      clearTimeout(searchTimeout);
      searchQuery.value = q;
      if (!searchAvailable.value) {
        skip.value = 0;
        fetchProducts();
      }
    }
  }
);

onMounted(async () => {
  if (route.query.q) {
    searchQuery.value = String(route.query.q);
  }
  // Probe сначала: решает, какой режим грузить (последовательно, без гонки).
  const available = await catalog.probe();
  if (available) {
    fetchAllCategories();
    catalog.initFromUrl();
    catalog.q.value = searchQuery.value;
    await catalog.load();
  } else {
    await fetchProducts();
  }

  // Infinite scroll via IntersectionObserver
  if (loadMoreTrigger.value && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && displayHasMore.value && !displayLoading.value && displayProducts.value.length > 0) {
        onLoadMore();
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

.home__catalog--search {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.home__filter-panel-summary {
  display: block;
  font-size: 15px;
  font-weight: 600;
  padding: 10px 12px;
  background: var(--color-bg-white);
  border-radius: var(--radius-md);
  cursor: pointer;
  user-select: none;
  list-style: none;
}

.home__filter-panel-summary::before {
  content: '▾ ';
  color: var(--color-text-secondary);
}

.home__filter-panel-wrap:not([open]) > .home__filter-panel-summary::before {
  content: '▸ ';
}

.home__filter-panel-wrap .filter-panel {
  margin-top: 8px;
}

.home__listing {
  flex: 1;
  min-width: 0;
}

@media (min-width: 768px) {
  .home__catalog--search {
    flex-direction: row;
    align-items: flex-start;
  }

  .home__filter-panel-wrap {
    width: 260px;
    flex-shrink: 0;
    position: sticky;
    top: 12px;
  }

  /* На desktop панель всегда развёрнута, summary не нужен */
  .home__filter-panel-summary {
    display: none;
  }

  .home__filter-panel-wrap .filter-panel {
    margin-top: 0;
  }
}

.home__breadcrumbs {
  margin-bottom: var(--space-2);
}

.home__title {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text);
  margin: 0 0 var(--space-3);
}

.home__filters {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 12px;
}

.home__sort-select {
  width: 100%;
  height: 48px;
  padding: 0 36px 0 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: var(--color-bg-white);
  font-size: 14px;
  color: var(--color-text);
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%236b7280' d='M6 8L1 3h10z'/%3E%3C/svg%3E");
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
  border-radius: var(--radius-md);
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
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
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
  padding: var(--space-6, 40px) var(--space-5, 20px);
  color: var(--color-text-secondary);
  font-size: 15px;
  background: var(--color-bg-white);
  border-radius: var(--radius-lg);
}

.home__load-more {
  margin-top: 12px;
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
  border-radius: var(--radius-pill);
  border: 1px solid var(--color-border);
  background: var(--color-bg-white);
  font-size: 13px;
  color: var(--color-text-secondary);
  transition: all 0.15s;
}

.home__rating-btn--active {
  background: var(--color-primary);
  color: var(--color-white);
  border-color: var(--color-primary);
}

.home__rating-clear {
  padding: 6px 10px;
  border-radius: var(--radius-pill);
  border: 1px solid var(--color-border);
  background: var(--color-bg-white);
  font-size: 13px;
  color: var(--color-text-secondary);
}

@media (max-width: 767px) {
  .home__rating-btn,
  .home__rating-clear {
    display: inline-flex;
    align-items: center;
    min-height: 40px;
  }
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

.home__tabs {
  display: flex;
  gap: var(--space-4);
  margin-bottom: var(--space-3);
}

.home__tab {
  background: none;
  border: none;
  padding: var(--space-2) 0;
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-medium);
  color: var(--color-text-secondary);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: color 0.15s, border-color 0.15s;
}

.home__tab:hover {
  color: var(--color-text);
}

.home__tab--active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
}

.home__load-trigger {
  height: 20px;
  margin-top: 8px;
}
</style>
