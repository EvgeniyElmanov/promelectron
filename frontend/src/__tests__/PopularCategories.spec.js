import { describe, it, expect, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import PopularCategories from '@/components/home/PopularCategories.vue';

const pushMock = vi.hoisted(() => vi.fn());

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock }),
  RouterLink: { template: '<a><slot /></a>' },
}));

const makeCategories = (n) =>
  Array.from({ length: n }, (_, i) => ({
    id: i + 1,
    name: `Категория ${i + 1}`,
    parent_id: null,
    product_count: 10 + i,
  }));

describe('PopularCategories (D-07)', () => {
  it('рендерит корневые категории из props', () => {
    const wrapper = mount(PopularCategories, {
      props: { categories: makeCategories(3) },
    });
    expect(wrapper.find('[data-testid="popular-categories"]').exists()).toBe(true);
    expect(wrapper.findAll('[data-testid^="category-card-"]')).toHaveLength(3);
  });

  it('отсекает дочерние категории и ограничивает 6 карточками', () => {
    const items = [...makeCategories(8), { id: 99, name: 'Дочерняя', parent_id: 1, product_count: 5 }];
    const wrapper = mount(PopularCategories, { props: { categories: items } });
    expect(wrapper.findAll('[data-testid^="category-card-"]')).toHaveLength(6);
    expect(wrapper.find('[data-testid="category-card-99"]').exists()).toBe(false);
  });

  it('передаёт image_url в карточку (через getImageUrl medium, F-06)', () => {
    const categories = [{ id: 1, name: 'Ноутбуки', parent_id: null, product_count: 5, image_url: '/uploads/cat.png' }];
    const wrapper = mount(PopularCategories, { props: { categories } });
    expect(wrapper.find('.category-card__img').attributes('src')).toBe('/uploads/cat.png?size=medium');
  });

  it('клик по карточке ведёт на /catalog?category_id=<id>', async () => {
    const wrapper = mount(PopularCategories, { props: { categories: makeCategories(2) } });
    await wrapper.find('[data-testid="category-card-2"]').trigger('click');
    expect(pushMock).toHaveBeenCalledWith({ path: '/catalog', query: { category_id: '2' } });
  });

  it('показывает skeleton при loading и скрывает секцию при пустом списке', () => {
    const loading = mount(PopularCategories, { props: { loading: true } });
    expect(loading.findAll('.popular-categories__skeleton').length).toBeGreaterThan(0);

    const empty = mount(PopularCategories, { props: { categories: [] } });
    expect(empty.find('[data-testid="popular-categories"]').exists()).toBe(false);
  });

  it('ссылка «Все категории» ведёт на /catalog', () => {
    const wrapper = mount(PopularCategories, { props: { categories: makeCategories(2) } });
    expect(wrapper.find('[data-testid="categories-view-all"]').exists()).toBe(true);
  });
});
