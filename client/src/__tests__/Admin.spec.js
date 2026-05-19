import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import Admin from '../views/Admin.vue';

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPut = vi.fn();
const mockDelete = vi.fn();
const mockPatch = vi.fn();

vi.mock('@/services/api', () => ({
  default: {
    get: (...args) => mockGet(...args),
    post: (...args) => mockPost(...args),
    put: (...args) => mockPut(...args),
    delete: (...args) => mockDelete(...args),
    patch: (...args) => mockPatch(...args),
  },
}));

const toastFn = vi.fn();
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ add: toastFn }),
}));

vi.mock('@/components/SkeletonAdminTable.vue', () => ({
  default: {
    name: 'SkeletonAdminTable',
    template: '<div data-testid="skeleton-admin-table">Loading...</div>',
  },
}));

const router = createRouter({
  history: createWebHistory(),
  routes: [{ path: '/', component: { template: '<div>Home</div>' } }],
});

const mockDashboard = {
  total_orders: 42,
  total_revenue: 125000,
  total_users: 15,
  total_products: 8,
};

const mockOrdersByDay = [
  { date: '2026-05-07', orders: 3, revenue: 15000 },
  { date: '2026-05-08', orders: 5, revenue: 25000 },
  { date: '2026-05-09', orders: 2, revenue: 8000 },
  { date: '2026-05-10', orders: 8, revenue: 40000 },
  { date: '2026-05-11', orders: 4, revenue: 18000 },
  { date: '2026-05-12', orders: 6, revenue: 30000 },
  { date: '2026-05-13', orders: 7, revenue: 35000 },
];

const mockTopProducts = [
  { id: 1, name: 'Смартфон Pro', sold: 12, revenue: 359880 },
  { id: 2, name: 'Наушники', sold: 8, revenue: 39920 },
];

const mockUsers = [
  { id: 1, email: 'admin@example.com', full_name: 'Админ', role: 'admin', is_active: true, created_at: '2026-01-01T00:00:00Z' },
  { id: 2, email: 'user@example.com', full_name: 'Пользователь', role: 'user', is_active: true, created_at: '2026-02-01T00:00:00Z' },
  { id: 3, email: 'blocked@example.com', full_name: 'Заблокированный', role: 'user', is_active: false, created_at: '2026-03-01T00:00:00Z' },
];

const mockCategories = [
  { id: 1, name: 'Смартфоны', description: 'Мобильные телефоны' },
  { id: 2, name: 'Ноутбуки', description: 'Компьютеры' },
];

describe('Admin.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    toastFn.mockClear();
    mockGet.mockImplementation((url) => {
      if (url === '/admin/dashboard') return Promise.resolve({ data: mockDashboard });
      if (url === '/admin/orders-by-day') return Promise.resolve({ data: mockOrdersByDay });
      if (url === '/admin/top-products') return Promise.resolve({ data: mockTopProducts });
      if (url === '/admin/users') return Promise.resolve({ data: mockUsers });
      if (url === '/categories') return Promise.resolve({ data: mockCategories });
      return Promise.resolve({ data: {} });
    });
    mockPatch.mockResolvedValue({ data: {} });
    mockDelete.mockResolvedValue({ data: {} });
  });

  it('отображает страницу админа', async () => {
    const wrapper = mount(Admin, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.find('[data-testid="admin-page"]').exists()).toBe(true);
    expect(wrapper.text()).toContain('Панель администратора');
  });

  it('отображает KPI карточки', async () => {
    const wrapper = mount(Admin, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.text()).toContain('Всего заказов');
    expect(wrapper.text()).toContain('42');
    expect(wrapper.text()).toContain('Выручка');
    expect(wrapper.text()).toContain('Пользователей');
    expect(wrapper.text()).toContain('15');
    expect(wrapper.text()).toContain('Товаров');
    expect(wrapper.text()).toContain('8');
  });

  it('отображает график заказов', async () => {
    const wrapper = mount(Admin, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.text()).toContain('Заказы за 7 дней');
    const bars = wrapper.findAll('.admin__chart-bar-wrap');
    expect(bars.length).toBe(7);
  });

  it('отображает топ товаров', async () => {
    const wrapper = mount(Admin, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.text()).toContain('Топ товаров');
    expect(wrapper.text()).toContain('Смартфон Pro');
    expect(wrapper.text()).toContain('Наушники');
    expect(wrapper.text()).toContain('12 продано');
  });

  it('отображает список пользователей с ролями и статусами', async () => {
    Object.defineProperty(window, 'innerWidth', { writable: true, configurable: true, value: 1024 });

    const wrapper = mount(Admin, { global: { plugins: [router] } });
    await flushPromises();

    // Переключаемся на вкладку пользователей
    await wrapper.find('.admin__tab--active').exists(); // на десктопе табов нет, всё видно

    expect(wrapper.text()).toContain('Пользователи');
    expect(wrapper.text()).toContain('admin@example.com');
    expect(wrapper.text()).toContain('user@example.com');
    expect(wrapper.text()).toContain('Админ');
    expect(wrapper.text()).toContain('Покупатель');
    expect(wrapper.text()).toContain('Активен');
    expect(wrapper.text()).toContain('Заблокирован');
  });

  it('отображает категории', async () => {
    const wrapper = mount(Admin, { global: { plugins: [router] } });
    await flushPromises();

    expect(wrapper.text()).toContain('Категории');
    expect(wrapper.text()).toContain('Смартфоны');
    expect(wrapper.text()).toContain('Ноутбуки');
  });

  it('блокирует пользователя по клику', async () => {
    mockPatch.mockResolvedValue({
      data: { id: 2, email: 'user@example.com', full_name: 'Пользователь', role: 'user', is_active: false },
    });

    const wrapper = mount(Admin, { global: { plugins: [router] } });
    await flushPromises();

    const buttons = wrapper.findAll('.admin__btn--danger');
    expect(buttons.length).toBeGreaterThan(0);

    await buttons[0].trigger('click');
    await flushPromises();

    expect(mockPatch).toHaveBeenCalledTimes(1);
    expect(mockPatch.mock.calls[0][0]).toMatch(/\/admin\/users\/\d+\/toggle-active/);
  });

  it('открывает модал создания категории', async () => {
    const wrapper = mount(Admin, { global: { plugins: [router] } });
    await flushPromises();

    const addBtn = wrapper.find('.admin__btn--primary');
    expect(addBtn.exists()).toBe(true);
    expect(addBtn.text()).toContain('Добавить');

    await addBtn.trigger('click');
    await flushPromises();

    expect(wrapper.text()).toContain('Новая категория');
  });
});
