import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import { ref, computed } from 'vue';
import { readFileSync } from 'node:fs';
import Header from '@/components/Header.vue';
import api from '@/services/api';

const headerSource = readFileSync('./src/components/Header.vue', 'utf-8');

const mockCartCount = ref(0);
const mockIsAuthenticated = ref(false);

vi.mock('@/composables/useAuth', () => ({
  useAuth: () => ({
    isAuthenticated: computed(() => mockIsAuthenticated.value),
    isSupplier: ref(false),
  }),
}));

vi.mock('@/composables/useCart', () => ({
  useCart: () => ({
    cartCount: computed(() => mockCartCount.value),
  }),
}));

vi.mock('@/composables/useNotifications', () => ({
  useNotifications: () => ({
    notifications: ref([]),
    unreadCount: ref(0),
  }),
}));

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
  },
}));

const router = createRouter({
  history: createWebHistory(),
  routes: [{ path: '/', component: { template: '<div>Home</div>' } }],
});

describe('Header.vue', () => {
  beforeEach(async () => {
    mockCartCount.value = 0;
    mockIsAuthenticated.value = false;
    vi.mocked(api.get).mockReset();
    await router.push('/');
    await router.isReady();
  });

  const mountHeader = async () => {
    const wrapper = mount(Header, {
      global: { plugins: [router] },
      attachTo: document.body,
    });
    await flushPromises();
    return wrapper;
  };

  it('отображает логотип', async () => {
    const wrapper = await mountHeader();
    expect(wrapper.find('[data-testid="header-logo"]').exists()).toBe(true);
    wrapper.unmount();
  });

  it('показывает блок иконок действий', async () => {
    const wrapper = await mountHeader();
    const actions = wrapper.find('.header__actions');
    expect(actions.exists()).toBe(true);
    expect(actions.isVisible()).toBe(true);
    expect(wrapper.find('[data-testid="cart-link"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="login-link"]').exists()).toBe(true);
    wrapper.unmount();
  });

  it('содержит CSS-правило для скрытия иконок на мобильном и планшете (< 1024px)', () => {
    expect(headerSource).toContain('@media (max-width: 1023px)');
    expect(headerSource).toContain('.header__actions {');
    expect(headerSource).toContain('display: none;');
  });

  it('ToastContainer рендерится вне блока иконок действий', async () => {
    const wrapper = await mountHeader();
    const toast = wrapper.find('.header__toast');
    expect(toast.exists()).toBe(true);
    expect(toast.element.closest('.header__actions')).toBeNull();
    wrapper.unmount();
  });

  it('базовый класс .header__icon задаёт контекст позиционирования для бейджей', () => {
    expect(headerSource).toContain('.header__icon {');
    expect(headerSource).toContain('position: relative;');
  });

  it('бейджи корзины и избранного находятся внутри .header__icon', async () => {
    mockCartCount.value = 2;
    mockIsAuthenticated.value = true;
    vi.mocked(api.get).mockImplementation((url) => {
      if (url === '/favorites/') return Promise.resolve({ data: [1, 2, 3, 4, 5] });
      return Promise.resolve({ data: [] });
    });
    const wrapper = await mountHeader();
    const cartBadge = wrapper.find('[data-testid="cart-link"] .header__notif-badge');
    const favBadge = wrapper.find('.header__action-item[href="/favorites"] .header__notif-badge');
    expect(cartBadge.exists()).toBe(true);
    expect(favBadge.exists()).toBe(true);
    expect(cartBadge.element.closest('.header__icon')).not.toBeNull();
    expect(favBadge.element.closest('.header__icon')).not.toBeNull();
    wrapper.unmount();
  });

  it('рендерит мобильные mobile-menu-btn и mobile-cart-link', async () => {
    const wrapper = await mountHeader();
    expect(wrapper.find('[data-testid="mobile-menu-btn"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="mobile-cart-link"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="header-search-bar-mobile"]').exists()).toBe(true);
    wrapper.unmount();
  });

  it('показывает бейдж cartCount на мобильной корзине', async () => {
    mockCartCount.value = 2;
    const wrapper = await mountHeader();
    const badge = wrapper.find('[data-testid="mobile-cart-link"] .header__notif-badge');
    expect(badge.exists()).toBe(true);
    expect(badge.text()).toBe('2');
    wrapper.unmount();
  });

  it('не показывает бейдж на мобильной корзине при cartCount = 0', async () => {
    const wrapper = await mountHeader();
    expect(wrapper.find('[data-testid="mobile-cart-link"] .header__notif-badge').exists()).toBe(false);
    wrapper.unmount();
  });

  it('открывает и закрывает drawer мобильного меню', async () => {
    const wrapper = await mountHeader();
    expect(document.body.querySelector('[data-testid="mobile-menu-drawer"]')).toBeNull();
    await wrapper.find('[data-testid="mobile-menu-btn"]').trigger('click');
    expect(document.body.querySelector('[data-testid="mobile-menu-drawer"]')).not.toBeNull();
    document.body.querySelector('.mobile-menu__overlay').click();
    await wrapper.vm.$nextTick();
    expect(document.body.querySelector('[data-testid="mobile-menu-drawer"]')).toBeNull();
    wrapper.unmount();
  });
});

describe('Header.vue (§11, D-09)', () => {
  const mountHeader = async () => {
    const wrapper = mount(Header, {
      global: { plugins: [router] },
      attachTo: document.body,
    });
    await flushPromises();
    return wrapper;
  };

  it('логотип «Пром Электрон» с иконкой', async () => {
    const wrapper = await mountHeader();
    const logo = wrapper.find('[data-testid="header-logo"]');
    expect(logo.text()).toContain('Пром');
    expect(logo.text()).toContain('Электрон');
    expect(logo.find('svg').exists()).toBe(true);
    wrapper.unmount();
  });

  it('синяя кнопка «Каталог» ведёт на /catalog', async () => {
    const wrapper = await mountHeader();
    const btn = wrapper.find('[data-testid="catalog-btn"]');
    expect(btn.exists()).toBe(true);
    expect(btn.attributes('href')).toBe('/catalog');
    wrapper.unmount();
  });

  it('телефон и часы работы — статический текст', async () => {
    const wrapper = await mountHeader();
    expect(wrapper.text()).toContain('8 (800) 500-45-85');
    expect(wrapper.text()).toContain('Ежедневно 9:00–21:00');
    wrapper.unmount();
  });

  it('«Сравнение» неактивно: aria-disabled, tooltip, не ссылка (D-09)', async () => {
    const wrapper = await mountHeader();
    const compare = wrapper.find('[data-testid="compare-link"]');
    expect(compare.exists()).toBe(true);
    expect(compare.element.tagName).not.toBe('A');
    expect(compare.attributes('aria-disabled')).toBe('true');
    expect(compare.attributes('title')).toBe('Сравнение скоро появится');
    wrapper.unmount();
  });
});
