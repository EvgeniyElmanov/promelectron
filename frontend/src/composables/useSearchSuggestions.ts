import { ref, watch } from 'vue';
import api from '@/services/api';

const CACHE_TTL_MS = 60 * 60 * 1000; // 1 hour
const memoryCache = new Map<string, { data: unknown; timestamp: number }>();

function getCacheKey(type: string, query?: string): string {
  return query ? `search_${type}_${query.toLowerCase()}` : `search_${type}`;
}

function getCached<T>(key: string): T | null {
  const mem = memoryCache.get(key);
  if (mem && Date.now() - mem.timestamp < CACHE_TTL_MS) {
    return mem.data as T;
  }
  try {
    const raw = localStorage.getItem(key);
    if (raw) {
      const parsed = JSON.parse(raw) as { data: T; timestamp: number };
      if (parsed && Date.now() - parsed.timestamp < CACHE_TTL_MS) {
        memoryCache.set(key, parsed);
        return parsed.data;
      }
    }
  } catch {
    // ignore localStorage errors
  }
  return null;
}

function setCached(key: string, data: unknown): void {
  const entry = { data, timestamp: Date.now() };
  memoryCache.set(key, entry);
  try {
    localStorage.setItem(key, JSON.stringify(entry));
  } catch {
    // ignore localStorage errors (e.g. quota exceeded)
  }
}

export interface PopularCategory {
  id: number;
  name: string;
  image?: string;
}

export interface MiniProduct {
  id: number;
  name: string;
  price?: number;
  image?: string;
}

export interface Recommendations {
  trending: string[];
  popular_categories: PopularCategory[];
  recommendations: MiniProduct[];
}

export interface Suggestions {
  queries: string[];
  categories: PopularCategory[];
  brands: string[];
  products: MiniProduct[];
}

const HISTORY_KEY = 'search_history';
const MAX_HISTORY = 8;

/**
 * Probe-флаг (issue #171): feature flag `catalog_search_meilisearch` выключен →
 * `/search/suggestions/` отвечает 404 (by design, D-09). После первого 404
 * помечаем search API недоступным в sessionStorage и дальше сразу идём
 * в fallback на `/products/`, не спамя 404 в консоль.
 */
const SEARCH_API_DOWN_KEY = 'search_api_unavailable';

function isSearchApiDown(): boolean {
  try {
    return sessionStorage.getItem(SEARCH_API_DOWN_KEY) === '1';
  } catch {
    return false;
  }
}

function markSearchApiDown(): void {
  try {
    sessionStorage.setItem(SEARCH_API_DOWN_KEY, '1');
  } catch {
    // ignore sessionStorage errors
  }
}

export function getSearchHistory(): string[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function addSearchHistory(query: string): void {
  const q = query.trim();
  if (!q) return;
  const history = getSearchHistory();
  const updated = [q, ...history.filter((h) => h.toLowerCase() !== q.toLowerCase())].slice(0, MAX_HISTORY);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(updated));
}

export function removeSearchHistory(query: string): void {
  const history = getSearchHistory().filter((h) => h !== query);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
}

export function clearSearchHistory(): void {
  localStorage.removeItem(HISTORY_KEY);
}

function mapProductItem(item: any): MiniProduct {
  return {
    id: item.id,
    name: item.name,
    price: item.price,
    image: item.images?.[0] || item.image || undefined,
  };
}

/**
 * D-06 (issue #122): backend Фазы 5 отдаёт `/search/suggestions/` в форме
 * `{suggestions: [{type: "product", id, name}]}` (без price/image, без
 * queries/categories/brands) и возвращает 200 — fallback по catch не сработает.
 * Принимаем обе формы: новую маппим в `Suggestions` (price/image опциональны,
 * SearchBar рендерит их под v-if), старую (`{queries, categories, brands,
 * products}`) — как есть. Обогащение suggestions — backend follow-up.
 */
function normalizeSuggestions(data: any): Suggestions {
  if (data && Array.isArray(data.suggestions)) {
    return {
      queries: [],
      categories: [],
      brands: [],
      products: data.suggestions
        .filter((s: any) => s && s.type === 'product')
        .map((s: any) => ({ id: s.id, name: s.name })),
    };
  }
  return data as Suggestions;
}

export function useSearchSuggestions() {
  const query = ref('');
  const isLoading = ref(false);
  const recommendations = ref<Recommendations | null>(null);
  const suggestions = ref<Suggestions | null>(null);
  const error = ref<string | null>(null);

  async function fetchRecommendations() {
    const key = getCacheKey('recommendations');
    const cached = getCached<Recommendations>(key);
    if (cached) {
      recommendations.value = cached;
      return;
    }
    try {
      isLoading.value = true;
      error.value = null;
      // Backend `/search/recommendations/` не существует (issue #171) —
      // сразу используем `/products/`, сохраняя формат Recommendations.
      const { data } = await api.get<{ items: any[]; total: number }>('/products/', {
        params: { limit: 6 },
      });
      recommendations.value = {
        trending: [],
        popular_categories: [],
        recommendations: data.items.map(mapProductItem),
      };
      setCached(key, recommendations.value);
    } catch (err: any) {
      if (!recommendations.value) {
        recommendations.value = {
          trending: [],
          popular_categories: [],
          recommendations: [],
        };
      }
      error.value = err?.message || 'Failed to load recommendations';
    } finally {
      isLoading.value = false;
    }
  }

  async function fetchSuggestionsFallback(q: string, key: string, originalErr?: any) {
    // Fallback to existing /products/ API when search endpoints are not ready
    try {
      const { data } = await api.get<{ items: any[]; total: number }>('/products/', {
        params: { q, limit: 5 },
      });
      suggestions.value = {
        queries: [],
        categories: [],
        brands: [],
        products: data.items.map(mapProductItem),
      };
      setCached(key, suggestions.value);
    } catch {
      suggestions.value = null;
      error.value = originalErr?.message || 'Failed to load suggestions';
    }
  }

  async function fetchSuggestions(q: string) {
    if (!q || q.trim().length < 2) {
      suggestions.value = null;
      return;
    }
    const key = getCacheKey('suggestions', q.trim());
    const cached = getCached<Suggestions>(key);
    if (cached) {
      suggestions.value = cached;
      return;
    }
    try {
      isLoading.value = true;
      error.value = null;
      if (isSearchApiDown()) {
        // search API помечен недоступным (probe 404) — сразу fallback без запроса
        await fetchSuggestionsFallback(q.trim(), key);
        return;
      }
      try {
        const { data } = await api.get<Suggestions>('/search/suggestions/', {
          params: { q: q.trim() },
        });
        suggestions.value = normalizeSuggestions(data);
        setCached(key, suggestions.value);
      } catch (err: any) {
        if (err?.response?.status === 404) {
          markSearchApiDown();
        }
        await fetchSuggestionsFallback(q.trim(), key, err);
      }
    } finally {
      isLoading.value = false;
    }
  }

  // Debounced watcher
  let debounceTimer: ReturnType<typeof setTimeout> | null = null;
  watch(query, (newVal) => {
    if (debounceTimer) clearTimeout(debounceTimer);
    if (!newVal || newVal.trim().length < 2) {
      suggestions.value = null;
      return;
    }
    debounceTimer = setTimeout(() => {
      fetchSuggestions(newVal);
    }, 300);
  });

  return {
    query,
    isLoading,
    recommendations,
    suggestions,
    error,
    fetchRecommendations,
    fetchSuggestions,
  };
}
