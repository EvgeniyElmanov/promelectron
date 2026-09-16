import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import CategoryNav from '@/components/CategoryNav.vue';

vi.mock('@/services/api', () => ({
  default: { get: vi.fn() },
}));

import api from '@/services/api';

const makeCategories = (n) =>
  Array.from({ length: n }, (_, i) => ({
    id: i + 1,
    name: `Категория ${i + 1}`,
    parent_id: null,
  }));

const mountOpts = {
  global: {
    stubs: {
      RouterLink: {
        template: '<a :href="to.path || to" :data-testid="$attrs[\'data-testid\']"><slot /></a>',
        props: ['to'],
        inheritAttrs: false,
      },
    },
  },
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe('CategoryNav (D-10)', () => {
  it('рендерит корневые категории (до 7 + «Ещё») и красную «Распродажа»', async () => {
    api.get.mockResolvedValue({ data: { items: [...makeCategories(9), { id: 50, name: 'Дочерняя', parent_id: 1 }], total: 10 } });
    const wrapper = mount(CategoryNav, mountOpts);
    await flushPromises();

    expect(wrapper.find('[data-testid="category-nav"]').exists()).toBe(true);
    expect(wrapper.findAll('[data-testid^="category-nav-link-"]')).toHaveLength(7);
    expect(wrapper.find('[data-testid="category-nav-link-50"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="category-nav-more"]').exists()).toBe(true);

    const sale = wrapper.find('[data-testid="category-nav-sale"]');
    expect(sale.exists()).toBe(true);
    expect(sale.text()).toBe('Распродажа');
    expect(sale.attributes('href')).toBe('/');
  });

  it('без переполнения «Ещё» не показывается', async () => {
    api.get.mockResolvedValue({ data: { items: makeCategories(3), total: 3 } });
    const wrapper = mount(CategoryNav, mountOpts);
    await flushPromises();
    expect(wrapper.find('[data-testid="category-nav-more"]').exists()).toBe(false);
  });

  it('при ошибке API строка скрывается (S-05)', async () => {
    api.get.mockRejectedValue(new Error('network'));
    const wrapper = mount(CategoryNav, mountOpts);
    await flushPromises();
    expect(wrapper.find('[data-testid="category-nav"]').exists()).toBe(false);
  });
});
