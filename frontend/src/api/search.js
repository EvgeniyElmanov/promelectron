import api from '@/services/api';

/**
 * API client for the public catalog search endpoints (issue #122).
 *
 * All endpoints live under the `catalog_search_meilisearch` feature flag and
 * return 404 when the flag is off — callers must handle that as
 * "search unavailable" and fall back to the legacy `/products/` listing.
 *
 * Trailing slash is mandatory (FastAPI redirects otherwise).
 *
 * Repeated query params (`attr.<code>=a&attr.<code>=b`) are serialized with
 * `indexes: null` so FastAPI reads them via `query_params.multi_items()`.
 */
const REPEAT_PARAMS_SERIALIZER = { indexes: null };

/**
 * Search products with facets (OR inside a group / AND between groups).
 * @param {Object} params - q, category_id, page, hits_per_page, sort,
 *   price_min, price_max, repeated `attr.<code>` (array values),
 *   `attrs_range.<code>` ("min:max" strings).
 * @param {AbortSignal} [signal]
 * @returns {Promise<{items: Array, total: number, page: number, pages: number, facets: Array}>}
 */
export const searchProducts = async (params, signal) => {
  const { data } = await api.get('/search/', {
    params,
    signal,
    paramsSerializer: REPEAT_PARAMS_SERIALIZER,
  });
  return data;
};

/**
 * Search box suggestions.
 * @param {string} q
 * @param {number} [limit]
 * @param {AbortSignal} [signal]
 * @returns {Promise<{suggestions: Array<{type: string, id: number, name: string}>}>}
 */
export const getSearchSuggestions = async (q, limit = 10, signal) => {
  const { data } = await api.get('/search/suggestions/', {
    params: { q, limit },
    signal,
  });
  return data;
};

/**
 * Search values of long enum facets (facet-search proxy).
 * Optional in the MVP UI — reserved for future facet value autocomplete.
 * @param {string} facet
 * @param {string} [q]
 * @param {AbortSignal} [signal]
 * @returns {Promise<{values: Array<{value: any, count: number}>}>}
 */
export const getFacetValues = async (facet, q, signal) => {
  const { data } = await api.get('/search/facet-values/', {
    params: { facet, ...(q ? { q } : {}) },
    signal,
  });
  return data;
};
