import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import HeroBanner from '@/components/home/HeroBanner.vue';

describe('HeroBanner', () => {
  it('renders title, description, CTAs and facts', () => {
    const wrapper = mount(HeroBanner);
    expect(wrapper.find('[data-testid="hero-banner"]').exists()).toBe(true);
    // h2, а не h1: единственный H1 на маршруте `/` — «Каталог» (review H001, решение владельца)
    expect(wrapper.find('h2.hero-banner__title').text()).toBeTruthy();
    expect(wrapper.find('[data-testid="hero-cta-catalog"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="hero-cta-new"]').exists()).toBe(true);
    expect(wrapper.findAll('.hero-banner__fact').length).toBeGreaterThan(0);
  });

  it('emits cta-click on primary CTA', async () => {
    const wrapper = mount(HeroBanner);
    await wrapper.find('[data-testid="hero-cta-catalog"]').trigger('click');
    expect(wrapper.emitted('cta-click')).toBeTruthy();
  });

  it('emits show-new on secondary CTA', async () => {
    const wrapper = mount(HeroBanner);
    await wrapper.find('[data-testid="hero-cta-new"]').trigger('click');
    expect(wrapper.emitted('show-new')).toBeTruthy();
  });
});
