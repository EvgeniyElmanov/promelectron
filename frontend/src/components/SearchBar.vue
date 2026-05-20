<template>
  <div class="search-bar">
    <div class="search-bar__input-wrapper">
      <svg class="search-bar__icon" viewBox="0 0 24 24" width="18" height="18" fill="none">
        <circle cx="11" cy="11" r="6" stroke="#999" stroke-width="2"/>
        <path d="M20 20l-3.5-3.5" stroke="#999" stroke-width="2" stroke-linecap="round"/>
      </svg>
      <input
        type="text"
        class="search-bar__input"
        data-testid="search-bar"
        placeholder="Поиск товаров..."
        :value="modelValue"
        @input="$emit('update:modelValue', $event.target.value)"
      />
    </div>
  </div>
</template>

<script setup>
defineProps({
  modelValue: {
    type: String,
    default: '',
  },
});

defineEmits(['update:modelValue']);
</script>

<style scoped>
.search-bar {
  padding: 8px 12px;
  background: var(--color-bg-white);
}

.search-bar__input-wrapper {
  display: flex;
  align-items: center;
  background: var(--color-bg);
  border-radius: 12px;
  padding: 0 12px;
  height: 40px;
}

.search-bar__icon {
  flex-shrink: 0;
  margin-right: 8px;
}

.search-bar__input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 15px;
  color: var(--color-text);
  outline: none;
}

.search-bar__input::placeholder {
  color: #aaa;
}
</style>