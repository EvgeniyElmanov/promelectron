<template>
  <section
    v-if="loading || categories.length > 0"
    class="popular-categories"
    data-testid="popular-categories"
  >
    <div class="popular-categories__header">
      <h2 class="popular-categories__title">Популярные категории</h2>
      <RouterLink
        to="/catalog"
        class="popular-categories__view-all"
        data-testid="categories-view-all"
      >
        Все категории
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M9 18l6-6-6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </RouterLink>
    </div>

    <div v-if="loading" class="popular-categories__grid">
      <div v-for="i in 6" :key="'sk' + i" class="popular-categories__skeleton" />
    </div>

    <div v-else class="popular-categories__grid">
      <CategoryCard
        v-for="cat in rootCategories"
        :key="cat.id"
        :id="cat.id"
        :name="cat.name"
        :product-count="cat.product_count"
        :image-url="cat.image_url ? getImageUrl(cat.image_url, 'medium') : null"
        @select="onSelect"
      />
    </div>
  </section>
</template>

<script setup>
// «Популярные категории» главной (D-07, §14): 6 карточек в ряд на desktop
// с фото из CategoryOut.image_url (optional, D-03 — без поля placeholder-плитка),
// именем и счётчиком «N товаров». Клик ведёт на /catalog?category_id=<id>.
// Mobile: компактная сетка 4 колонки с горизонтальным скроллом при переполнении.
// Категории приходят пропсом от HomeView (один запрос на страницу, NFR ≤3 API).
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import CategoryCard from '@/components/CategoryCard.vue';
import { getImageUrl } from '@/composables/useImageUrl';

const props = defineProps({
  categories: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
});

const router = useRouter();

const MAX_CARDS = 6;

const rootCategories = computed(() =>
  props.categories.filter((cat) => cat.parent_id === null).slice(0, MAX_CARDS)
);

const onSelect = (id) => {
  router.push({ path: '/catalog', query: { category_id: String(id) } });
};
</script>

<style scoped>
.popular-categories {
  padding: var(--space-6) var(--space-4) 0;
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
  padding: var(--space-2);
  font-size: var(--font-size-body-sm);
  color: var(--color-primary);
  text-decoration: none;
  flex-shrink: 0;
}

.popular-categories__grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(90px, 1fr));
  gap: var(--space-3);
  overflow-x: auto;
  scrollbar-width: none;
}

.popular-categories__grid::-webkit-scrollbar {
  display: none;
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

@media (min-width: 1024px) {
  .popular-categories__grid {
    grid-template-columns: repeat(6, 1fr);
    gap: var(--space-4);
    overflow: visible;
  }
}
</style>
