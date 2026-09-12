import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createMemoryHistory } from 'vue-router';
import AppFooter from '@/components/AppFooter.vue';

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/', component: { template: '<div />' } },
    { path: '/orders', component: { template: '<div />' } },
  ],
});

describe('AppFooter', () => {
  it('renders footer with brand, columns, phone and payments', () => {
    const wrapper = mount(AppFooter, { global: { plugins: [router] } });
    expect(wrapper.find('[data-testid="app-footer"]').exists()).toBe(true);
    expect(wrapper.text()).toContain('Пром Электрон');
    expect(wrapper.text()).toContain('8 (800) 500-45-85');
    expect(wrapper.text()).toContain('Покупателям');
    expect(wrapper.text()).toContain('Компания');
    expect(wrapper.findAll('.app-footer__payment').length).toBeGreaterThan(0);
  });

  it('renders links only for existing routes', () => {
    const wrapper = mount(AppFooter, { global: { plugins: [router] } });
    const hrefs = wrapper.findAll('a').map((a) => a.attributes('href'));
    expect(hrefs).toContain('tel:88005004585');
  });
});
