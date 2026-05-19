import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import Notifications from '../views/Notifications.vue';

const mockGet = vi.fn();
const mockPatch = vi.fn();
const mockDelete = vi.fn();

vi.mock('@/services/api', () => ({
  default: {
    get: (...args) => mockGet(...args),
    patch: (...args) => mockPatch(...args),
    delete: (...args) => mockDelete(...args),
  },
}));

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: { template: '<div>Home</div>' } },
    { path: '/orders/:id', component: { template: '<div>Order</div>' } },
    { path: '/notifications', component: Notifications },
  ],
});

const mockNotifications = [
  { id: 1, type: 'order_created', title: 'Заказ оформлен', message: 'Заказ №42 создан', order_id: 42, is_read: false, created_at: '2026-05-18T10:00:00Z' },
  { id: 2, type: 'order_paid', title: 'Заказ оплачен', message: 'Заказ №42 оплачен', order_id: 42, is_read: true, created_at: '2026-05-18T11:00:00Z' },
];

describe('Notifications.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockImplementation((url) => {
      if (url === '/notifications/') return Promise.resolve({ data: { items: mockNotifications, unread_count: 1 } });
      return Promise.resolve({ data: {} });
    });
    mockPatch.mockResolvedValue({ data: {} });
    mockDelete.mockResolvedValue({ data: {} });
  });

  const mountComponent = async () => {
    await router.push('/notifications');
    await router.isReady();
    const wrapper = mount(Notifications, { global: { plugins: [router] } });
    await flushPromises();
    return wrapper;
  };

  it('отображает страницу уведомлений', async () => {
    const wrapper = await mountComponent();
    expect(wrapper.find('[data-testid="notifications-page"]').exists()).toBe(true);
    expect(wrapper.text()).toContain('Уведомления');
  });

  it('показывает список уведомлений', async () => {
    const wrapper = await mountComponent();
    expect(wrapper.text()).toContain('Заказ оформлен');
    expect(wrapper.text()).toContain('Заказ оплачен');
    expect(wrapper.text()).toContain('Заказ №42 создан');
  });

  it('показывает пустое состояние', async () => {
    mockGet.mockImplementation((url) => {
      if (url === '/notifications/') return Promise.resolve({ data: { items: [], unread_count: 0 } });
      return Promise.resolve({ data: {} });
    });
    const wrapper = await mountComponent();
    expect(wrapper.text()).toContain('У вас пока нет уведомлений');
  });

  it('прочитать все', async () => {
    const wrapper = await mountComponent();
    const btn = wrapper.find('.notifications-page__read-all');
    expect(btn.exists()).toBe(true);
    await btn.trigger('click');
    await flushPromises();
    expect(mockPatch).toHaveBeenCalledWith('/notifications/read-all');
  });

  it('удаляет уведомление', async () => {
    const wrapper = await mountComponent();
    const deleteBtns = wrapper.findAll('.notification-item__delete');
    expect(deleteBtns.length).toBe(2);
    await deleteBtns[0].trigger('click');
    await flushPromises();
    expect(mockDelete).toHaveBeenCalledWith('/notifications/1');
  });
});
