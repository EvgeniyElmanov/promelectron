<template>
  <div class="skeleton-profile">
    <!-- Avatar Card -->
    <div class="skeleton-profile__card">
      <div class="skeleton-profile__avatar skeleton" />
      <div class="skeleton-profile__name skeleton" />
      <div class="skeleton-profile__email skeleton" />
    </div>
    <!-- Details Card -->
    <div class="skeleton-profile__card">
      <div class="skeleton-profile__title skeleton" />
      <div class="skeleton-profile__row" v-for="i in 4" :key="i">
        <div class="skeleton-profile__label skeleton" />
        <div class="skeleton-profile__value skeleton" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.skeleton-profile {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

@media (min-width: 768px) {
  .skeleton-profile {
    display: grid;
    grid-template-columns: 300px 1fr;
    gap: 16px;
    align-items: start;
  }
}

.skeleton-profile__card {
  background: var(--color-bg-white);
  border-radius: 14px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.skeleton-profile__avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  margin: 0 auto;
}

.skeleton-profile__name {
  width: 60%;
  height: 16px;
  border-radius: 4px;
  margin: 0 auto;
}

.skeleton-profile__email {
  width: 80%;
  height: 14px;
  border-radius: 4px;
  margin: 0 auto;
}

.skeleton-profile__title {
  width: 50%;
  height: 16px;
  border-radius: 4px;
  margin-bottom: 6px;
}

.skeleton-profile__row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.skeleton-profile__label {
  width: 40%;
  height: 14px;
  border-radius: 4px;
}

.skeleton-profile__value {
  width: 40%;
  height: 14px;
  border-radius: 4px;
}
</style>
