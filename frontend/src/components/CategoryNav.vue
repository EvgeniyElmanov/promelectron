<template>
  <nav
    v-if="rootCategories.length > 0"
    class="category-nav"
    data-testid="category-nav"
    aria-label="Категории"
  >
    <div class="category-nav__inner">
      <RouterLink
        v-for="cat in visibleCategories"
        :key="cat.id"
        :to="{ path: '/catalog', query: { category_id: String(cat.id) } }"
        class="category-nav__link"
        :data-testid="`category-nav-link-${cat.id}`"
      >
        {{ cat.name }}
      </RouterLink>
      <RouterLink
        v-if="hasMore"
        to="/catalog"
        class="category-nav__link category-nav__link--more"
        data-testid="category-nav-more"
      >
        Ещё
      </RouterLink>
      <RouterLink
        :to="{ path: '/', query: { tab: 'sale' } }"
        class="category-nav__link category-nav__link--sale"
        data-testid="category-nav-sale"
      >
        Распродажа
      </RouterLink>
    </div>
  </nav>
</template>

<script setup>
// Строка категорийной навигации под шапкой (§11, D-10): корневые категории из
// /categories/ (до 7 + «Ещё» → /catalog), красная «Распродажа» → таб «Скидки»
// главной (/?tab=sale). «Бренды» не рендерится — данных/страницы нет (D-10).
// Desktop-only; на mobile категории доступны через бургер-меню.
// При ошибке API строка скрывается, страница не валится (S-05).
import { ref, computed, onMounted } from 'vue';
import api from '@/services/api';

const MAX_LINKS = 7;

const categories = ref([]);

const rootCategories = computed(() =>
  categories.value.filter((cat) => cat.parent_id === null)
);

const visibleCategories = computed(() => rootCategories.value.slice(0, MAX_LINKS));
const hasMore = computed(() => rootCategories.value.length > MAX_LINKS);

onMounted(async () => {
  try {
    const { data } = await api.get('/categories/', { params: { skip: 0, limit: 100 } });
    categories.value = data.items || [];
  } catch {
    categories.value = [];
  }
});
</script>

<style scoped>
.category-nav {
  display: none;
}

@media (min-width: 1024px) {
  .category-nav {
    display: block;
    background: var(--color-bg-white);
    border-bottom: 1px solid var(--color-border);
  }

  .category-nav__inner {
    display: flex;
    align-items: center;
    gap: var(--space-5);
    padding: 0 var(--space-4);
    height: 44px;
    overflow-x: auto;
    scrollbar-width: none;
  }

  .category-nav__inner::-webkit-scrollbar {
    display: none;
  }

  .category-nav__link {
    font-size: var(--font-size-body-sm);
    font-weight: var(--font-weight-medium);
    color: var(--color-text);
    text-decoration: none;
    white-space: nowrap;
    transition: color 0.15s;
  }

  .category-nav__link:hover {
    color: var(--color-primary);
  }

  .category-nav__link--sale {
    color: var(--color-danger);
  }

  .category-nav__link--sale:hover {
    color: var(--color-danger);
    text-decoration: underline;
  }
}
</style>
