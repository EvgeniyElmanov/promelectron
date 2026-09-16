import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import PromoStack from '@/components/home/PromoStack.vue';

const pushMock = vi.hoisted(() => vi.fn());

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: pushMock }),
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe('PromoStack (D-06)', () => {
  it('рендерит две промо-карточки', () => {
    const wrapper = mount(PromoStack);
    expect(wrapper.find('[data-testid="promo-stack"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="promo-smartphones"]').text()).toContain('Смартфоны');
    expect(wrapper.find('[data-testid="promo-sale"]').text()).toContain('Скидки до 30%');
  });

  it('«Смартфоны» ведёт на /catalog?category_id, fallback — /catalog', async () => {
    const withCat = mount(PromoStack, { props: { smartphonesCategoryId: 7 } });
    await withCat.find('[data-testid="promo-smartphones"]').trigger('click');
    expect(pushMock).toHaveBeenCalledWith({ path: '/catalog', query: { category_id: '7' } });

    const withoutCat = mount(PromoStack);
    await withoutCat.find('[data-testid="promo-smartphones"]').trigger('click');
    expect(pushMock).toHaveBeenCalledWith('/catalog');
  });

  it('«Скидки» ведут на таб «Скидки» главной (/?tab=sale)', async () => {
    const wrapper = mount(PromoStack);
    await wrapper.find('[data-testid="promo-sale"]').trigger('click');
    expect(pushMock).toHaveBeenCalledWith({ path: '/', query: { tab: 'sale' } });
  });

  it('фон карточки «Смартфоны» — image_url категории, без него — чистая карточка', () => {
    const wrapper = mount(PromoStack, { props: { smartphonesImageUrl: '/uploads/phone.png' } });
    expect(wrapper.find('.promo-stack__bg').attributes('style')).toContain('/uploads/phone.png');

    const noImg = mount(PromoStack);
    expect(noImg.find('.promo-stack__bg').attributes('style') || '').not.toContain('url(');
  });
});
