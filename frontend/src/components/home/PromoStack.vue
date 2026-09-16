<template>
  <aside class="promo-stack" data-testid="promo-stack" aria-label="Акции">
    <button class="promo-stack__card" data-testid="promo-smartphones" @click="goToSmartphones">
      <span
        class="promo-stack__bg"
        :style="smartphonesImageUrl ? { backgroundImage: `url(${smartphonesImageUrl})` } : {}"
        aria-hidden="true"
      />
      <span class="promo-stack__text">
        <span class="promo-stack__title">Смартфоны</span>
        <span class="promo-stack__subtitle">Новинки и хиты продаж</span>
        <span class="promo-stack__link">Смотреть →</span>
      </span>
    </button>

    <button class="promo-stack__card promo-stack__card--sale" data-testid="promo-sale" @click="goToSale">
      <span class="promo-stack__percent" aria-hidden="true">%</span>
      <span class="promo-stack__text">
        <span class="promo-stack__title">Скидки до 30%</span>
        <span class="promo-stack__subtitle">На популярные товары</span>
        <span class="promo-stack__link">Перейти к акциям →</span>
      </span>
    </button>
  </aside>
</template>

<script setup>
// Промо-колонка справа от hero на desktop (D-06, макет homepage-mockup.png).
// «Смартфоны» → категория «Смартфоны и гаджеты» в каталоге (fallback /catalog);
// фон — image_url категории из API (optional, D-03), без него — чистая карточка.
// «Скидки до 30%» → таб «Скидки» главной (/?tab=sale, скролл к секции в HomeView);
// графика «%» — текстом, не картинкой. На mobile скрыта (по макету).
import { useRouter } from 'vue-router';

const props = defineProps({
  smartphonesCategoryId: { type: [Number, String], default: null },
  smartphonesImageUrl: { type: String, default: null },
});

const router = useRouter();

const goToSmartphones = () => {
  if (props.smartphonesCategoryId) {
    router.push({ path: '/catalog', query: { category_id: String(props.smartphonesCategoryId) } });
  } else {
    router.push('/catalog');
  }
};

const goToSale = () => {
  router.push({ path: '/', query: { tab: 'sale' } });
};
</script>

<style scoped>
.promo-stack {
  display: none;
}

@media (min-width: 1024px) {
  .promo-stack {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
    margin: var(--space-3) var(--space-4) 0;
    flex: 0 0 300px;
  }

  .promo-stack__card {
    position: relative;
    flex: 1;
    display: flex;
    align-items: flex-end;
    padding: var(--space-4);
    background: var(--color-bg-white);
    border: none;
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-card);
    cursor: pointer;
    text-align: left;
    overflow: hidden;
    font-family: inherit;
    transition: box-shadow 0.2s;
  }

  .promo-stack__card:hover {
    box-shadow: var(--shadow-card-hover);
  }

  .promo-stack__bg {
    position: absolute;
    inset: 0;
    background-size: cover;
    background-position: center;
    opacity: 0.25;
    pointer-events: none;
  }

  .promo-stack__text {
    position: relative;
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
  }

  .promo-stack__title {
    font-size: var(--font-size-h3);
    font-weight: var(--font-weight-bold);
    color: var(--color-text);
  }

  .promo-stack__subtitle {
    font-size: var(--font-size-body-sm);
    color: var(--color-text-secondary);
  }

  .promo-stack__link {
    margin-top: var(--space-2);
    font-size: var(--font-size-body-sm);
    font-weight: var(--font-weight-medium);
    color: var(--color-primary);
  }

  .promo-stack__percent {
    position: absolute;
    top: var(--space-3);
    right: var(--space-4);
    font-size: 64px;
    font-weight: var(--font-weight-bold);
    color: var(--color-primary-light);
    line-height: 1;
    pointer-events: none;
  }
}
</style>
