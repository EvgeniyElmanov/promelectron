<template>
  <div ref="searchBarRef" class="search-bar">
    <div class="search-bar__input-wrapper">
      <svg
        class="search-bar__icon"
        viewBox="0 0 24 24"
        width="18"
        height="18"
        fill="none"
      >
        <circle cx="11" cy="11" r="6" stroke="#999" stroke-width="2" />
        <path
          d="M20 20l-3.5-3.5"
          stroke="#999"
          stroke-width="2"
          stroke-linecap="round"
        />
      </svg>
      <input
        ref="inputRef"
        type="text"
        class="search-bar__input"
        :data-testid="dataTestid"
        placeholder="Поиск товаров..."
        :value="modelValue"
        @input="onInput"
        @focus="onFocus"
        @keydown.enter.prevent="onEnter"
        @keydown.esc.prevent="closeDropdown"
      />
      <button
        v-if="modelValue"
        type="button"
        class="search-bar__clear-btn"
        data-testid="search-bar-clear"
        @click="clearQuery"
      >
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none">
          <circle cx="12" cy="12" r="10" stroke="#999" stroke-width="1.5" />
          <path
            d="M9 9l6 6M15 9l-6 6"
            stroke="#999"
            stroke-width="1.5"
            stroke-linecap="round"
          />
        </svg>
      </button>
    </div>

    <!-- Dropdown -->
    <div
      v-if="isOpen"
      class="search-bar__dropdown"
      :class="{ 'search-bar__dropdown--mobile': isMobileOpen }"
      data-testid="search-bar-dropdown"
    >
      <!-- Mobile header -->
      <div
        v-if="isMobileOpen"
        class="search-bar__mobile-header"
        data-testid="search-bar-mobile-header"
      >
        <span class="search-bar__mobile-title">Поиск</span>
        <button
          class="search-bar__mobile-close"
          data-testid="search-bar-mobile-close"
          @click="closeDropdown"
        >
          Готово
        </button>
      </div>

      <!-- Scrollable content -->
      <div class="search-bar__scroll">
        <!-- Recommendations view (empty query) -->
        <template v-if="!modelValue.trim()">
          <!-- Trending / Often searched -->
          <div v-if="trending.length" class="search-bar__section">
            <div class="search-bar__section-title">Часто ищут</div>
            <div class="search-bar__tags">
              <button
                v-for="item in trending"
                :key="item"
                class="search-bar__tag"
                @click="selectQuery(item)"
              >
                {{ item }}
              </button>
            </div>
          </div>

          <!-- Popular categories -->
          <div v-if="popularCategories.length" class="search-bar__section">
            <div class="search-bar__section-title">Популярные категории</div>
            <div class="search-bar__categories">
              <button
                v-for="cat in popularCategories"
                :key="cat.id"
                class="search-bar__category-btn"
                @click="selectQuery(cat.name)"
              >
                <img
                  v-if="cat.image"
                  :src="cat.image"
                  class="search-bar__category-img"
                  alt=""
                />
                <span>{{ cat.name }}</span>
              </button>
            </div>
          </div>

          <!-- Product recommendations -->
          <div v-if="recommendedProducts.length" class="search-bar__section">
            <div class="search-bar__section-title">Вам может понравиться</div>
            <div class="search-bar__product-list">
              <div
                v-for="product in recommendedProducts"
                :key="product.id"
                class="search-bar__product-mini"
                data-testid="search-bar-recommended-product"
                @click="selectProduct(product)"
              >
                <img
                  v-if="product.image"
                  :src="product.image"
                  class="search-bar__product-img"
                  alt=""
                />
                <div class="search-bar__product-info">
                  <div class="search-bar__product-name">{{ product.name }}</div>
                  <div
                    v-if="product.price"
                    class="search-bar__product-price"
                  >
                    {{ formatPrice(product.price) }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div
            v-if="!trending.length && !popularCategories.length && !recommendedProducts.length"
            class="search-bar__empty"
          >
            Начните вводить название товара
          </div>
        </template>

        <!-- Suggestions view (with query) -->
        <template v-else>
          <!-- Text suggestions -->
          <div v-if="textSuggestions.length" class="search-bar__section">
            <div
              v-for="s in textSuggestions"
              :key="s"
              class="search-bar__suggestion-row"
              data-testid="search-bar-text-suggestion"
              @click="selectQuery(s)"
            >
              <svg
                class="search-bar__suggestion-icon"
                viewBox="0 0 24 24"
                width="16"
                height="16"
                fill="none"
              >
                <circle
                  cx="11"
                  cy="11"
                  r="6"
                  stroke="#999"
                  stroke-width="2"
                />
                <path
                  d="M20 20l-3.5-3.5"
                  stroke="#999"
                  stroke-width="2"
                  stroke-linecap="round"
                />
              </svg>
              <span
                class="search-bar__suggestion-text"
                v-html="highlightMatch(s)"
              />
            </div>
          </div>

          <!-- Categories -->
          <div v-if="suggestedCategories.length" class="search-bar__section">
            <div class="search-bar__section-title">Категории</div>
            <div
              v-for="cat in suggestedCategories"
              :key="cat.id"
              class="search-bar__suggestion-row"
              data-testid="search-bar-category-suggestion"
              @click="selectQuery(cat.name)"
            >
              <svg
                class="search-bar__suggestion-icon"
                viewBox="0 0 24 24"
                width="16"
                height="16"
                fill="none"
              >
                <path
                  d="M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z"
                  stroke="#999"
                  stroke-width="2"
                />
              </svg>
              <span
                class="search-bar__suggestion-text"
                v-html="highlightMatch(cat.name)"
              />
            </div>
          </div>

          <!-- Brands -->
          <div v-if="suggestedBrands.length" class="search-bar__section">
            <div class="search-bar__section-title">Бренды</div>
            <div class="search-bar__tags">
              <button
                v-for="brand in suggestedBrands"
                :key="brand"
                class="search-bar__tag"
                data-testid="search-bar-brand-suggestion"
                @click="selectQuery(brand)"
              >
                {{ brand }}
              </button>
            </div>
          </div>

          <!-- Products from API suggestions -->
          <div v-if="suggestedProducts.length" class="search-bar__section">
            <div class="search-bar__section-title">Товары</div>
            <div
              v-for="product in suggestedProducts"
              :key="product.id"
              class="search-bar__product-mini"
              data-testid="search-bar-product-suggestion"
              @click="selectProduct(product)"
            >
              <img
                v-if="product.image"
                :src="product.image"
                class="search-bar__product-img"
                alt=""
              />
              <div class="search-bar__product-info">
                <div
                  class="search-bar__product-name"
                  v-html="highlightMatch(product.name)"
                />
                <div
                  v-if="product.price"
                  class="search-bar__product-price"
                >
                  {{ formatPrice(product.price) }}
                </div>
              </div>
            </div>
          </div>

          <!-- Fallback products when suggestions API fails -->
          <div v-else-if="fallbackProducts.length" class="search-bar__section">
            <div class="search-bar__section-title">Товары</div>
            <div
              v-for="product in fallbackProducts"
              :key="product.id"
              class="search-bar__product-mini"
              data-testid="search-bar-product-suggestion"
              @click="selectProduct(product)"
            >
              <img
                v-if="product.image"
                :src="product.image"
                class="search-bar__product-img"
                alt=""
              />
              <div class="search-bar__product-info">
                <div
                  class="search-bar__product-name"
                  v-html="highlightMatch(product.name)"
                />
                <div
                  v-if="product.price"
                  class="search-bar__product-price"
                >
                  {{ formatPrice(product.price) }}
                </div>
              </div>
            </div>
          </div>

          <!-- No results -->
          <div v-if="showNoResults" class="search-bar__empty">
            Ничего не найдено
          </div>
        </template>
      </div>
    </div>

    <!-- Mobile backdrop -->
    <div
      v-if="isMobileOpen"
      class="search-bar__backdrop"
      @click="closeDropdown"
    />
  </div>
</template>

<script setup>
import {
  ref,
  computed,
  watch,
  onMounted,
  onUnmounted,
} from 'vue';
import { useSearchSuggestions } from '@/composables/useSearchSuggestions';

/**
 * SearchBar — строка поиска с двумя режимами:
 * 1. При фокусе на пустую строку: dropdown с рекомендациями
 *    (тренды, популярные категории, персональные рекомендации)
 * 2. При вводе текста (≥2 символа): autocomplete с подсказками
 *    (запросы, категории, бренды, товары с мини-картинкой и ценой)
 *
 * Props:
 *   - modelValue (string): текущее значение поиска
 *   - dataTestid (string): data-testid для input (default: 'search-bar')
 *
 * Emits:
 *   - update:modelValue (string): изменение значения поиска
 *   - submit (string): нажатие Enter или выбор подсказки
 *
 * Фичи:
 *   - Debounce 300ms на запросы suggestions
 *   - Клиентский кеш (in-memory + localStorage, TTL 1 час)
 *   - Закрытие dropdown при клике вне, Escape
 *   - Мобильная адаптивность (dropdown на весь экран)
 *   - Подсветка совпадений в подсказках
 */

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
  dataTestid: {
    type: String,
    default: 'search-bar',
  },
});

const emit = defineEmits(['update:modelValue', 'submit']);

const searchBarRef = ref(null);
const inputRef = ref(null);
const isOpen = ref(false);
const isMobileOpen = ref(false);

const {
  query: searchQuery,
  isLoading,
  recommendations,
  suggestions,
  fetchRecommendations,
} = useSearchSuggestions();

// Sync composable query with prop
watch(
  () => props.modelValue,
  (val) => {
    searchQuery.value = val;
  },
  { immediate: true }
);

// Computed data from recommendations
const trending = computed(() => recommendations.value?.trending || []);
const popularCategories = computed(
  () => recommendations.value?.popular_categories || []
);
const recommendedProducts = computed(
  () => recommendations.value?.recommendations || []
);

// Computed data from suggestions
const textSuggestions = computed(() => suggestions.value?.queries || []);
const suggestedCategories = computed(
  () => suggestions.value?.categories || []
);
const suggestedBrands = computed(() => suggestions.value?.brands || []);
const suggestedProducts = computed(
  () => suggestions.value?.products || []
);

// Fallback: filter recommendations locally when suggestions API fails
const fallbackProducts = computed(() => {
  const q = props.modelValue.trim().toLowerCase();
  if (!q || q.length < 2) return [];
  return recommendedProducts.value.filter((p) =>
    p.name.toLowerCase().includes(q)
  );
});

const showNoResults = computed(() => {
  const q = props.modelValue.trim();
  if (!q || q.length < 2) return false;
  if (isLoading.value) return false;
  // If suggestions API returned an error (null), show fallback or nothing
  if (suggestions.value === null) {
    return fallbackProducts.value.length === 0;
  }
  return (
    !textSuggestions.value.length &&
    !suggestedCategories.value.length &&
    !suggestedBrands.value.length &&
    !suggestedProducts.value.length
  );
});

function onInput(e) {
  const val = e.target.value;
  emit('update:modelValue', val);
  searchQuery.value = val;
}

function onFocus() {
  openDropdown();
  fetchRecommendations();
}

function onEnter() {
  const q = props.modelValue.trim();
  closeDropdown();
  if (q) {
    emit('submit', q);
  }
}

function selectQuery(q) {
  emit('update:modelValue', q);
  searchQuery.value = q;
  closeDropdown();
  emit('submit', q);
}

function selectProduct(product) {
  emit('update:modelValue', product.name);
  searchQuery.value = product.name;
  closeDropdown();
  emit('submit', product.name);
}

function clearQuery() {
  emit('update:modelValue', '');
  searchQuery.value = '';
  inputRef.value?.focus();
}

function openDropdown() {
  isOpen.value = true;
  isMobileOpen.value = window.innerWidth < 768;
}

function closeDropdown() {
  isOpen.value = false;
  isMobileOpen.value = false;
}

function formatPrice(price) {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0,
  }).format(price);
}

function escapeRegex(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function highlightMatch(text) {
  const q = props.modelValue.trim();
  if (!q) return text;
  const regex = new RegExp(`(${escapeRegex(q)})`, 'gi');
  return text.replace(
    regex,
    '<mark class="search-bar__highlight">$1</mark>'
  );
}

// Click-outside handler
function onDocumentClick(e) {
  if (searchBarRef.value && !searchBarRef.value.contains(e.target)) {
    closeDropdown();
  }
}

// Resize handler to sync mobile state
function onWindowResize() {
  if (isOpen.value) {
    isMobileOpen.value = window.innerWidth < 768;
  }
}

onMounted(() => {
  document.addEventListener('click', onDocumentClick);
  window.addEventListener('resize', onWindowResize);
});

onUnmounted(() => {
  document.removeEventListener('click', onDocumentClick);
  window.removeEventListener('resize', onWindowResize);
});
</script>

<style scoped>
.search-bar {
  position: relative;
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

.search-bar__clear-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  padding: 4px;
  margin-left: 4px;
  cursor: pointer;
}

/* Dropdown */
.search-bar__dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 12px;
  right: 12px;
  background: var(--color-bg-white);
  border-radius: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
  z-index: 150;
  max-height: 520px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.search-bar__scroll {
  overflow-y: auto;
  padding: 8px 0;
  flex: 1;
}

.search-bar__section {
  padding: 8px 16px;
}

.search-bar__section + .search-bar__section {
  border-top: 1px solid var(--color-border);
}

.search-bar__section-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

/* Tags */
.search-bar__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.search-bar__tag {
  padding: 6px 12px;
  border-radius: 16px;
  background: var(--color-bg);
  color: var(--color-text);
  font-size: 13px;
  border: 1px solid var(--color-border);
  transition: background 0.15s, border-color 0.15s;
}

.search-bar__tag:hover {
  background: var(--color-primary-light);
  border-color: var(--color-primary);
}

/* Categories */
.search-bar__categories {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.search-bar__category-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 10px;
  background: var(--color-bg);
  color: var(--color-text);
  font-size: 13px;
  border: 1px solid var(--color-border);
  transition: background 0.15s;
}

.search-bar__category-btn:hover {
  background: var(--color-primary-light);
}

.search-bar__category-img {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  object-fit: cover;
}

/* Product mini cards */
.search-bar__product-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.search-bar__product-mini {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.15s;
}

.search-bar__product-mini:hover {
  background: var(--color-bg);
}

.search-bar__product-img {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  object-fit: cover;
  flex-shrink: 0;
  background: var(--color-bg);
}

.search-bar__product-info {
  flex: 1;
  min-width: 0;
}

.search-bar__product-name {
  font-size: 14px;
  color: var(--color-text);
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.search-bar__product-price {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-primary);
  margin-top: 2px;
}

/* Suggestion rows */
.search-bar__suggestion-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  cursor: pointer;
  border-radius: 8px;
  transition: background 0.15s;
}

.search-bar__suggestion-row:hover {
  background: var(--color-bg);
}

.search-bar__suggestion-icon {
  flex-shrink: 0;
}

.search-bar__suggestion-text {
  font-size: 14px;
  color: var(--color-text);
}

.search-bar__highlight {
  background: none;
  color: var(--color-primary);
  font-weight: 600;
}

/* Empty state */
.search-bar__empty {
  padding: 32px 16px;
  text-align: center;
  color: var(--color-text-secondary);
  font-size: 14px;
}

/* Mobile full-screen dropdown */
.search-bar__backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 140;
}

@media (max-width: 767px) {
  .search-bar__dropdown--mobile {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    max-height: none;
    border-radius: 0;
    z-index: 200;
  }

  .search-bar__mobile-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    border-bottom: 1px solid var(--color-border);
    flex-shrink: 0;
    background: var(--color-bg-white);
  }

  .search-bar__mobile-title {
    font-size: 17px;
    font-weight: 600;
  }

  .search-bar__mobile-close {
    font-size: 15px;
    color: var(--color-primary);
    background: none;
    border: none;
    font-weight: 500;
    cursor: pointer;
  }
}

@media (min-width: 768px) {
  .search-bar__mobile-header {
    display: none;
  }
}
</style>
