import { ref, reactive, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { searchProducts } from '@/api/search';

/**
 * useCatalogSearch — состояние и загрузка листинга каталога через
 * `GET /api/v1/search/` (Meilisearch, за feature flag `catalog_search_meilisearch`).
 *
 * D-01 (spec): доступность поиска определяется пробным запросом (probe).
 * 404 → флаг выключен → `searchAvailable = false`, страница остаётся на
 * legacy `/products/`. Результат кэшируется в module-scope (не localStorage —
 * флаг может переключиться между сессиями); откат флага на backend даёт
 * автоматический fallback без релиза фронта. Ошибки, отличные от 404
 * (503/сеть), не кэшируются — следующий probe попробует снова.
 *
 * D-03: состояние фильтров синхронизируется с URL query (`router.replace`,
 * shareable ссылки + back-кнопка). OR внутри группы — повторяющиеся
 * `attr.<code>`; AND между группами — забота backend (D-08 эпика).
 *
 * Защита от гонок: AbortController + fetchId (паттерн Products.vue).
 * Дебаунс 300 мс только на текстовый ввод; клики по чекбоксам — мгновенно.
 */

const HITS_PER_PAGE = 20;
const DEBOUNCE_MS = 300;

let probePromise = null;

function probeSearchApi() {
  if (!probePromise) {
    probePromise = searchProducts({ page: 1, hits_per_page: 1 })
      .then(() => true)
      .catch((err) => {
        if (err?.response?.status !== 404) {
          // Не кэшируем временные ошибки (503 Meilisearch, сеть) —
          // следующий probe попробует ещё раз.
          probePromise = null;
        }
        return false;
      });
  }
  return probePromise;
}

/** Только для unit-тестов: сброс module-scope кэша probe между кейсами. */
export function __resetSearchProbeForTests() {
  probePromise = null;
}

function parseRangeParam(raw) {
  if (typeof raw !== 'string') return null;
  const [minRaw, maxRaw] = raw.split(':');
  const min = minRaw === '' || minRaw === undefined ? null : Number(minRaw);
  const max = maxRaw === '' || maxRaw === undefined ? null : Number(maxRaw);
  if ((min !== null && Number.isNaN(min)) || (max !== null && Number.isNaN(max))) return null;
  if (min === null && max === null) return null;
  return { min, max };
}

export function useCatalogSearch() {
  const route = useRoute();
  const router = useRouter();

  const items = ref([]);
  const total = ref(null);
  const page = ref(1);
  const pages = ref(0);
  const facets = ref([]);
  const loading = ref(false);
  const error = ref(null);
  const searchAvailable = ref(false);

  /** reactive Map<facetCode, Set<value>> — выбранные значения фасетов (OR внутри группы). */
  const selected = reactive(new Map());
  /** reactive Map<facetCode, {min: number|null, max: number|null}> — числовые диапазоны. */
  const ranges = reactive(new Map());
  const priceRange = reactive({ min: null, max: null });
  const sort = ref('');
  const categoryId = ref(null);
  const q = ref('');

  const hasMore = computed(() => page.value < pages.value);

  let abortController = null;
  let fetchId = 0;
  let debounceTimer = null;

  const buildParams = (targetPage) => {
    const params = { page: targetPage, hits_per_page: HITS_PER_PAGE };
    const query = q.value.trim();
    if (query) params.q = query;
    if (categoryId.value) params.category_id = categoryId.value;
    if (sort.value) params.sort = sort.value;
    if (priceRange.min !== null && priceRange.min !== '') params.price_min = priceRange.min;
    if (priceRange.max !== null && priceRange.max !== '') params.price_max = priceRange.max;
    for (const [code, values] of selected) {
      if (values.size > 0) params[`attr.${code}`] = [...values];
    }
    for (const [code, range] of ranges) {
      if (range.min !== null || range.max !== null) {
        params[`attrs_range.${code}`] = `${range.min ?? ''}:${range.max ?? ''}`;
      }
    }
    return params;
  };

  const syncUrl = () => {
    const query = {};
    // `q` управляется Products.vue (router.push на submit) — сохраняем как есть.
    if (route.query.q) query.q = route.query.q;
    if (sort.value) query.sort = sort.value;
    if (categoryId.value) query.category_id = String(categoryId.value);
    if (priceRange.min !== null && priceRange.min !== '') query.price_min = String(priceRange.min);
    if (priceRange.max !== null && priceRange.max !== '') query.price_max = String(priceRange.max);
    for (const [code, values] of selected) {
      if (values.size > 0) query[`attr.${code}`] = [...values].map(String);
    }
    for (const [code, range] of ranges) {
      if (range.min !== null || range.max !== null) {
        query[`attrs_range.${code}`] = `${range.min ?? ''}:${range.max ?? ''}`;
      }
    }
    router.replace({ query }).catch(() => {});
  };

  const initFromUrl = () => {
    for (const [key, raw] of Object.entries(route.query)) {
      if (key.startsWith('attr.')) {
        const code = key.slice('attr.'.length);
        const values = Array.isArray(raw) ? raw : [raw];
        selected.set(code, new Set(values.filter((v) => v !== null && v !== undefined)));
      } else if (key.startsWith('attrs_range.')) {
        const range = parseRangeParam(Array.isArray(raw) ? raw[0] : raw);
        if (range) ranges.set(key.slice('attrs_range.'.length), range);
      }
    }
    const priceMin = Number(route.query.price_min);
    const priceMax = Number(route.query.price_max);
    if (!Number.isNaN(priceMin) && route.query.price_min !== undefined) priceRange.min = priceMin;
    if (!Number.isNaN(priceMax) && route.query.price_max !== undefined) priceRange.max = priceMax;
    if (route.query.sort) sort.value = String(route.query.sort);
    const catId = Number(route.query.category_id);
    if (!Number.isNaN(catId) && route.query.category_id !== undefined) categoryId.value = catId;
  };

  const load = async (append = false) => {
    if (abortController) {
      abortController.abort();
    }
    abortController = new AbortController();
    const currentFetchId = ++fetchId;

    loading.value = true;
    error.value = null;
    try {
      const data = await searchProducts(buildParams(page.value), abortController.signal);
      // Игнорируем устаревшие ответы (пришли после более нового запроса).
      if (currentFetchId !== fetchId) return;
      if (append) {
        items.value.push(...data.items);
      } else {
        items.value = data.items;
      }
      total.value = data.total;
      pages.value = data.pages;
      facets.value = data.facets || [];
    } catch (err) {
      if (err?.code !== 'ERR_CANCELED' && err?.name !== 'AbortError') {
        error.value = err;
      }
    } finally {
      if (currentFetchId === fetchId) {
        loading.value = false;
      }
    }
  };

  const applyAndLoad = () => {
    page.value = 1;
    syncUrl();
    load();
  };

  const toggleFacetValue = (code, value) => {
    if (!selected.has(code)) selected.set(code, new Set());
    const values = selected.get(code);
    if (values.has(value)) {
      values.delete(value);
    } else {
      values.add(value);
    }
    if (values.size === 0) selected.delete(code);
    applyAndLoad();
  };

  const setRange = (code, min, max) => {
    if (min === null && max === null) {
      ranges.delete(code);
    } else {
      ranges.set(code, { min, max });
    }
    applyAndLoad();
  };

  const setPrice = (min, max) => {
    priceRange.min = min;
    priceRange.max = max;
    applyAndLoad();
  };

  const setSort = (value) => {
    sort.value = value || '';
    applyAndLoad();
  };

  const setCategory = (id) => {
    categoryId.value = id || null;
    applyAndLoad();
  };

  const setQuery = (text) => {
    q.value = text || '';
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      applyAndLoad();
    }, DEBOUNCE_MS);
  };

  const loadMore = () => {
    if (!hasMore.value || loading.value) return;
    page.value += 1;
    load(true);
  };

  const reset = () => {
    selected.clear();
    ranges.clear();
    priceRange.min = null;
    priceRange.max = null;
    sort.value = '';
    categoryId.value = null;
    applyAndLoad();
  };

  const probe = async () => {
    searchAvailable.value = await probeSearchApi();
    return searchAvailable.value;
  };

  return {
    items,
    total,
    page,
    pages,
    facets,
    loading,
    error,
    searchAvailable,
    selected,
    ranges,
    priceRange,
    sort,
    categoryId,
    q,
    hasMore,
    toggleFacetValue,
    setRange,
    setPrice,
    setSort,
    setCategory,
    setQuery,
    loadMore,
    load,
    reset,
    probe,
    initFromUrl,
  };
}
