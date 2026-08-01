import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createMemoryHistory } from 'vue-router';
import { useCatalogSearch, __resetSearchProbeForTests } from '@/composables/useCatalogSearch';
import { searchProducts } from '@/api/search';

vi.mock('@/api/search', () => ({
  searchProducts: vi.fn(),
  getSearchSuggestions: vi.fn(),
  getFacetValues: vi.fn(),
}));

const SEARCH_RESPONSE = {
  items: [{ id: 1, sku: 'SKU-1', name: 'Product 1', price: 9999, stock: 10, category_id: 1, categories: {}, attrs: {} }],
  total: 1,
  page: 1,
  pages: 1,
  facets: [],
};

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/', component: { template: '<div />' } }],
  });
}

async function mountCatalog(url = '/') {
  const router = makeRouter(url);
  await router.push(url);
  await router.isReady();
  let catalog;
  const wrapper = mount(
    {
      template: '<div />',
      setup() {
        catalog = useCatalogSearch();
        return {};
      },
    },
    { global: { plugins: [router] } },
  );
  return { catalog, router, wrapper };
}

describe('useCatalogSearch', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    __resetSearchProbeForTests();
    searchProducts.mockResolvedValue(SEARCH_RESPONSE);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('probe: 404 → searchAvailable = false (fallback на /products/)', async () => {
    searchProducts.mockRejectedValueOnce({ response: { status: 404 } });
    const { catalog } = await mountCatalog();
    const available = await catalog.probe();
    expect(available).toBe(false);
    expect(catalog.searchAvailable.value).toBe(false);
  });

  it('probe: успешный ответ → searchAvailable = true, результат кэшируется', async () => {
    const { catalog } = await mountCatalog();
    expect(await catalog.probe()).toBe(true);
    expect(await catalog.probe()).toBe(true);
    // Второй probe не делает новый запрос — module-scope кэш (D-01).
    expect(searchProducts).toHaveBeenCalledTimes(1);
  });

  it('probe: временная ошибка (503) не кэшируется — повторная попытка возможна', async () => {
    searchProducts.mockRejectedValueOnce({ response: { status: 503 } });
    const { catalog } = await mountCatalog();
    expect(await catalog.probe()).toBe(false);
    searchProducts.mockResolvedValueOnce(SEARCH_RESPONSE);
    expect(await catalog.probe()).toBe(true);
    expect(searchProducts).toHaveBeenCalledTimes(2);
  });

  it('toggleFacetValue сериализует OR внутри группы как массив attr.<code>', async () => {
    const { catalog } = await mountCatalog();
    catalog.toggleFacetValue('brand', 'Samsung');
    await vi.waitFor(() => expect(searchProducts).toHaveBeenCalledTimes(1));
    expect(searchProducts.mock.calls[0][0]['attr.brand']).toEqual(['Samsung']);

    catalog.toggleFacetValue('brand', 'LG');
    await vi.waitFor(() => expect(searchProducts).toHaveBeenCalledTimes(2));
    expect(searchProducts.mock.calls[1][0]['attr.brand']).toEqual(['Samsung', 'LG']);

    // Повторный клик снимает значение
    catalog.toggleFacetValue('brand', 'Samsung');
    await vi.waitFor(() => expect(searchProducts).toHaveBeenCalledTimes(3));
    expect(searchProducts.mock.calls[2][0]['attr.brand']).toEqual(['LG']);
  });

  it('setRange сериализует attrs_range.<code>=min:max', async () => {
    const { catalog } = await mountCatalog();
    catalog.setRange('power', 100, 500);
    await vi.waitFor(() => expect(searchProducts).toHaveBeenCalledTimes(1));
    expect(searchProducts.mock.calls[0][0]['attrs_range.power']).toBe('100:500');
  });

  it('setPrice и setSort попадают в query params', async () => {
    const { catalog } = await mountCatalog();
    catalog.setPrice(1000, 5000);
    await vi.waitFor(() => expect(searchProducts).toHaveBeenCalledTimes(1));
    expect(searchProducts.mock.calls[0][0].price_min).toBe(1000);
    expect(searchProducts.mock.calls[0][0].price_max).toBe(5000);

    catalog.setSort('price_asc');
    await vi.waitFor(() => expect(searchProducts).toHaveBeenCalledTimes(2));
    expect(searchProducts.mock.calls[1][0].sort).toBe('price_asc');
  });

  it('состояние фильтров синхронизируется с URL query (D-03)', async () => {
    const { catalog, router } = await mountCatalog();
    catalog.toggleFacetValue('brand', 'Samsung');
    await vi.waitFor(() => expect(router.currentRoute.value.query['attr.brand']).toEqual(['Samsung']));
    catalog.setPrice(100, 200);
    await vi.waitFor(() => {
      expect(router.currentRoute.value.query.price_min).toBe('100');
      expect(router.currentRoute.value.query.price_max).toBe('200');
    });
  });

  it('initFromUrl восстанавливает состояние из URL (перезагрузка по ссылке)', async () => {
    const { catalog } = await mountCatalog('/?attr.brand=Samsung&attr.brand=LG&price_min=100&price_max=500&sort=price_desc&category_id=3&attrs_range.power=10:50');
    catalog.initFromUrl();
    expect([...catalog.selected.get('brand')]).toEqual(['Samsung', 'LG']);
    expect(catalog.priceRange.min).toBe(100);
    expect(catalog.priceRange.max).toBe(500);
    expect(catalog.sort.value).toBe('price_desc');
    expect(catalog.categoryId.value).toBe(3);
    expect(catalog.ranges.get('power')).toEqual({ min: 10, max: 50 });
  });

  it('setQuery применяет дебаунс 300 мс', async () => {
    vi.useFakeTimers();
    const { catalog } = await mountCatalog();
    catalog.setQuery('тел');
    catalog.setQuery('телевизор');
    expect(searchProducts).not.toHaveBeenCalled();
    vi.advanceTimersByTime(300);
    await vi.waitFor(() => expect(searchProducts).toHaveBeenCalledTimes(1));
    expect(searchProducts.mock.calls[0][0].q).toBe('телевизор');
  });

  it('новый запрос отменяет предыдущий (AbortController)', async () => {
    const signals = [];
    searchProducts.mockImplementation((params, signal) => {
      signals.push(signal);
      return new Promise(() => {});
    });
    const { catalog } = await mountCatalog();
    catalog.toggleFacetValue('brand', 'Samsung');
    catalog.toggleFacetValue('brand', 'LG');
    expect(signals).toHaveLength(2);
    expect(signals[0].aborted).toBe(true);
    expect(signals[1].aborted).toBe(false);
  });

  it('loadMore инкрементирует page и дописывает items (append)', async () => {
    const paged = {
      ...SEARCH_RESPONSE,
      pages: 3,
      items: [{ id: 2, sku: 'SKU-2', name: 'Product 2', price: 1, stock: 1, category_id: 1, categories: {}, attrs: {} }],
    };
    searchProducts.mockResolvedValue(paged);
    const { catalog } = await mountCatalog();
    await catalog.load();
    expect(catalog.hasMore.value).toBe(true);
    catalog.loadMore();
    await vi.waitFor(() => expect(searchProducts).toHaveBeenCalledTimes(2));
    expect(searchProducts.mock.calls[1][0].page).toBe(2);
    expect(catalog.items.value).toHaveLength(2);
  });

  it('reset очищает фильтры и перезагружает выдачу', async () => {
    const { catalog, router } = await mountCatalog();
    catalog.toggleFacetValue('brand', 'Samsung');
    catalog.setPrice(100, 200);
    await vi.waitFor(() => expect(searchProducts).toHaveBeenCalledTimes(2));
    catalog.reset();
    await vi.waitFor(() => expect(searchProducts).toHaveBeenCalledTimes(3));
    const params = searchProducts.mock.calls[2][0];
    expect(params['attr.brand']).toBeUndefined();
    expect(params.price_min).toBeUndefined();
    expect(router.currentRoute.value.query['attr.brand']).toBeUndefined();
    expect(catalog.selected.size).toBe(0);
  });

  it('F001: ошибка устаревшего (stale) запроса не пишется в error', async () => {
    let rejectStale;
    searchProducts
      .mockImplementationOnce(() => new Promise((_, reject) => { rejectStale = reject; }))
      .mockResolvedValueOnce(SEARCH_RESPONSE);
    const { catalog } = await mountCatalog();

    const firstLoad = catalog.load(); // станет stale
    catalog.toggleFacetValue('brand', 'Samsung'); // новый запрос
    await vi.waitFor(() => expect(searchProducts).toHaveBeenCalledTimes(2));

    rejectStale({ response: { status: 503 } });
    await firstLoad;

    expect(catalog.error.value).toBeNull();
    expect(catalog.items.value).toEqual(SEARCH_RESPONSE.items);
    expect(catalog.loading.value).toBe(false);
  });

  it('F002: числовое значение фасета из URL отмечается и снимается по числу из фасетов', async () => {
    const { catalog } = await mountCatalog('/?attr.size=2.5');
    catalog.initFromUrl();
    expect(catalog.selected.get('size').has('2.5')).toBe(true);

    // Backend отдаёт значение числом 2.5 — toggle не должен создавать дубликат,
    // а должен снять выбор.
    catalog.toggleFacetValue('size', 2.5);
    await vi.waitFor(() => expect(searchProducts).toHaveBeenCalledTimes(1));
    expect(catalog.selected.has('size')).toBe(false);
    expect(searchProducts.mock.calls[0][0]['attr.size']).toBeUndefined();
  });

  it('F003: 404 в обычном запросе сбрасывает searchAvailable и кэш probe (fallback без ошибки)', async () => {
    const { catalog } = await mountCatalog();
    expect(await catalog.probe()).toBe(true);
    expect(catalog.searchAvailable.value).toBe(true);

    // Флаг выключили mid-session: обычный запрос получает 404.
    searchProducts.mockRejectedValueOnce({ response: { status: 404 } });
    await catalog.load();

    expect(catalog.searchAvailable.value).toBe(false);
    expect(catalog.error.value).toBeNull();

    // Кэш probe сброшен — следующий probe делает реальный запрос.
    searchProducts.mockRejectedValueOnce({ response: { status: 404 } });
    expect(await catalog.probe()).toBe(false);
    expect(searchProducts).toHaveBeenCalledTimes(3);
  });
});
