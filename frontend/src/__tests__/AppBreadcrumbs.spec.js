import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createMemoryHistory } from 'vue-router';
import AppBreadcrumbs from '@/components/ui/AppBreadcrumbs.vue';

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/', component: { template: '<div />' } },
    { path: '/catalog', component: { template: '<div />' } },
  ],
});

const mountBreadcrumbs = (items) =>
  mount(AppBreadcrumbs, {
    props: { items },
    global: { plugins: [router] },
  });

describe('AppBreadcrumbs', () => {
  it('renders all items', () => {
    const wrapper = mountBreadcrumbs([
      { label: 'Главная', to: '/' },
      { label: 'Каталог', to: '/catalog' },
      { label: 'Ноутбуки' },
    ]);
    expect(wrapper.text()).toContain('Главная');
    expect(wrapper.text()).toContain('Каталог');
    expect(wrapper.text()).toContain('Ноутбуки');
  });

  it('renders intermediate items as links and the last one as plain text', () => {
    const wrapper = mountBreadcrumbs([
      { label: 'Главная', to: '/' },
      { label: 'Ноутбуки' },
    ]);
    const links = wrapper.findAll('a');
    expect(links).toHaveLength(1);
    expect(links[0].text()).toBe('Главная');
    const current = wrapper.find('.app-breadcrumbs__current');
    expect(current.text()).toBe('Ноутбуки');
    expect(current.attributes('aria-current')).toBe('page');
  });

  it('renders separators between items only', () => {
    const wrapper = mountBreadcrumbs([
      { label: 'Главная', to: '/' },
      { label: 'Каталог', to: '/catalog' },
      { label: 'Ноутбуки' },
    ]);
    expect(wrapper.findAll('.app-breadcrumbs__sep')).toHaveLength(2);
  });
});
