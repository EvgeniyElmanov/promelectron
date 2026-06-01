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
  price: number;
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
      const { data } = await api.get<Recommendations>('/search/recommendations/');
      recommendations.value = data;
      setCached(key, data);
    } catch (err: any) {
      // Keep previous data on error; UI handles empty state gracefully
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
      const { data } = await api.get<Suggestions>('/search/suggestions/', {
        params: { q: q.trim() },
      });
      suggestions.value = data;
      setCached(key, data);
    } catch (err: any) {
      // Keep suggestions null on error so UI can show fallback instead of "not found"
      suggestions.value = null;
      error.value = err?.message || 'Failed to load suggestions';
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
