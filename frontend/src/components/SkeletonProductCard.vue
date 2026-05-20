<template>
  <div class="skeleton-card">
    <div class="skeleton-card__image skeleton" />
    <div class="skeleton-card__body">
      <div class="skeleton-card__price skeleton" />
      <div class="skeleton-card__name skeleton" />
      <div class="skeleton-card__name skeleton skeleton--short" />
      <div class="skeleton-card__btn skeleton" />
    </div>
  </div>
</template>

<style scoped>
.skeleton-card {
  background: var(--color-bg-white);
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.skeleton-card__image {
  aspect-ratio: 1;
  border-radius: 0;
}

.skeleton-card__body {
  padding: 8px 10px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.skeleton-card__price {
  width: 60%;
  height: 17px;
  border-radius: 4px;
}

.skeleton-card__name {
  width: 90%;
  height: 15px;
  border-radius: 4px;
}

.skeleton-card__name.skeleton--short {
  width: 55%;
}

.skeleton-card__btn {
  width: 100%;
  height: 29px;
  border-radius: 8px;
  margin-top: 4px;
}
</style>
