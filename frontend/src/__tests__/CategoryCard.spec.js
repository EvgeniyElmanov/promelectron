import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import CategoryCard from '@/components/CategoryCard.vue';

describe('CategoryCard', () => {
  it('renders name, testid and product count', () => {
    const wrapper = mount(CategoryCard, {
      props: { id: 3, name: 'Ноутбуки', productCount: 312 },
    });
    const card = wrapper.find('[data-testid="category-card-3"]');
    expect(card.exists()).toBe(true);
    expect(card.text()).toContain('Ноутбуки');
    expect(card.text()).toContain('312 товаров');
  });

  it('hides product count when not provided', () => {
    const wrapper = mount(CategoryCard, {
      props: { id: 1, name: 'Мониторы' },
    });
    expect(wrapper.find('.category-card__count').exists()).toBe(false);
  });

  it('renders placeholder letter when no imageUrl', () => {
    const wrapper = mount(CategoryCard, {
      props: { id: 1, name: 'Мониторы' },
    });
    expect(wrapper.find('.category-card__img').exists()).toBe(false);
    expect(wrapper.find('.category-card__image-letter').text()).toBe('М');
  });

  it('renders lazy image when imageUrl is provided', () => {
    const wrapper = mount(CategoryCard, {
      props: { id: 1, name: 'Мониторы', imageUrl: '/img/cat.png' },
    });
    const img = wrapper.find('.category-card__img');
    expect(img.exists()).toBe(true);
    expect(img.attributes('loading')).toBe('lazy');
    expect(wrapper.find('.category-card__image-letter').exists()).toBe(false);
  });

  it('emits select with id on click', async () => {
    const wrapper = mount(CategoryCard, {
      props: { id: 7, name: 'Кабели' },
    });
    await wrapper.trigger('click');
    expect(wrapper.emitted('select')).toEqual([[7]]);
  });
});
