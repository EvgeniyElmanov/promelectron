<template>
  <section class="hero-banner" data-testid="hero-banner">
    <div class="hero-banner__content">
      <h2 class="hero-banner__title">Техника для работы без компромиссов</h2>
      <p class="hero-banner__description">
        Надёжные решения для бизнеса и дома. Всегда в наличии на складе.
      </p>
      <div class="hero-banner__actions">
        <AppButton data-testid="hero-cta-catalog" @click="$emit('cta-click')">
          Перейти в каталог
        </AppButton>
        <AppButton variant="ghost" class="hero-banner__cta-secondary" data-testid="hero-cta-new" @click="$emit('show-new')">
          Смотреть новинки
        </AppButton>
      </div>
    </div>

    <ul class="hero-banner__facts">
      <li v-for="fact in facts" :key="fact" class="hero-banner__fact">{{ fact }}</li>
    </ul>

    <div class="hero-banner__dots" aria-hidden="true">
      <span class="hero-banner__dot hero-banner__dot--active" />
      <span class="hero-banner__dot" />
      <span class="hero-banner__dot" />
    </div>
  </section>
</template>

<script setup>
import AppButton from '@/components/ui/AppButton.vue';

// Контент статичный (D-04), адаптирован из docs/design/metadata.json sections.hero.
// Carousel — декоративные доты, 1 слайд, без JS-карусели (D-08).
const facts = [
  'Более 25 лет на рынке',
  'Тысячи товаров в наличии',
  'Доставка по всей России',
];

defineEmits(['cta-click', 'show-new']);
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

.hero-banner__actions {
  display: flex;
  gap: var(--space-3);
  margin-top: var(--space-5);
  flex-wrap: wrap;
}

.hero-banner__cta-secondary {
  color: var(--color-white);
  border: 1px solid rgba(255, 255, 255, 0.35);
  background: transparent;
}

.hero-banner__facts {
  list-style: none;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  font-size: var(--font-size-body-sm);
  color: rgba(255, 255, 255, 0.75);
}

.hero-banner__dots {
  position: absolute;
  bottom: var(--space-4);
  left: var(--space-6);
  display: flex;
  gap: var(--space-2);
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

@media (min-width: 768px) {
  .hero-banner {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    min-height: 271px;
    padding: var(--space-7) var(--space-8);
  }

  .hero-banner__facts {
    text-align: right;
    flex-shrink: 0;
  }
}
</style>
