/**
 * Composable для подсказок адреса через Nominatim (OpenStreetMap).
 * Debounce + кэширование + rate-limit-friendly.
 */

import { ref } from 'vue';

const CACHE = new Map();
let lastRequestTime = 0;
const MIN_DELAY_MS = 1100; // Nominatim policy: 1 req/sec

async function _doFetch(url) {
  const now = Date.now();
  const wait = lastRequestTime + MIN_DELAY_MS - now;
  if (wait > 0) {
    await new Promise((r) => setTimeout(r, wait));
  }
  lastRequestTime = Date.now();

  const res = await fetch(url, {
    headers: { 'User-Agent': 'Promelectron/1.0 (contact@example.com)' },
  });
  if (!res.ok) return [];
  return res.json();
}

function _buildNominatimUrl(query) {
  const params = new URLSearchParams({
    format: 'json',
    q: query,
    lang: 'ru',
    limit: '5',
    countrycodes: 'ru',
    addressdetails: '1',
  });
  return `https://nominatim.openstreetmap.org/search?${params.toString()}`;
}

function _extractAddress(item) {
  const a = item.address || {};
  return {
    region: a.state || '',
    district: a.county || a.city_district || '',
    city: a.city || a.town || a.village || a.hamlet || '',
    street: a.road || a.pedestrian || a.living_street || a.highway || '',
    house: a.house_number || '',
    apartment: '',
    _display: item.display_name || item.name || '',
    _type: item.addresstype || '',
  };
}

function _filterByType(results, types) {
  return results.filter((r) => types.includes(r.addresstype) || types.includes(r.type));
}

export function useAddressSuggestions() {
  const isLoading = ref(false);

  async function fetchSuggestions({ field, value, context = {} }) {
    const trimmed = value.trim();
    if (trimmed.length < 2) return [];

    let query = trimmed;
    const { region = '', city = '' } = context;

    // Build contextual query
    if (field === 'district' && region) {
      query = `${trimmed}, ${region}`;
    } else if (field === 'city' && region) {
      query = `${trimmed}, ${region}`;
    } else if (field === 'street') {
      const parts = [trimmed];
      if (city) parts.push(city);
      else if (region) parts.push(region);
      query = parts.join(', ');
    }

    const cacheKey = `${field}:${query}`;
    if (CACHE.has(cacheKey)) {
      return CACHE.get(cacheKey);
    }

    isLoading.value = true;
    try {
      const url = _buildNominatimUrl(query);
      const results = await _doFetch(url);
      if (!Array.isArray(results)) return [];

      let filtered = results;

      if (field === 'region') {
        filtered = _filterByType(results, ['state']);
      } else if (field === 'district') {
        filtered = _filterByType(results, ['county', 'district', 'city_district']);
      } else if (field === 'city') {
        filtered = _filterByType(results, ['city', 'town', 'village']);
      } else if (field === 'street') {
        filtered = results.filter(
          (r) => r.addresstype === 'road' || r.class === 'highway' || r.addresstype === 'street'
        );
      }

      const mapped = filtered.map(_extractAddress);
      // Deduplicate by display name
      const seen = new Set();
      const unique = mapped.filter((m) => {
        if (seen.has(m._display)) return false;
        seen.add(m._display);
        return true;
      });

      CACHE.set(cacheKey, unique);
      return unique;
    } catch {
      return [];
    } finally {
      isLoading.value = false;
    }
  }

  return {
    isLoading,
    fetchSuggestions,
  };
}
