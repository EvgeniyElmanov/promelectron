<template>
  <nav class="app-breadcrumbs" aria-label="Хлебные крошки" data-testid="app-breadcrumbs">
    <ol class="app-breadcrumbs__list">
      <li
        v-for="(item, index) in items"
        :key="index"
        class="app-breadcrumbs__item"
      >
        <RouterLink
          v-if="item.to && index < items.length - 1"
          :to="item.to"
          class="app-breadcrumbs__link"
        >
          {{ item.label }}
        </RouterLink>
        <span
          v-else
          class="app-breadcrumbs__current"
          :aria-current="index === items.length - 1 ? 'page' : undefined"
        >
          {{ item.label }}
        </span>
        <span v-if="index < items.length - 1" class="app-breadcrumbs__sep" aria-hidden="true">/</span>
      </li>
    </ol>
  </nav>
</template>

<script setup>
defineProps({
  items: {
    type: Array,
    required: true,
    validator: (value) => value.every((item) => item && typeof item.label === 'string'),
  },
});
</script>

<style scoped>
.app-breadcrumbs__list {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: var(--space-2);
  list-style: none;
  padding: 0;
  overflow: hidden;
  white-space: nowrap;
}

.app-breadcrumbs__item {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
  font-size: var(--font-size-body-sm);
  color: var(--color-text-muted);
}

.app-breadcrumbs__link {
  color: var(--color-text-muted);
  text-decoration: none;
  overflow: hidden;
  text-overflow: ellipsis;
}

.app-breadcrumbs__link:hover {
  color: var(--color-primary);
}

.app-breadcrumbs__current {
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
}

.app-breadcrumbs__sep {
  color: var(--color-text-muted);
  flex-shrink: 0;
}
</style>
