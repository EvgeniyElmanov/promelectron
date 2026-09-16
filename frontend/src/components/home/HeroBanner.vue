<template>
  <section class="hero-banner" data-testid="hero-banner">
    <div class="hero-banner__content">
      <h1 class="hero-banner__title">Новый уровень производительности</h1>
      <p class="hero-banner__description">
        Современные ноутбуки для работы, учёбы и развлечений
      </p>
      <AppButton
        class="hero-banner__cta"
        data-testid="hero-cta-laptops"
        @click="goToLaptops"
      >
        Смотреть ноутбуки
      </AppButton>
      <div class="hero-banner__dots" aria-hidden="true">
        <span class="hero-banner__dot hero-banner__dot--active" />
        <span class="hero-banner__dot" />
        <span class="hero-banner__dot" />
        <span class="hero-banner__dot" />
      </div>
    </div>

    <div v-if="imageUrl" class="hero-banner__media" aria-hidden="true">
      <img :src="imageUrl" class="hero-banner__img" alt="" data-testid="hero-image" decoding="async" />
    </div>
  </section>
</template>

<script setup>
// Hero главной по макету docs/design/homepage-mockup.png (D-05):
// один слайд, декоративные доты без JS-карусели; CTA ведёт в каталог
// ноутбуков (id категории резолвит HomeView по имени, fallback — /catalog);
// фото ноутбука — из API (первый товар категории с изображением),
// без фото — чистый тёмный баннер. На mobile фото скрыто (по макету).
import { useRouter } from 'vue-router';
import AppButton from '@/components/ui/AppButton.vue';

const props = defineProps({
  categoryId: { type: [Number, String], default: null },
  imageUrl: { type: String, default: null },
});

const router = useRouter();

const goToLaptops = () => {
  if (props.categoryId) {
    router.push({ path: '/catalog', query: { category_id: String(props.categoryId) } });
  } else {
    router.push('/catalog');
  }
};
</script>

<style scoped>
.hero-banner {
  position: relative;
  margin: var(--space-3) var(--space-4) 0;
  padding: var(--space-6) var(--space-5);
  background: var(--color-dark);
  border-radius: var(--radius-md);
  color: var(--color-white);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  overflow: hidden;
}

.hero-banner__title {
  font-size: var(--font-size-h1);
  font-weight: var(--font-weight-bold);
  line-height: 1.15;
  max-width: 560px;
}

.hero-banner__description {
  margin-top: var(--space-3);
  font-size: var(--font-size-body);
  color: rgba(255, 255, 255, 0.75);
  max-width: 480px;
}

.hero-banner__cta {
  margin-top: var(--space-5);
  align-self: flex-start;
}

.hero-banner__dots {
  display: flex;
  gap: var(--space-2);
  margin-top: var(--space-5);
}

.hero-banner__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.35);
}

.hero-banner__dot--active {
  background: var(--color-white);
}

.hero-banner__media {
  display: none;
}

@media (min-width: 1024px) {
  .hero-banner {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    min-height: 320px;
    padding: var(--space-7) var(--space-8);
  }

  .hero-banner__media {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    flex-shrink: 0;
    max-width: 50%;
  }

  .hero-banner__img {
    max-width: 100%;
    max-height: 280px;
    object-fit: contain;
    border-radius: var(--radius-md);
  }
}
</style>
