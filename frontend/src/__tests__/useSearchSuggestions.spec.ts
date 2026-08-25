import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useSearchSuggestions } from '@/composables/useSearchSuggestions';
import api from '@/services/api';

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
  },
}));

describe('useSearchSuggestions — fetchSuggestions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
  });

  it('мапит фактическую форму backend {suggestions: [{type, id, name}]} в Suggestions (D-06)', async () => {
    api.get.mockResolvedValueOnce({
      data: {
        suggestions: [
          { type: 'product', id: 1, name: 'Смартфон Xiaomi' },
          { type: 'product', id: 2, name: 'Смартфон Samsung' },
        ],
      },
    });

    const { suggestions, fetchSuggestions } = useSearchSuggestions();
    await fetchSuggestions('смартфон уник1');

    expect(suggestions.value).toEqual({
      queries: [],
      categories: [],
      brands: [],
      products: [
        { id: 1, name: 'Смартфон Xiaomi' },
        { id: 2, name: 'Смартфон Samsung' },
      ],
    });
    // Форма без price/image не должна уходить в fallback на /products/
    expect(api.get).toHaveBeenCalledTimes(1);
    expect(api.get.mock.calls[0][0]).toBe('/search/suggestions/');
  });

  it('старую форму {queries, categories, brands, products} принимает как есть', async () => {
    const legacy = {
      queries: ['смартфон'],
      categories: [{ id: 1, name: 'Телефоны' }],
      brands: ['Xiaomi'],
      products: [{ id: 1, name: 'Смартфон Xiaomi', price: 12999, image: '/img/1.jpg' }],
    };
    api.get.mockResolvedValueOnce({ data: legacy });

    const { suggestions, fetchSuggestions } = useSearchSuggestions();
    await fetchSuggestions('старая форма уник2');

    expect(suggestions.value).toEqual(legacy);
  });

  it('при ошибке /search/suggestions/ отрабатывает fallback на /products/', async () => {
    api.get
      .mockRejectedValueOnce({ response: { status: 404 }, message: 'Not Found' })
      .mockResolvedValueOnce({
        data: {
          items: [{ id: 1, name: 'Смартфон Xiaomi', price: 12999, images: ['/img/1.jpg'] }],
          total: 1,
        },
      });

    const { suggestions, fetchSuggestions } = useSearchSuggestions();
    await fetchSuggestions('ошибка фолбэк уник3');

    expect(api.get).toHaveBeenCalledTimes(2);
    expect(api.get.mock.calls[1][0]).toBe('/products/');
    expect(suggestions.value.products).toEqual([
      { id: 1, name: 'Смартфон Xiaomi', price: 12999, image: '/img/1.jpg' },
    ]);
  });

  it('фильтрует не-product suggestions из новой формы', async () => {
    api.get.mockResolvedValueOnce({
      data: {
        suggestions: [
          { type: 'category', id: 5, name: 'Телефоны' },
          { type: 'product', id: 1, name: 'Смартфон Xiaomi' },
        ],
      },
    });

    const { suggestions, fetchSuggestions } = useSearchSuggestions();
    await fetchSuggestions('фильтр категорий уник4');

    expect(suggestions.value.products).toEqual([{ id: 1, name: 'Смартфон Xiaomi' }]);
  });
});

describe('useSearchSuggestions — probe-флаг (issue #171)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
  });

  it('после 404 на /search/suggestions/ ставит sessionStorage-флаг и дальше идёт в fallback без /search/*', async () => {
    api.get
      .mockRejectedValueOnce({ response: { status: 404 }, message: 'Not Found' })
      .mockResolvedValueOnce({ data: { items: [], total: 0 } });

    const { fetchSuggestions } = useSearchSuggestions();
    await fetchSuggestions('probe первый уник5');

    expect(api.get.mock.calls[0][0]).toBe('/search/suggestions/');
    expect(sessionStorage.getItem('search_api_unavailable')).toBe('1');

    api.get.mockClear();
    api.get.mockResolvedValueOnce({
      data: {
        items: [{ id: 1, name: 'Смартфон Xiaomi', price: 12999, images: ['/img/1.jpg'] }],
        total: 1,
      },
    });

    await fetchSuggestions('probe второй уник6');

    // /search/suggestions/ больше не вызывается — сразу fallback на /products/
    expect(api.get).toHaveBeenCalledTimes(1);
    expect(api.get.mock.calls[0][0]).toBe('/products/');
  });

  it('не-404 ошибка не включает probe-флаг', async () => {
    api.get
      .mockRejectedValueOnce({ response: { status: 500 }, message: 'Server Error' })
      .mockResolvedValueOnce({ data: { items: [], total: 0 } });

    const { fetchSuggestions } = useSearchSuggestions();
    await fetchSuggestions('probe 500 уник7');

    expect(sessionStorage.getItem('search_api_unavailable')).toBeNull();
  });
});

describe('useSearchSuggestions — fetchRecommendations (issue #171)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
  });

  it('не вызывает несуществующий /search/recommendations/ — сразу /products/ в формате Recommendations', async () => {
    api.get.mockResolvedValueOnce({
      data: {
        items: [{ id: 1, name: 'Смартфон Xiaomi', price: 12999, images: ['/img/1.jpg'] }],
        total: 1,
      },
    });

    const { recommendations, fetchRecommendations } = useSearchSuggestions();
    await fetchRecommendations();

    expect(api.get).toHaveBeenCalledTimes(1);
    expect(api.get.mock.calls[0][0]).toBe('/products/');
    expect(recommendations.value).toEqual({
      trending: [],
      popular_categories: [],
      recommendations: [
        { id: 1, name: 'Смартфон Xiaomi', price: 12999, image: '/img/1.jpg' },
      ],
    });
  });
});
