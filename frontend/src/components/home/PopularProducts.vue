<template>
  <section id="popular-products" class="popular-products" data-testid="popular-products">
    <div class="popular-products__header">
      <h2 class="popular-products__title">Популярные товары</h2>
      <RouterLink to="/catalog" class="popular-products__view-all" data-testid="products-view-all">
        Все товары →
      </RouterLink>
    </div>

    <div class="popular-products__tabs" role="tablist">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="popular-products__tab"
        :class="{ 'popular-products__tab--active': activeTab === tab.key }"
        :data-testid="`products-tab-${tab.key}`"
        role="tab"
        :aria-selected="activeTab === tab.key"
        @click="setTab(tab.key)"
      >
        {{ tab.label }}
      </button>
    </div>

    <div v-if="loading" class="popular-products__grid">
      <SkeletonProductCard v-for="i in 6" :key="'sk' + i" />
    </div>

    <div
      v-else-if="activeTab === 'sale'"
      class="popular-products__empty"
      data-testid="products-tab-sale-empty"
    >
      Скидок сейчас нет
    </div>

    <div v-else-if="products.length === 0" class="popular-products__empty" data-testid="popular-products-empty">
      Товары не найдены
    </div>

    <div v-else class="popular-products__grid">
      <ProductCard v-for="product in products" :key="product.id" :product="product" />
    </div>
  </section>
</template>

<script setup>
// «Популярные товары» главной (D-08): табы «Хиты продаж / Новинки / Скидки»,
// 6 карточек desktop / 2 колонки mobile, «Все товары →» → /catalog.
// Хиты — дефолтный порядок API, приоритет товарам с is_hit (optional, D-03;
// без полей — порядок API, задокументированный fallback). Новинки — sort_by=newest.
// Скидки — old_price в данных нет (D-04) → честный empty-state «Скидок сейчас нет».
// При ошибке API секция скрывает грид, страница не валится (S-05).
import { ref, onMounted } from 'vue';
import ProductCard from '@/components/ProductCard.vue';
import SkeletonProductCard from '@/components/SkeletonProductCard.vue';
import api from '@/services/api';

const PAGE_SIZE = 6;

const props = defineProps({
  initialTab: { type: String, default: 'hits' },
});

const tabs = [
  { key: 'hits', label: 'Хиты продаж' },
  { key: 'new', label: 'Новинки' },
  { key: 'sale', label: 'Скидки' },
];

const activeTab = ref(tabs.some((t) => t.key === props.initialTab) ? props.initialTab : 'hits');
const products = ref([]);
const loading = ref(false);

const cache = new Map();

const fetchTab = async (tab) => {
  if (tab === 'sale') {
    products.value = [];
    return;
  }
  if (cache.has(tab)) {
    products.value = cache.get(tab);
    return;
  }
  loading.value = true;
  try {
    const params = { skip: 0, limit: PAGE_SIZE };
    if (tab === 'new') params.sort_by = 'newest';
    const { data } = await api.get('/products/', { params });
    let items = data.items || [];
    if (tab === 'hits' && items.some((p) => p.is_hit)) {
      items = [...items].sort((a, b) => Number(b.is_hit || false) - Number(a.is_hit || false));
    }
    cache.set(tab, items);
    products.value = items;
  } catch {
    products.value = [];
  } finally {
    loading.value = false;
  }
};

const setTab = (tab) => {
  if (activeTab.value === tab) return;
  activeTab.value = tab;
  fetchTab(tab);
};

defineExpose({ setTab });

onMounted(() => fetchTab(activeTab.value));
</script>

<style scoped>
.popular-products {
  padding: var(--space-6) var(--space-4) 0;
}

.popular-products__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-3);
}

.popular-products__title {
  font-size: var(--font-size-h2);
  font-weight: var(--font-weight-bold);
  color: var(--color-text);
}

.popular-products__view-all {
  font-size: var(--font-size-body-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-primary);
  text-decoration: none;
  flex-shrink: 0;
}

.popular-products__tabs {
  display: flex;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}

.popular-products__tab {
  background: none;
  border: none;
  padding: var(--space-2) 0;
  font-size: var(--font-size-body);
  font-weight: var(--font-weight-medium);
  font-family: inherit;
  color: var(--color-text-secondary);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: color 0.15s, border-color 0.15s;
}

.popular-products__tab:hover {
  color: var(--color-text);
}

.popular-products__tab--active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
}

.popular-products__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
}

.popular-products__empty {
  padding: var(--space-6) var(--space-5);
  text-align: center;
  color: var(--color-text-secondary);
  font-size: var(--font-size-body-sm);
  background: var(--color-bg-white);
  border-radius: var(--radius-lg);
}

@media (min-width: 768px) {
  .popular-products__grid {
    grid-template-columns: repeat(3, 1fr);
    gap: var(--space-4);
  }
}

@media (min-width: 1280px) {
  .popular-products__grid {
    grid-template-columns: repeat(6, 1fr);
  }
}
</style>
