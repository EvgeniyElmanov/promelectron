<template>
  <div class="skeleton-cart-item">
    <div class="skeleton-cart-item__image skeleton" />
    <div class="skeleton-cart-item__info">
      <div class="skeleton-cart-item__name skeleton" />
      <div class="skeleton-cart-item__name skeleton skeleton--short" />
      <div class="skeleton-cart-item__bottom">
        <div class="skeleton-cart-item__qty skeleton" />
        <div class="skeleton-cart-item__total skeleton" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.skeleton-cart-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  background: var(--color-bg-white);
  border-radius: 14px;
}

.skeleton-cart-item__image {
  width: 72px;
  height: 72px;
  border-radius: 10px;
  flex-shrink: 0;
}

.skeleton-cart-item__info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.skeleton-cart-item__name {
  width: 80%;
  height: 14px;
  border-radius: 4px;
}

.skeleton-cart-item__name.skeleton--short {
  width: 50%;
}

.skeleton-cart-item__bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 4px;
}

.skeleton-cart-item__qty {
  width: 80px;
  height: 32px;
  border-radius: 10px;
}

.skeleton-cart-item__total {
  width: 60px;
  height: 18px;
  border-radius: 4px;
}
</style>
