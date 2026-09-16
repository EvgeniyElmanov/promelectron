<template>
  <button
    class="category-card"
    :data-testid="'category-card-' + id"
    @click="$emit('select', id)"
  >
    <span class="category-card__image">
      <img
        v-if="imageUrl"
        :src="imageUrl"
        class="category-card__img"
        alt=""
        loading="lazy"
        decoding="async"
      />
      <svg v-else class="category-card__image-placeholder" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <rect x="3" y="3" width="18" height="18" rx="2"/>
        <circle cx="9" cy="9" r="2"/>
        <path d="M21 15l-4.5-4.5L6 21"/>
      </svg>
    </span>
    <span class="category-card__name">{{ name }}</span>
    <span v-if="productCount != null" class="category-card__count">{{ productCount }} товаров</span>
  </button>
</template>

<script setup>
// CategoryCard (§14, D-07): фото из CategoryOut.image_url; без изображения —
// нейтральный placeholder (иконка на --color-bg), не буква-заглушка (edge case spec).
defineProps({
  id: { type: [Number, String], required: true },
  name: { type: String, required: true },
  productCount: { type: Number, default: null },
  imageUrl: { type: String, default: null },
});

defineEmits(['select']);
</script>

<style scoped>
.category-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--space-2);
  padding: var(--space-3);
  background: var(--color-bg-white);
  border: none;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  cursor: pointer;
  text-align: left;
  transition: box-shadow 0.2s;
}

.category-card:hover {
  box-shadow: var(--shadow-card-hover);
}

.category-card__image {
  width: 100%;
  aspect-ratio: 4 / 3;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: var(--color-bg);
  transition: transform 0.2s;
}

.category-card:hover .category-card__image {
  transform: scale(1.03);
}

.category-card__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.category-card__image-placeholder {
  color: var(--color-text-muted);
  opacity: 0.5;
}

.category-card__name {
  font-size: var(--font-size-body-sm);
  font-weight: var(--font-weight-medium);
  color: var(--color-text);
}

.category-card__count {
  font-size: var(--font-size-caption);
  color: var(--color-text-muted);
}
</style>
