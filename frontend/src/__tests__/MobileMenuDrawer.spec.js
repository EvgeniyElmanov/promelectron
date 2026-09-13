import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import { ref, computed } from 'vue';
import MobileMenuDrawer from '@/components/MobileMenuDrawer.vue';

const mockIsAuthenticated = ref(false);
const mockIsSupplier = ref(false);

vi.mock('@/composables/useAuth', () => ({
  useAuth: () => ({
    isAuthenticated: computed(() => mockIsAuthenticated.value),
    isSupplier: computed(() => mockIsSupplier.value),
  }),
}));

const router = createRouter({
  history: createWebHistory(),
  routes: [{ path: '/', component: { template: '<div>Home</div>' } }],
});

const mountDrawer = async (open = true) => {
  await router.push('/');
  await router.isReady();
  return mount(MobileMenuDrawer, {
    props: { open },
    global: { plugins: [router], stubs: { teleport: true } },
    attachTo: document.body,
  });
};

describe('MobileMenuDrawer.vue', () => {
  beforeEach(() => {
    mockIsAuthenticated.value = false;
    mockIsSupplier.value = false;
  });

  it('не рендерится при open=false', async () => {
    const wrapper = await mountDrawer(false);
    expect(wrapper.find('[data-testid="mobile-menu-drawer"]').exists()).toBe(false);
    wrapper.unmount();
  });

  it('гостю показывает Каталог и Войти, скрывает auth-пункты', async () => {
    const wrapper = await mountDrawer();
    const drawer = wrapper.find('[data-testid="mobile-menu-drawer"]');
    expect(drawer.exists()).toBe(true);
    const links = drawer.findAll('a');
    const hrefs = links.map((l) => l.attributes('href'));
    expect(hrefs).toContain('/');
    expect(hrefs).toContain('/login');
    expect(hrefs).not.toContain('/orders');
    expect(hrefs).not.toContain('/profile');
    wrapper.unmount();
  });

  it('авторизованному показывает Заказы, Уведомления, Профиль', async () => {
    mockIsAuthenticated.value = true;
    const wrapper = await mountDrawer();
    const hrefs = wrapper.findAll('a').map((l) => l.attributes('href'));
    expect(hrefs).toContain('/orders');
    expect(hrefs).toContain('/notifications');
    expect(hrefs).toContain('/profile');
    expect(hrefs).not.toContain('/login');
    wrapper.unmount();
  });

  it('поставщику показывает supplier-пункты', async () => {
    mockIsAuthenticated.value = true;
    mockIsSupplier.value = true;
    const wrapper = await mountDrawer();
    const hrefs = wrapper.findAll('a').map((l) => l.attributes('href'));
    expect(hrefs).toContain('/supplier-dashboard');
    expect(hrefs).toContain('/my-products');
    expect(hrefs).toContain('/supplier-orders');
    wrapper.unmount();
  });

  it('эмитит close по Escape', async () => {
    const wrapper = await mountDrawer();
    await wrapper.find('.mobile-menu__drawer').trigger('keydown.esc');
    expect(wrapper.emitted('close')).toHaveLength(1);
    wrapper.unmount();
  });

  it('эмитит close по клику на overlay', async () => {
    const wrapper = await mountDrawer();
    await wrapper.find('.mobile-menu__overlay').trigger('click');
    expect(wrapper.emitted('close')).toHaveLength(1);
    wrapper.unmount();
  });

  it('эмитит close по выбору пункта меню', async () => {
    const wrapper = await mountDrawer();
    await wrapper.find('a[href="/"]').trigger('click');
    expect(wrapper.emitted('close')).toHaveLength(1);
    wrapper.unmount();
  });
});
