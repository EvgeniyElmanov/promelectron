<template>
  <section class="benefits-strip" data-testid="benefits-strip" aria-label="Преимущества">
    <ul class="benefits-strip__list">
      <li v-for="benefit in benefits" :key="benefit.title" class="benefits-strip__item">
        <span class="benefits-strip__icon" aria-hidden="true" v-html="benefit.icon" />
        <span class="benefits-strip__text">
          <span class="benefits-strip__title">{{ benefit.title }}</span>
          <span class="benefits-strip__description">{{ benefit.description }}</span>
        </span>
      </li>
    </ul>
  </section>
</template>

<script setup>
// Статичный контент (D-07) по растру homepage-mockup.png — 4 карточки.
// Иконки — inline SVG в стиле Lucide, как в Header/ProductCard.
const icons = {
  truck: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 8h14v9H1z"/><path d="M15 11h4l3 3v3h-7z"/><circle cx="6" cy="19" r="2"/><circle cx="18" cy="19" r="2"/></svg>',
  package: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 8l-9-5-9 5v8l9 5 9-5z"/><path d="M3 8l9 5 9-5"/><path d="M12 13v8"/></svg>',
  headphones: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 18v-6a9 9 0 0118 0v6"/><path d="M3 18a2 2 0 002 2h1v-6H5a2 2 0 00-2 2zm18 0a2 2 0 01-2 2h-1v-6h1a2 2 0 012 2z"/></svg>',
  shield: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-3.5 8-10V5l-8-3-8 3v7c0 6.5 8 10 8 10z"/><path d="M9 12l2 2 4-4"/></svg>',
};

const benefits = [
  { title: 'Официальная гарантия', description: 'Вся продукция сертифицирована', icon: icons.shield },
  { title: 'Доставка по всей России', description: 'Быстро и надёжно', icon: icons.truck },
  { title: 'Оплата удобным способом', description: 'Наличные, карта, онлайн', icon: icons.package },
  { title: 'Поддержка 24/7', description: 'Мы всегда на связи', icon: icons.headphones },
];
</script>

<style scoped>
.benefits-strip {
  padding: var(--space-4) var(--space-4) 0;
}

.benefits-strip__list {
  list-style: none;
  padding: 0;
  display: flex;
  gap: var(--space-4);
  overflow-x: auto;
  scrollbar-width: none;
}

.benefits-strip__list::-webkit-scrollbar {
  display: none;
}

.benefits-strip__item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-shrink: 0;
  min-width: 200px;
}

.benefits-strip__icon {
  color: var(--color-primary);
  display: inline-flex;
  flex-shrink: 0;
}

.benefits-strip__text {
  display: flex;
  flex-direction: column;
}

.benefits-strip__title {
  font-size: var(--font-size-body-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-text);
}

.benefits-strip__description {
  font-size: var(--font-size-caption);
  color: var(--color-text-secondary);
}

@media (min-width: 1024px) {
  .benefits-strip__list {
    justify-content: space-between;
    overflow: visible;
  }

  .benefits-strip__item {
    min-width: 0;
  }
}
</style>
