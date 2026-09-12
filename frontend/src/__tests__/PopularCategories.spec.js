import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import PopularCategories from '@/components/home/PopularCategories.vue';
import api from '@/services/api';

vi.mock('@/services/api', () => ({
  default: { get: vi.fn() },
}));

const makeCategories = (n) =>
  Array.from({ length: n }, (_, i) => ({
    id: i + 1,
    name: `Категория ${i + 1}`,
    parent_id: null,
    product_count: 10 + i,
  }));

beforeEach(() => {
  vi.clearAllMocks();
});

describe('PopularCategories', () => {
  it('renders root categories after fetch', async () => {
    api.get.mockResolvedValue({ data: { items: makeCategories(3), total: 3 } });
    const wrapper = mount(PopularCategories);
    await flushPromises();
    expect(wrapper.find('[data-testid="popular-categories"]').exists()).toBe(true);
    expect(wrapper.findAll('[data-testid^="category-card-"]')).toHaveLength(3);
  });

  it('filters out non-root categories and limits to 8', async () => {
    const items = [...makeCategories(10), { id: 99, name: 'Дочерняя', parent_id: 1, product_count: 5 }];
    api.get.mockResolvedValue({ data: { items, total: items.length } });
    const wrapper = mount(PopularCategories);
    await flushPromises();
    expect(wrapper.findAll('[data-testid^="category-card-"]')).toHaveLength(8);
    expect(wrapper.find('[data-testid="category-card-99"]').exists()).toBe(false);
  });

  it('emits select with category id on card click', async () => {
    api.get.mockResolvedValue({ data: { items: makeCategories(2), total: 2 } });
    const wrapper = mount(PopularCategories);
    await flushPromises();
    await wrapper.find('[data-testid="category-card-2"]').trigger('click');
    expect(wrapper.emitted('select')).toEqual([[2]]);
  });

  it('hides section when fetch fails', async () => {
    api.get.mockRejectedValue(new Error('network'));
    const wrapper = mount(PopularCategories);
    await flushPromises();
    expect(wrapper.find('[data-testid="popular-categories"]').exists()).toBe(false);
  });

  it('hides section when categories list is empty', async () => {
    api.get.mockResolvedValue({ data: { items: [], total: 0 } });
    const wrapper = mount(PopularCategories);
    await flushPromises();
    expect(wrapper.find('[data-testid="popular-categories"]').exists()).toBe(false);
  });

  it('emits view-all on header button click when categories exceed 8', async () => {
    api.get.mockResolvedValue({ data: { items: makeCategories(10), total: 10 } });
    const wrapper = mount(PopularCategories);
    await flushPromises();
    await wrapper.find('[data-testid="categories-view-all"]').trigger('click');
    expect(wrapper.emitted('view-all')).toBeTruthy();
  });

  it('hides view-all button when all root categories fit', async () => {
    api.get.mockResolvedValue({ data: { items: makeCategories(3), total: 3 } });
    const wrapper = mount(PopularCategories);
    await flushPromises();
    expect(wrapper.find('[data-testid="categories-view-all"]').exists()).toBe(false);
  });
});
