<template>
  <section
    v-if="loading || rootCategories.length > 0"
    class="popular-categories"
    data-testid="popular-categories"
  >
    <div class="popular-categories__header">
      <h2 class="popular-categories__title">Популярные категории</h2>
      <button
        v-if="hasMoreCategories"
        class="popular-categories__view-all"
        data-testid="categories-view-all"
        @click="$emit('view-all')"
      >
        Смотреть все категории
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M9 18l6-6-6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
    </div>

    <div v-if="loading" class="popular-categories__grid">
      <div v-for="i in 8" :key="'sk' + i" class="popular-categories__skeleton" />
    </div>

    <div v-else class="popular-categories__grid">
      <CategoryCard
        v-for="cat in rootCategories"
        :key="cat.id"
        :id="cat.id"
        :name="cat.name"
        :product-count="cat.product_count"
        @select="(id) => $emit('select', id)"
      />
    </div>
  </section>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import CategoryCard from '@/components/CategoryCard.vue';
import api from '@/services/api';

const MAX_CARDS = 8;

const categories = ref([]);
const loading = ref(true);

defineEmits(['select', 'view-all']);

const rootCategoriesAll = computed(() =>
  categories.value.filter((cat) => cat.parent_id === null)
);

const rootCategories = computed(() => rootCategoriesAll.value.slice(0, MAX_CARDS));

const hasMoreCategories = computed(() => rootCategoriesAll.value.length > MAX_CARDS);

onMounted(async () => {
  try {
    const { data } = await api.get('/categories/');
    categories.value = data.items || [];
  } catch {
    // silently fail — секция скрывается, листинг работает (S-03)
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.popular-categories {
  padding: var(--space-5) var(--space-4);
}

.popular-categories__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}

.popular-categories__title {
  font-size: var(--font-size-h2);
  font-weight: var(--font-weight-bold);
  color: var(--color-text);
}

.popular-categories__view-all {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  background: none;
  border: none;
  padding: var(--space-2);
  font-size: var(--font-size-body-sm);
  color: var(--color-primary);
  cursor: pointer;
  flex-shrink: 0;
}

.popular-categories__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
}

.popular-categories__skeleton {
  aspect-ratio: 1;
  border-radius: var(--radius-lg);
  background: var(--color-bg-white);
  animation: popular-categories-pulse 1.5s ease-in-out infinite;
}

@keyframes popular-categories-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@media (min-width: 768px) {
  .popular-categories__grid {
    grid-template-columns: repeat(4, 1fr);
    gap: var(--space-4);
  }
}

@media (min-width: 1280px) {
  .popular-categories__grid {
    grid-template-columns: repeat(8, 1fr);
  }
}
</style>
