<template>
  <div class="autocomplete" ref="containerRef">
    <input
      :value="modelValue"
      @input="onInput"
      @keydown="onKeydown"
      @focus="onFocus"
      @blur="onBlur"
      type="text"
      :placeholder="placeholder"
      class="address-field__input"
      :data-testid="testid"
      autocomplete="off"
    />
    <div v-if="showDropdown && filteredOptions.length" class="autocomplete__dropdown">
      <div
        v-for="(opt, i) in filteredOptions"
        :key="opt.value || opt"
        class="autocomplete__item"
        :class="{ 'autocomplete__item--active': i === activeIndex }"
        @mousedown.prevent="selectOption(opt)"
      >
        {{ opt.label || opt }}
      </div>
    </div>
    <div v-else-if="showDropdown && isLoading" class="autocomplete__dropdown autocomplete__dropdown--empty">
      <span class="autocomplete__loading">Загрузка…</span>
    </div>
    <div v-else-if="showDropdown && hasTyped && !filteredOptions.length && !isLoading" class="autocomplete__dropdown autocomplete__dropdown--empty">
      <span>Ничего не найдено</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { useAddressSuggestions } from '@/composables/useAddressSuggestions';

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  field: { type: String, required: true },
  context: { type: Object, default: () => ({}) },
  testid: { type: String, default: '' },
  options: { type: Array, default: null }, // local list of strings
});

const emit = defineEmits(['update:modelValue', 'select']);

const { isLoading, fetchSuggestions } = useAddressSuggestions();
const suggestions = ref([]);
const activeIndex = ref(-1);
const showDropdown = ref(false);
const hasTyped = ref(false);
const containerRef = ref(null);
let debounceTimer = null;

// Local options filtering
const filteredOptions = computed(() => {
  if (props.options) {
    const q = props.modelValue.toLowerCase().trim();
    if (!q) return props.options;
    return props.options.filter((o) => o.toLowerCase().includes(q));
  }
  return suggestions.value;
});

function selectOption(opt) {
  const value = typeof opt === 'string' ? opt : opt.value || opt.label || '';
  emit('update:modelValue', value);

  // For local options, try to build a partial address object
  if (props.options) {
    const item = { [props.field]: value };
    emit('select', item);
  } else {
    emit('select', opt);
  }

  showDropdown.value = false;
  activeIndex.value = -1;
}

async function loadRemoteSuggestions(value) {
  hasTyped.value = true;
  if (value.trim().length < 1) {
    suggestions.value = [];
    return;
  }
  const res = await fetchSuggestions({ field: props.field, value, context: props.context });
  suggestions.value = res;
  activeIndex.value = -1;
}

function onInput(e) {
  const value = e.target.value;
  emit('update:modelValue', value);
  showDropdown.value = true;
  hasTyped.value = true;

  if (props.options) {
    // Local filtering — no debounce needed
    activeIndex.value = -1;
    return;
  }

  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => loadRemoteSuggestions(value), 300);
}

function onFocus() {
  showDropdown.value = true;
  if (props.options) {
    // Show all options on focus
    activeIndex.value = -1;
    return;
  }
  if (props.modelValue.trim().length >= 1) {
    loadRemoteSuggestions(props.modelValue);
  }
}

function onBlur() {
  setTimeout(() => {
    showDropdown.value = false;
    activeIndex.value = -1;
  }, 200);
}

function onKeydown(e) {
  const opts = filteredOptions.value;
  if (!showDropdown.value || !opts.length) return;

  if (e.key === 'ArrowDown') {
    e.preventDefault();
    activeIndex.value = (activeIndex.value + 1) % opts.length;
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    activeIndex.value = (activeIndex.value - 1 + opts.length) % opts.length;
  } else if (e.key === 'Enter') {
    e.preventDefault();
    if (activeIndex.value >= 0) {
      selectOption(opts[activeIndex.value]);
    }
  } else if (e.key === 'Escape') {
    showDropdown.value = false;
    activeIndex.value = -1;
  }
}

watch(() => props.modelValue, (newVal) => {
  if (!newVal) {
    suggestions.value = [];
    hasTyped.value = false;
  }
});
</script>

<style scoped>
.autocomplete {
  position: relative;
}

.autocomplete__dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 50;
  max-height: 260px;
  overflow-y: auto;
  background: #fff;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  margin-top: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.autocomplete__item {
  padding: 10px 12px;
  font-size: 14px;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
  transition: background 0.1s;
}

.autocomplete__item:last-child {
  border-bottom: none;
}

.autocomplete__item:hover,
.autocomplete__item--active {
  background: var(--color-primary-light);
  color: var(--color-primary);
}

.autocomplete__dropdown--empty {
  padding: 12px;
  font-size: 13px;
  color: var(--color-text-secondary);
  text-align: center;
}

.autocomplete__loading {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
</style>
