import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick, reactive } from 'vue'
import SearchBar from '@/components/SearchBar.vue'

// Mutable mock state so each test can configure data
const mockState = reactive({
  query: '',
  isLoading: false,
  recommendations: null,
  suggestions: null,
  error: null,
});

const mockFetchRecommendations = vi.fn();
const mockFetchSuggestions = vi.fn();

const mockAddSearchHistory = vi.fn();
const mockRemoveSearchHistory = vi.fn();
const mockClearSearchHistory = vi.fn();
const mockGetSearchHistory = vi.fn(() => []);

vi.mock('@/composables/useSearchSuggestions', () => ({
  useSearchSuggestions: () => ({
    get query() { return { value: mockState.query }; },
    get isLoading() { return { value: mockState.isLoading }; },
    get recommendations() { return { value: mockState.recommendations }; },
    get suggestions() { return { value: mockState.suggestions }; },
    get error() { return { value: mockState.error }; },
    fetchRecommendations: mockFetchRecommendations,
    fetchSuggestions: mockFetchSuggestions,
  }),
  getSearchHistory: () => mockGetSearchHistory(),
  addSearchHistory: (q) => mockAddSearchHistory(q),
  removeSearchHistory: (q) => mockRemoveSearchHistory(q),
  clearSearchHistory: () => mockClearSearchHistory(),
}));

describe('SearchBar.vue', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    mockState.query = '';
    mockState.isLoading = false;
    mockState.recommendations = null;
    mockState.suggestions = null;
    mockState.error = null;
    mockFetchRecommendations.mockClear();
    mockFetchSuggestions.mockClear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('отображает input с placeholder', () => {
    const wrapper = mount(SearchBar);
    const input = wrapper.find('input[type="text"]');
    expect(input.exists()).toBe(true);
    expect(input.attributes('placeholder')).toBe('Поиск товаров...');
    expect(input.attributes('data-testid')).toBe('search-bar');
  });

  it('эмитит update:modelValue при вводе текста', async () => {
    const wrapper = mount(SearchBar);
    const input = wrapper.find('input[type="text"]');
    await input.setValue('смартфон');
    expect(wrapper.emitted('update:modelValue')).toBeTruthy();
    expect(wrapper.emitted('update:modelValue')[0]).toEqual(['смартфон']);
  });

  it('открывает dropdown при фокусе и загружает рекомендации', async () => {
    const wrapper = mount(SearchBar);
    const input = wrapper.find('input[type="text"]');
    await input.trigger('focus');
    await nextTick();

    expect(mockFetchRecommendations).toHaveBeenCalled();
    expect(wrapper.find('[data-testid="search-bar-dropdown"]').exists()).toBe(true);
  });

  it('показывает рекомендации при пустом запросе', async () => {
    mockState.recommendations = {
      trending: ['смартфон', 'наушники'],
      popular_categories: [{ id: 1, name: 'Телефоны' }],
      recommendations: [{ id: 10, name: 'Xiaomi Redmi', price: 12999 }],
    };

    const wrapper = mount(SearchBar);
    await wrapper.find('input[type="text"]').trigger('focus');
    await nextTick();

    expect(wrapper.text()).toContain('Часто ищут');
    expect(wrapper.text()).toContain('смартфон');
    expect(wrapper.text()).toContain('Популярные категории');
    expect(wrapper.text()).toContain('Вам может понравиться');
  });

  it('эмитит submit при нажатии Enter', async () => {
    const wrapper = mount(SearchBar, {
      props: { modelValue: 'телефон' },
    });
    const input = wrapper.find('input[type="text"]');
    await input.trigger('keydown.enter');

    expect(wrapper.emitted('submit')).toBeTruthy();
    expect(wrapper.emitted('submit')[0]).toEqual(['телефон']);
  });

  it('закрывает dropdown при клике вне компонента', async () => {
    const wrapper = mount(SearchBar, { attachTo: document.body });
    await wrapper.find('input[type="text"]').trigger('focus');
    await nextTick();
    expect(wrapper.find('[data-testid="search-bar-dropdown"]').exists()).toBe(true);

    document.body.click();
    await nextTick();
    expect(wrapper.find('[data-testid="search-bar-dropdown"]').exists()).toBe(false);

    wrapper.unmount();
  });

  it('очищает запрос по кнопке', async () => {
    const wrapper = mount(SearchBar, {
      props: { modelValue: 'тест' },
    });
    const clearBtn = wrapper.find('[data-testid="search-bar-clear"]');
    expect(clearBtn.exists()).toBe(true);

    await clearBtn.trigger('click');
    expect(wrapper.emitted('update:modelValue')).toBeTruthy();
    expect(wrapper.emitted('update:modelValue').at(-1)).toEqual(['']);
  });

  it('выбирает текстовую подсказку и эмитит submit', async () => {
    mockState.suggestions = {
      queries: ['смартфон', 'смарт-часы'],
      categories: [],
      brands: [],
      products: [],
    };

    const wrapper = mount(SearchBar, {
      props: { modelValue: 'смар' },
    });
    await wrapper.find('input[type="text"]').trigger('focus');
    await nextTick();

    const suggestion = wrapper.find('[data-testid="search-bar-text-suggestion"]');
    expect(suggestion.exists()).toBe(true);

    await suggestion.trigger('click');
    expect(wrapper.emitted('submit')).toBeTruthy();
    expect(wrapper.emitted('submit')[0]).toEqual(['смартфон']);
  });

  it('показывает товары в подсказках', async () => {
    mockState.suggestions = {
      queries: [],
      categories: [],
      brands: [],
      products: [
        { id: 1, name: 'Смартфон Xiaomi', price: 12999, image: '/img/1.jpg' },
      ],
    };

    const wrapper = mount(SearchBar, {
      props: { modelValue: 'xiaomi' },
    });
    await wrapper.find('input[type="text"]').trigger('focus');
    await nextTick();

    const product = wrapper.find('[data-testid="search-bar-product-suggestion"]');
    expect(product.exists()).toBe(true);
    expect(wrapper.text()).toContain('Смартфон Xiaomi');
    expect(wrapper.text()).toContain('12');
    expect(wrapper.text()).toContain('999');
    expect(wrapper.text()).toContain('₽');
  });

  it('показывает товары без цены/фото (новая форма backend suggestions, D-06)', async () => {
    mockState.suggestions = {
      queries: [],
      categories: [],
      brands: [],
      products: [{ id: 1, name: 'Смартфон Xiaomi' }],
    };

    const wrapper = mount(SearchBar, {
      props: { modelValue: 'xiaomi' },
    });
    await wrapper.find('input[type="text"]').trigger('focus');
    await nextTick();

    const product = wrapper.find('[data-testid="search-bar-product-suggestion"]');
    expect(product.exists()).toBe(true);
    expect(wrapper.text()).toContain('Смартфон Xiaomi');
    // price/image отсутствуют — блоки цены и картинки не рендерятся (v-if)
    expect(product.find('.search-bar__product-price').exists()).toBe(false);
    expect(product.find('.search-bar__product-img').exists()).toBe(false);
  });

  it('показывает "Ничего не найдено" при отсутствии результатов', async () => {
    mockState.suggestions = {
      queries: [],
      categories: [],
      brands: [],
      products: [],
    };

    const wrapper = mount(SearchBar, {
      props: { modelValue: 'zzz' },
    });
    await wrapper.find('input[type="text"]').trigger('focus');
    await nextTick();

    expect(wrapper.text()).toContain('Ничего не найдено');
  });

  it('не показывает "Ничего не найдено" при ошибке API если есть fallback товары', async () => {
    mockState.recommendations = {
      trending: [],
      popular_categories: [],
      recommendations: [
        { id: 1, name: 'Смартфон Nova X12', price: 45990 },
        { id: 2, name: 'Ноутбук Pro', price: 89990 },
      ],
    };
    mockState.suggestions = null; // API error

    const wrapper = mount(SearchBar, {
      props: { modelValue: 'смарт' },
    });
    await wrapper.find('input[type="text"]').trigger('focus');
    await nextTick();

    expect(wrapper.text()).not.toContain('Ничего не найдено');
    expect(wrapper.text()).toContain('Смартфон Nova X12');
    expect(wrapper.text()).not.toContain('Ноутбук Pro');
  });

  it('не показывает "Ничего не найдено" во время загрузки', async () => {
    mockState.isLoading = true;
    mockState.suggestions = null;

    const wrapper = mount(SearchBar, {
      props: { modelValue: 'тест' },
    });
    await wrapper.find('input[type="text"]').trigger('focus');
    await nextTick();

    expect(wrapper.text()).not.toContain('Ничего не найдено');
  });
})
