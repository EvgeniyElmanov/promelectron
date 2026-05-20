<template>
  <div class="skeleton-admin">
    <div class="skeleton-admin__header">
      <div class="skeleton-admin__title skeleton" />
      <div class="skeleton-admin__btn skeleton" />
    </div>
    <div class="skeleton-admin__table-wrapper">
      <div class="skeleton-admin__row skeleton-admin__row--head">
        <div class="skeleton-admin__cell skeleton" v-for="i in 4" :key="i" />
      </div>
      <div class="skeleton-admin__row" v-for="row in 5" :key="'r' + row">
        <div class="skeleton-admin__cell skeleton" v-for="i in 4" :key="'c' + i" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.skeleton-admin {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.skeleton-admin__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.skeleton-admin__title {
  width: 200px;
  height: 20px;
  border-radius: 4px;
}

.skeleton-admin__btn {
  width: 120px;
  height: 36px;
  border-radius: 8px;
}

.skeleton-admin__table-wrapper {
  background: var(--color-bg-white);
  border-radius: 12px;
  padding: 16px;
  overflow-x: auto;
}

.skeleton-admin__row {
  display: grid;
  grid-template-columns: 60px 1fr 1fr 100px;
  gap: 12px;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid var(--color-border);
}

.skeleton-admin__row--head {
  padding-bottom: 8px;
  margin-bottom: 4px;
}

.skeleton-admin__row--head .skeleton {
  height: 13px;
}

.skeleton-admin__cell {
  height: 14px;
  border-radius: 4px;
}

.skeleton-admin__row:not(.skeleton-admin__row--head) .skeleton-admin__cell:last-child {
  width: 70%;
}
</style>
