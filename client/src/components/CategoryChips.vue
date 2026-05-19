<template>
  <div class="category-chips" data-testid="category-chips">
    <button
      class="category-chips__chip"
      data-testid="category-all"
      :class="{ 'category-chips__chip--active': selectedId === null }"
      @click="select(null)"
    >
      Все
    </button>
    <button
      v-for="cat in categories"
      :key="cat.id"
      class="category-chips__chip"
      :data-testid="'category-chip-' + cat.id"
      :class="{ 'category-chips__chip--active': selectedId === cat.id }"
      @click="select(cat.id)"
    >
      {{ cat.name }}
    </button>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import api from '@/services/api';

const categories = ref([]);
const selectedId = ref(null);

const emit = defineEmits(['select']);

const select = (id) => {
  selectedId.value = id;
  emit('select', id);
};

onMounted(async () => {
  try {
    const { data } = await api.get('/categories');
    categories.value = data;
  } catch {
    // silently fail — chips just won't show
  }
});
</script>

<style scoped>
.category-chips {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 8px 12px;
  background: var(--color-bg-white);
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.category-chips::-webkit-scrollbar {
  display: none;
}

.category-chips__chip {
  flex-shrink: 0;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
  background: var(--color-bg);
  color: var(--color-text);
  border: none;
  white-space: nowrap;
  transition: background 0.15s, color 0.15s;
}

.category-chips__chip--active {
  background: var(--color-primary);
  color: var(--color-white);
}
</style>