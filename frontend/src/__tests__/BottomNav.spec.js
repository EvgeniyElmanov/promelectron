import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import { ref, computed } from 'vue';
import { readFileSync } from 'node:fs';
import BottomNav from '@/components/BottomNav.vue';

const bottomNavSource = readFileSync('./src/components/BottomNav.vue', 'utf-8');

const mockCartCount = ref(0);

vi.mock('@/composables/useCart', () => ({
  useCart: () => ({
    cartCount: computed(() => mockCartCount.value),
  }),
}));

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: { template: '<div>Home</div>' } },
    { path: '/cart', component: { template: '<div>Cart</div>' } },
  ],
});

describe('BottomNav.vue', () => {
  beforeEach(async () => {
    mockCartCount.value = 0;
    await router.push('/');
    await router.isReady();
  });

  const mountNav = async () => {
    const wrapper = mount(BottomNav, {
      global: { plugins: [router] },
      attachTo: document.body,
    });
    await flushPromises();
    return wrapper;
  };

  it('отображает пункты нижней навигации', async () => {
    const wrapper = await mountNav();
    expect(wrapper.find('[data-testid="nav-Главная"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="nav-Корзина"]').exists()).toBe(true);
    wrapper.unmount();
  });

  it('не показывает бейдж корзины при нулевом количестве', async () => {
    mockCartCount.value = 0;
    const wrapper = await mountNav();
    expect(wrapper.find('.bottom-nav__badge').exists()).toBe(false);
    wrapper.unmount();
  });

  it('показывает бейдж корзины, когда count > 0', async () => {
    mockCartCount.value = 3;
    const wrapper = await mountNav();
    const badge = wrapper.find('.bottom-nav__badge');
    expect(badge.exists()).toBe(true);
    expect(badge.text()).toBe('3');
    wrapper.unmount();
  });

  it('бейдж корзины находится внутри иконки и позиционирован в правом верхнем углу', async () => {
    mockCartCount.value = 1;
    const wrapper = await mountNav();
    const badge = wrapper.find('.bottom-nav__badge');
    const cartIcon = wrapper.find('[data-testid="nav-Корзина"] .bottom-nav__icon');

    expect(cartIcon.exists()).toBe(true);
    expect(badge.exists()).toBe(true);
    expect(badge.element.closest('.bottom-nav__icon')).toBe(cartIcon.element);

    // JSDOM не применяет scoped-CSS, поэтому проверяем исходные стили компонента
    expect(bottomNavSource).toContain('.bottom-nav__icon {');
    expect(bottomNavSource).toContain('position: relative;');
    expect(bottomNavSource).toContain('.bottom-nav__badge {');
    expect(bottomNavSource).toContain('top: -2px;');
    expect(bottomNavSource).toContain('right: -2px;');
    wrapper.unmount();
  });
});
