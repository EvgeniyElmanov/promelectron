<template>
  <div class="skeleton-pdp">
    <!-- Image -->
    <div class="skeleton-pdp__gallery">
      <div class="skeleton-pdp__image skeleton" />
      <div class="skeleton-pdp__thumbs">
        <div class="skeleton-pdp__thumb skeleton" v-for="i in 4" :key="i" />
      </div>
    </div>
    <!-- Info -->
    <div class="skeleton-pdp__info">
      <div class="skeleton-pdp__price skeleton" />
      <div class="skeleton-pdp__rating skeleton" />
      <div class="skeleton-pdp__actions">
        <div class="skeleton-pdp__btn skeleton" />
        <div class="skeleton-pdp__btn skeleton skeleton--small" />
      </div>
      <!-- Description -->
      <div class="skeleton-pdp__section">
        <div class="skeleton-pdp__section-title skeleton" />
        <div class="skeleton-pdp__text skeleton" v-for="i in 3" :key="i" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.skeleton-pdp {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

@media (min-width: 768px) {
  .skeleton-pdp {
    flex-direction: row;
    gap: 20px;
    padding: 20px;
  }
}

.skeleton-pdp__gallery {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

@media (min-width: 768px) {
  .skeleton-pdp__gallery {
    flex: 0 0 45%;
    max-width: 500px;
  }
}

.skeleton-pdp__image {
  aspect-ratio: 1;
  border-radius: 12px;
}

@media (min-width: 768px) {
  .skeleton-pdp__image {
    aspect-ratio: 4 / 3;
  }
}

.skeleton-pdp__thumbs {
  display: flex;
  gap: 8px;
}

.skeleton-pdp__thumb {
  width: 56px;
  height: 56px;
  border-radius: 8px;
}

.skeleton-pdp__info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 0 12px;
}

.skeleton-pdp__price {
  width: 40%;
  height: 32px;
  border-radius: 6px;
}

.skeleton-pdp__rating {
  width: 30%;
  height: 20px;
  border-radius: 4px;
}

.skeleton-pdp__actions {
  display: flex;
  gap: 10px;
}

.skeleton-pdp__btn {
  flex: 1;
  height: 48px;
  border-radius: 12px;
}

.skeleton-pdp__btn.skeleton--small {
  flex: 0 0 48px;
}

.skeleton-pdp__section {
  background: var(--color-bg-white);
  border-radius: 12px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.skeleton-pdp__section-title {
  width: 40%;
  height: 16px;
  border-radius: 4px;
  margin-bottom: 4px;
}

.skeleton-pdp__text {
  width: 100%;
  height: 12px;
  border-radius: 4px;
}

.skeleton-pdp__text:nth-child(3) {
  width: 70%;
}
</style>
