<template>
  <div class="skeleton-order">
    <div class="skeleton-order__header">
      <div class="skeleton-order__id skeleton" />
      <div class="skeleton-order__date skeleton" />
    </div>
    <div class="skeleton-order__divider" />
    <div class="skeleton-order__body">
      <div class="skeleton-order__row skeleton" />
      <div class="skeleton-order__row skeleton skeleton--short" />
    </div>
  </div>
</template>

<style scoped>
.skeleton-order {
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 16px;
  background: var(--color-bg-white);
}

.skeleton-order__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.skeleton-order__id {
  width: 100px;
  height: 16px;
  border-radius: 4px;
}

.skeleton-order__date {
  width: 80px;
  height: 14px;
  border-radius: 4px;
}

.skeleton-order__divider {
  height: 1px;
  background: var(--color-border);
  margin-bottom: 10px;
}

.skeleton-order__row {
  width: 70%;
  height: 14px;
  border-radius: 4px;
  margin-bottom: 8px;
}

.skeleton-order__row.skeleton--short {
  width: 45%;
  margin-bottom: 0;
}
</style>
