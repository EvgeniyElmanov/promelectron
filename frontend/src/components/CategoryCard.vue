<template>
  <button
    class="category-card"
    :data-testid="'category-card-' + id"
    @click="$emit('select', id)"
  >
    <span class="category-card__image" :style="imageUrl ? {} : { background: placeholderBg }">
      <img
        v-if="imageUrl"
        :src="imageUrl"
        class="category-card__img"
        alt=""
        loading="lazy"
        decoding="async"
      />
      <span v-else class="category-card__image-letter" aria-hidden="true">{{ name.charAt(0) }}</span>
    </span>
    <span class="category-card__name">{{ name }}</span>
    <span v-if="productCount != null" class="category-card__count">{{ productCount }} товаров</span>
  </button>
</template>

<script setup>
import { computed } from 'vue';
import { getPlaceholderBg } from '@/utils/placeholderColors';

const props = defineProps({
  id: { type: [Number, String], required: true },
  name: { type: String, required: true },
  productCount: { type: Number, default: null },
  imageUrl: { type: String, default: null },
});

defineEmits(['select']);

const placeholderBg = computed(() => getPlaceholderBg(props.id));
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

.category-card__image-letter {
  font-size: 32px;
  font-weight: var(--font-weight-bold);
  color: rgba(0, 0, 0, 0.12);
  user-select: none;
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
