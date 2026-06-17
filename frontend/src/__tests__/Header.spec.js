import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import { ref, computed } from 'vue';
import { readFileSync } from 'node:fs';
import Header from '@/components/Header.vue';

const headerSource = readFileSync('./src/components/Header.vue', 'utf-8');

const mockCartCount = ref(0);

vi.mock('@/composables/useAuth', () => ({
  useAuth: () => ({
    isAuthenticated: ref(false),
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

  it('содержит CSS-правило для скрытия иконок на мобильном (< 768px)', () => {
    expect(headerSource).toContain('@media (max-width: 767px)');
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
});
