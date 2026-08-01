<template>
  <aside class="filter-panel" data-testid="filter-panel">
    <!-- Категории: дерево из фасетов categories.lvl0 / categories.lvl1 -->
    <details v-if="categoryTree.length" class="filter-panel__section" open data-testid="filter-group-categories">
      <summary class="filter-panel__section-title">Категории</summary>
      <ul class="filter-panel__category-tree">
        <li v-for="root in categoryTree" :key="root.name">
          <button
            type="button"
            class="filter-panel__category-btn"
            :class="{ 'filter-panel__category-btn--active': isCategoryActive(root.name) }"
            :data-testid="`filter-category-${root.id ?? root.name}`"
            @click="onCategoryClick(root.name)"
          >
            {{ root.name }} <span class="filter-panel__count">({{ root.count }})</span>
          </button>
          <ul v-if="root.children.length" class="filter-panel__category-children">
            <li v-for="child in root.children" :key="child.name">
              <button
                type="button"
                class="filter-panel__category-btn filter-panel__category-btn--child"
                :class="{ 'filter-panel__category-btn--active': isCategoryActive(child.name) }"
                :data-testid="`filter-category-${child.id ?? child.name}`"
                @click="onCategoryClick(child.name)"
              >
                {{ child.name }} <span class="filter-panel__count">({{ child.count }})</span>
              </button>
            </li>
          </ul>
        </li>
      </ul>
    </details>

    <!-- Цена -->
    <details v-if="priceStats" class="filter-panel__section" open data-testid="filter-group-price">
      <summary class="filter-panel__section-title">Цена</summary>
      <div class="filter-panel__range">
        <input
          v-model.number="priceMinInput"
          type="number"
          class="filter-panel__range-input"
          :placeholder="String(priceStats.min)"
          :min="priceStats.min"
          :max="priceStats.max"
          data-testid="filter-price-min"
        />
        <span class="filter-panel__range-sep">—</span>
        <input
          v-model.number="priceMaxInput"
          type="number"
          class="filter-panel__range-input"
          :placeholder="String(priceStats.max)"
          :min="priceStats.min"
          :max="priceStats.max"
          data-testid="filter-price-max"
        />
        <button
          type="button"
          class="filter-panel__apply-btn"
          data-testid="filter-apply"
          @click="applyPrice"
        >
          OK
        </button>
      </div>
    </details>

    <!-- Остальные фасеты в порядке backend -->
    <details
      v-for="facet in attributeFacets"
      :key="facet.code"
      class="filter-panel__section"
      open
      :data-testid="`filter-group-${facet.code}`"
    >
      <summary class="filter-panel__section-title">{{ facet.name }}</summary>

      <!-- Enum-фасет: чекбоксы с disjunctive-счётчиками (считает backend, D-08 эпика) -->
      <ul v-if="facet.values" class="filter-panel__values">
        <li v-for="(item, i) in facet.values" :key="String(item.value)">
          <label class="filter-panel__value">
            <input
              type="checkbox"
              :checked="isSelected(facet.code, item.value)"
              :data-testid="`filter-value-${facet.code}-${i}`"
              @change="$emit('toggle', facet.code, item.value)"
            />
            <span class="filter-panel__value-label">{{ item.value }}</span>
            <span class="filter-panel__count">({{ item.count }})</span>
          </label>
        </li>
      </ul>

      <!-- Числовой фасет: диапазон по stats {min,max} -->
      <div v-else-if="facet.stats" class="filter-panel__range">
        <input
          v-model.number="rangeInputs[facet.code].min"
          type="number"
          class="filter-panel__range-input"
          :placeholder="String(facet.stats.min)"
          :min="facet.stats.min"
          :max="facet.stats.max"
          :data-testid="`filter-range-min-${facet.code}`"
        />
        <span class="filter-panel__range-sep">—</span>
        <input
          v-model.number="rangeInputs[facet.code].max"
          type="number"
          class="filter-panel__range-input"
          :placeholder="String(facet.stats.max)"
          :min="facet.stats.min"
          :max="facet.stats.max"
          :data-testid="`filter-range-max-${facet.code}`"
        />
        <button
          type="button"
          class="filter-panel__apply-btn"
          :data-testid="`filter-range-apply-${facet.code}`"
          @click="applyRange(facet)"
        >
          OK
        </button>
        <span v-if="facet.unit" class="filter-panel__unit">{{ facet.unit }}</span>
      </div>
    </details>

    <button
      type="button"
      class="filter-panel__reset"
      data-testid="filter-reset"
      @click="$emit('reset')"
    >
      Сбросить фильтры
    </button>
  </aside>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue';

/**
 * FilterPanel — dumb-компонент фасетных фильтров каталога (issue #122, D-04).
 *
 * Props:
 *   - facets: FacetOut[] из ответа GET /api/v1/search/
 *     ({code, name, value_type, unit, values: [{value, count}] | stats: {min, max}})
 *   - selected: Map<facetCode, Set<value>> — выбранные значения
 *   - priceRange: {min, max} — текущий фильтр цены
 *   - categoryId: number|null — выбранная категория
 *   - categoryOptions: справочник категорий из useCategories.allCategories
 *     (имя → id; фасеты отдают только имена/пути, маппинг id-first — D-спека)
 *
 * Emits: toggle(code, value), price({min, max}), range(code, {min, max}),
 *        category(id|null), reset.
 *
 * Счётчики уже disjunctive (их считает backend) — компонент только отображает.
 */
const props = defineProps({
  facets: {
    type: Array,
    default: () => [],
  },
  selected: {
    type: Map,
    default: () => new Map(),
  },
  priceRange: {
    type: Object,
    default: () => ({ min: null, max: null }),
  },
  categoryId: {
    type: [Number, String],
    default: null,
  },
  categoryOptions: {
    type: Array,
    default: () => [],
  },
});

const emit = defineEmits(['toggle', 'price', 'range', 'category', 'reset']);

const lvl0Facet = computed(() => props.facets.find((f) => f.code === 'categories.lvl0'));
const lvl1Facet = computed(() => props.facets.find((f) => f.code === 'categories.lvl1'));
const priceFacet = computed(() => props.facets.find((f) => f.code === 'price'));
const priceStats = computed(() => priceFacet.value?.stats || null);

const attributeFacets = computed(() =>
  props.facets.filter(
    (f) => f.code !== 'categories.lvl0' && f.code !== 'categories.lvl1' && f.code !== 'price',
  ),
);

// Дерево категорий: lvl1-значения — пути «Root > Child», сплит по ' > ' (D-04).
const categoryTree = computed(() => {
  const roots = (lvl0Facet.value?.values || []).map((v) => ({
    name: String(v.value),
    count: v.count,
    id: findCategoryId(String(v.value)),
    children: [],
  }));
  const byRoot = new Map(roots.map((r) => [r.name, r]));
  for (const v of lvl1Facet.value?.values || []) {
    const parts = String(v.value).split(' > ');
    if (parts.length < 2) continue;
    const childName = parts[parts.length - 1];
    const root = byRoot.get(parts[0]);
    if (root) {
      root.children.push({ name: childName, count: v.count, id: findCategoryId(childName) });
    }
  }
  return roots;
});

// Имя категории → id по справочнику из useCategories (id-first; фасеты — для counts).
function findCategoryId(name) {
  const match = props.categoryOptions.find((c) => c.name === name);
  return match ? match.id : null;
}

function isCategoryActive(name) {
  const id = findCategoryId(name);
  return id !== null && props.categoryId !== null && Number(props.categoryId) === Number(id);
}

function onCategoryClick(name) {
  const id = findCategoryId(name);
  // Повторный клик по активной категории снимает фильтр.
  emit('category', isCategoryActive(name) ? null : id);
}

function isSelected(code, value) {
  // F002: selected хранит строки (URL query — строки); значения фасетов
  // backend могут быть числами — сравниваем через String().
  return props.selected.get(code)?.has(String(value)) ?? false;
}

// --- Цена ---
const priceMinInput = ref(props.priceRange.min);
const priceMaxInput = ref(props.priceRange.max);
watch(
  () => [props.priceRange.min, props.priceRange.max],
  ([min, max]) => {
    priceMinInput.value = min;
    priceMaxInput.value = max;
  },
);

function clamp(value, stats) {
  if (value === null || value === undefined || value === '') return null;
  const num = Number(value);
  if (Number.isNaN(num)) return null;
  return Math.min(Math.max(num, stats.min), stats.max);
}

function applyPrice() {
  if (!priceStats.value) return;
  emit('price', {
    min: clamp(priceMinInput.value, priceStats.value),
    max: clamp(priceMaxInput.value, priceStats.value),
  });
}

// --- Числовые диапазоны атрибутов ---
const rangeInputs = reactive({});
watch(
  attributeFacets,
  (facets) => {
    for (const facet of facets) {
      if (facet.stats && !rangeInputs[facet.code]) {
        rangeInputs[facet.code] = { min: null, max: null };
      }
    }
  },
  { immediate: true },
);

function applyRange(facet) {
  const input = rangeInputs[facet.code];
  emit('range', facet.code, {
    min: clamp(input.min, facet.stats),
    max: clamp(input.max, facet.stats),
  });
}
</script>

<style scoped>
.filter-panel {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
  background: var(--color-bg-white);
  border-radius: 12px;
}

.filter-panel__section {
  border-bottom: 1px solid var(--color-border);
  padding: 8px 0;
}

.filter-panel__section:last-of-type {
  border-bottom: none;
}

.filter-panel__section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  cursor: pointer;
  user-select: none;
  list-style: none;
}

.filter-panel__section-title::before {
  content: '▾ ';
  color: var(--color-text-secondary);
}

.filter-panel__section:not([open]) > .filter-panel__section-title::before {
  content: '▸ ';
}

.filter-panel__category-tree,
.filter-panel__category-children,
.filter-panel__values {
  list-style: none;
  margin: 8px 0 0;
  padding: 0;
}

.filter-panel__category-children {
  margin-left: 16px;
}

.filter-panel__category-btn {
  display: block;
  width: 100%;
  text-align: left;
  background: none;
  border: none;
  padding: 6px 4px;
  font-size: 14px;
  color: var(--color-text);
  border-radius: 6px;
}

.filter-panel__category-btn:hover {
  background: var(--color-bg);
}

.filter-panel__category-btn--active {
  color: var(--color-primary);
  font-weight: 600;
}

.filter-panel__value {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 4px;
  font-size: 14px;
  color: var(--color-text);
  cursor: pointer;
}

.filter-panel__count {
  color: var(--color-text-secondary);
  font-size: 13px;
}

.filter-panel__range {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.filter-panel__range-input {
  flex: 1;
  min-width: 0;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-white);
  font-size: 14px;
  color: var(--color-text);
}

.filter-panel__range-sep {
  color: var(--color-text-secondary);
}

.filter-panel__apply-btn {
  padding: 8px 14px;
  border-radius: 8px;
  background: var(--color-primary);
  color: var(--color-white);
  font-size: 14px;
  font-weight: 500;
  border: none;
  flex-shrink: 0;
}

.filter-panel__unit {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.filter-panel__reset {
  margin-top: 8px;
  padding: 10px;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-white);
  color: var(--color-primary);
  font-size: 14px;
  font-weight: 500;
}
</style>
