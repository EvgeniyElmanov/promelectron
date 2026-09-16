import { describe, it, expect, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import HeroBanner from '@/components/home/HeroBanner.vue';

const pushMock = vi.hoisted(() => vi.fn());

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock }),
}));

describe('HeroBanner (D-05)', () => {
  it('рендерит заголовок, подзаголовок и одну CTA по макету', () => {
    const wrapper = mount(HeroBanner);
    expect(wrapper.find('[data-testid="hero-banner"]').exists()).toBe(true);
    expect(wrapper.find('h1.hero-banner__title').text()).toBe('Новый уровень производительности');
    expect(wrapper.text()).toContain('Современные ноутбуки для работы, учёбы и развлечений');
    expect(wrapper.find('[data-testid="hero-cta-laptops"]').text()).toContain('Смотреть ноутбуки');
  });

  it('CTA ведёт на /catalog?category_id при известной категории', async () => {
    const wrapper = mount(HeroBanner, { props: { categoryId: 5 } });
    await wrapper.find('[data-testid="hero-cta-laptops"]').trigger('click');
    expect(pushMock).toHaveBeenCalledWith({ path: '/catalog', query: { category_id: '5' } });
  });

  it('CTA ведёт на /catalog без фильтра, если категория не найдена (fallback)', async () => {
    const wrapper = mount(HeroBanner);
    await wrapper.find('[data-testid="hero-cta-laptops"]').trigger('click');
    expect(pushMock).toHaveBeenCalledWith('/catalog');
  });

  it('показывает фото при imageUrl и скрывает без него', () => {
    const withImage = mount(HeroBanner, { props: { imageUrl: '/uploads/laptop.png' } });
    expect(withImage.find('[data-testid="hero-image"]').attributes('src')).toBe('/uploads/laptop.png');

    const withoutImage = mount(HeroBanner);
    expect(withoutImage.find('[data-testid="hero-image"]').exists()).toBe(false);
  });
});
