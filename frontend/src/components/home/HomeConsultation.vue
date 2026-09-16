<template>
  <section class="home-consultation" data-testid="home-consultation">
    <div class="home-consultation__inner">
      <h2 class="home-consultation__title">Нужна консультация или закупка для бизнеса?</h2>
      <p class="home-consultation__text">
        Поможем с выбором техники и подготовим предложение для юридических лиц.
      </p>
      <AppButton
        class="home-consultation__cta"
        data-testid="consultation-cta"
        @click="call"
      >
        Оставить заявку
      </AppButton>
    </div>
  </section>
</template>

<script setup>
// Секция Consultation/B2B перед футером (§22, D-11). Отдельного роута обратной
// связи в проекте нет — CTA ведёт на телефон из шапки (tel:88005004585).
import AppButton from '@/components/ui/AppButton.vue';

const call = () => {
  window.location.href = 'tel:88005004585';
};
</script>

<style scoped>
.home-consultation {
  margin: var(--space-6) var(--space-4) 0;
  padding: var(--space-7) var(--space-5);
  background: var(--color-bg-white);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
}

.home-consultation__inner {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-3);
  max-width: 720px;
}

.home-consultation__title {
  font-size: var(--font-size-h2);
  font-weight: var(--font-weight-bold);
  color: var(--color-text);
}

.home-consultation__text {
  font-size: var(--font-size-body);
  color: var(--color-text-secondary);
}

.home-consultation__cta {
  margin-top: var(--space-2);
}
</style>
