<template>
  <div class="home-view" data-testid="home-view">
    <div class="home-view__top">
      <HeroBanner
        class="home-view__hero"
        :category-id="laptopsCategoryId"
        :image-url="heroImageUrl"
      />
      <PromoStack
        :smartphones-category-id="smartphonesCategoryId"
        :smartphones-image-url="smartphonesImageUrl"
      />
    </div>

    <BenefitsStrip />
    <PopularCategories :categories="categories" :loading="categoriesLoading" />
    <PopularProducts ref="popularProductsRef" :initial-tab="initialTab" />
    <HomeConsultation />
    <AppFooter />
  </div>
</template>

<script setup>
// HomeView — витрина главной по макету docs/design/homepage-mockup.png и §22
// (D-02): Hero + промо-колонка → Benefits → Популярные категории →
// Популярные товары → Consultation/B2B → Footer. Инлайн-каталога нет —
// листинг живёт на /catalog.
// Данные: один запрос /categories/ на страницу (NFR ≤3 API-запроса), id целевых
// категорий резолвятся по имени (fallback — /catalog без фильтра, D-05/D-06);
// hero-фото — первый товар категории ноутбуков с непустым images.
// Промо «Распродажа»/«Скидки» (CategoryNav, PromoStack) ведут на /?tab=sale —
// здесь watch активирует таб «Скидки» и скроллит к секции.
import { ref, computed, onMounted, watch, nextTick } from 'vue';
import { useRoute } from 'vue-router';
import HeroBanner from '@/components/home/HeroBanner.vue';
import PromoStack from '@/components/home/PromoStack.vue';
import BenefitsStrip from '@/components/home/BenefitsStrip.vue';
import PopularCategories from '@/components/home/PopularCategories.vue';
import PopularProducts from '@/components/home/PopularProducts.vue';
import HomeConsultation from '@/components/home/HomeConsultation.vue';
import AppFooter from '@/components/AppFooter.vue';
import { getImageUrl } from '@/composables/useImageUrl';
import api from '@/services/api';

const route = useRoute();

const categories = ref([]);
const categoriesLoading = ref(true);
const heroImageUrl = ref(null);
const popularProductsRef = ref(null);

// Имя категории в БД может отличаться от макета (1С-дамп) — ищем по ключевому
// слову case-insensitive (fallback без категории задокументирован в D-05/D-06).
const findCategoryId = (keyword) => {
  const needle = keyword.toLowerCase();
  const cat = categories.value.find((c) => c.name?.toLowerCase().includes(needle));
  return cat ? cat.id : null;
};

const laptopsCategoryId = computed(() => findCategoryId('ноутбук'));
const smartphonesCategoryId = computed(() => findCategoryId('смартфон'));

const smartphonesImageUrl = computed(() => {
  const id = smartphonesCategoryId.value;
  if (!id) return null;
  const cat = categories.value.find((c) => c.id === id);
  return cat?.image_url ? getImageUrl(cat.image_url, 'medium') : null;
});

const fetchHeroImage = async (categoryId) => {
  if (!categoryId) return;
  try {
    const { data } = await api.get('/products/', {
      params: { skip: 0, limit: 20, category_id: categoryId },
    });
    const withImage = (data.items || []).find((p) => p.images?.length);
    if (withImage) heroImageUrl.value = getImageUrl(withImage.images[0], 'medium');
  } catch {
    // без фото — чистый тёмный баннер (D-05)
  }
};

const initialTab = computed(() => (route.query.tab === 'sale' ? 'sale' : 'hits'));

watch(
  () => route.query.tab,
  async (tab) => {
    if (tab !== 'sale') return;
    await nextTick();
    popularProductsRef.value?.setTab('sale');
    document
      .getElementById('popular-products')
      ?.scrollIntoView({ behavior: 'smooth' });
  },
);

onMounted(async () => {
  try {
    const { data } = await api.get('/categories/', { params: { skip: 0, limit: 100 } });
    categories.value = data.items || [];
  } catch {
    categories.value = [];
  } finally {
    categoriesLoading.value = false;
  }
  fetchHeroImage(laptopsCategoryId.value);

  // Прямая загрузка /?tab=sale: таб уже открыт через initialTab — доскроллить
  // до секции (F-05; watch выше срабатывает только на смену query после mount).
  if (route.query.tab === 'sale') {
    await nextTick();
    document
      .getElementById('popular-products')
      ?.scrollIntoView({ behavior: 'smooth' });
  }
});
</script>

<style scoped>
.home-view {
  background: var(--color-bg);
}

@media (min-width: 1024px) {
  .home-view__top {
    display: flex;
    align-items: stretch;
  }

  .home-view__hero {
    flex: 1;
    min-width: 0;
  }
}
</style>
