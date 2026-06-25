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
  { id: 1, name: 'Смартфоны', description: 'Мобильные телефоны', parent_id: null, product_count: 5 },
  { id: 2, name: 'Ноутбуки', description: 'Компьютеры', parent_id: null, product_count: 3 },
  { id: 3, name: 'iPhone', description: 'Apple iPhone', parent_id: 1, product_count: 2 },
  { id: 4, name: 'Samsung', description: 'Samsung phones', parent_id: 1, product_count: 3 },
  { id: 5, name: 'MacBook', description: 'Apple MacBook', parent_id: 2, product_count: 1 },
];

const categoryListResponse = (items) => ({ items, total: items.length });

const matchCategoriesRequest = (url, params, categories = mockCategories) => {
  if (url !== '/categories/') return null;
  let items = [...categories];
  if (params?.parent_id !== undefined) {
    items = items.filter((c) => c.parent_id === Number(params.parent_id));
  }
  if (params?.q) {
    items = items.filter((c) => c.name.toLowerCase().includes(String(params.q).toLowerCase()));
  }
  if (params?.skip !== undefined && params?.limit !== undefined) {
    const skip = Number(params.skip);
    const limit = Number(params.limit);
    items = items.slice(skip, skip + limit);
  }
  return categoryListResponse(items);
};

const defaultMockGet = (url, config, categories = mockCategories) => {
  const params = config?.params;
  if (url === '/admin/dashboard') return Promise.resolve({ data: mockDashboard });
  if (url === '/admin/orders-by-day') return Promise.resolve({ data: mockOrdersByDay });
  if (url === '/admin/top-products') return Promise.resolve({ data: mockTopProducts });
  if (url === '/admin/users') return Promise.resolve({ data: mockUsers });
  if (url === '/categories/') return Promise.resolve({ data: matchCategoriesRequest(url, params, categories) });
  if (url === '/delivery-methods/') return Promise.resolve({ data: [] });
  if (url === '/admin/orders') return Promise.resolve({ data: mockOrders });
  if (url === '/admin/feature-flags') return Promise.resolve({ data: mockFeatureFlags });
  return Promise.resolve({ data: {} });
};

const mockFeatureFlags = [
  { name: 'google_oauth', enabled: true, env_default: true, redis_override: null, source: 'env' },
];

const mockOrders = [
  {
    id: 101,
    user_id: 5,
    status: 'paid',
    total_price: 29990,
    delivery_method: { name: 'CDEK' },
    tracking_number: 'TRK987654321',
    created_at: '2026-05-18T10:00:00Z',
    recipient: {
      id: 1,
      first_name: 'Иван',
      last_name: 'Иванов',
      patronymic: 'Иванович',
      phone: '+79990001122',
      country_code: 'RU',
    },
    cdek_order: {
      id: 1,
      cdek_uuid: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
      cdek_number: 'CDEK123456',
      tracking_number: 'TRK987654321',
      cdek_status: 'ACCEPTED',
      cdek_status_name: 'Принят',
      status_date_time: '2026-05-19T10:00:00Z',
      status_city: 'Москва',
      tracking_url: 'https://cdek.ru/track?number=TRK987654321',
      status_history: [
        { id: 1, cdek_status: 'CREATED', cdek_status_name: 'Создан', status_date_time: '2026-05-18T12:00:00Z', city: null },
        { id: 2, cdek_status: 'ACCEPTED', cdek_status_name: 'Принят', status_date_time: '2026-05-19T10:00:00Z', city: 'Москва' },
      ],
    },
  },
];

const switchSectionTab = async (wrapper, key) => {
  const tab = wrapper.find(`[data-testid="admin-section-tab-${key}"]`);
  expect(tab.exists()).toBe(true);
  await tab.trigger('click');
  await flushPromises();
};

describe('Admin.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    toastFn.mockClear();
    mockGet.mockImplementation(defaultMockGet);
    mockPost.mockImplementation((url) => {
      if (url === '/admin/orders/101/ship/') {
        return Promise.resolve({ data: { ...mockOrders[0], status: 'shipped' } });
      }
      return Promise.resolve({ data: {} });
    });
    mockPatch.mockImplementation((url) => {
      if (url === '/admin/feature-flags/google_oauth') {
        return Promise.resolve({ data: { name: 'google_oauth', enabled: false, source: 'redis' } });
      }
      return Promise.resolve({ data: {} });
    });
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

  it('по умолчанию активна вкладка Дашборд', async () => {
    const wrapper = mount(Admin, { global: { plugins: [router] } });
    await flushPromises();

    const dashboardTab = wrapper.find('[data-testid="admin-section-tab-dashboard"]');
    expect(dashboardTab.classes()).toContain('admin__tab--active');

    expect(wrapper.find('[data-testid="admin-section-tab-users"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="admin-section-tab-categories"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="admin-section-tab-delivery"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="admin-section-tab-orders"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="admin-section-tab-feature-flags"]').exists()).toBe(true);
  });

  it('переключает секции при клике на табы', async () => {
    const wrapper = mount(Admin, { global: { plugins: [router] } });
    await flushPromises();

    const isPanelVisible = (key) => {
      const style = wrapper.find(`[data-testid="admin-section-panel-${key}"]`).attributes('style') || '';
      return !style.includes('display: none');
    };

    expect(isPanelVisible('dashboard')).toBe(true);
    expect(isPanelVisible('users')).toBe(false);

    await switchSectionTab(wrapper, 'users');
    expect(isPanelVisible('users')).toBe(true);
    expect(isPanelVisible('dashboard')).toBe(false);

    await switchSectionTab(wrapper, 'categories');
    expect(isPanelVisible('categories')).toBe(true);
    expect(isPanelVisible('users')).toBe(false);

    await switchSectionTab(wrapper, 'delivery');
    expect(isPanelVisible('delivery')).toBe(true);

    await switchSectionTab(wrapper, 'orders');
    expect(isPanelVisible('orders')).toBe(true);

    await switchSectionTab(wrapper, 'feature-flags');
    expect(isPanelVisible('feature-flags')).toBe(true);
  });

  it('отображает список пользователей с ролями и статусами', async () => {
    const wrapper = mount(Admin, { global: { plugins: [router] } });
    await flushPromises();

    await switchSectionTab(wrapper, 'users');

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

    await switchSectionTab(wrapper, 'categories');

    const categoriesSection = wrapper.find('[data-testid="categories-section"]');
    expect(categoriesSection.text()).toContain('Категории');
    expect(categoriesSection.text()).toContain('Смартфоны');
    expect(categoriesSection.text()).toContain('Ноутбуки');
  });

  it('отображает корневые категории как вкладки', async () => {
    const wrapper = mount(Admin, { global: { plugins: [router] } });
    await flushPromises();

    await switchSectionTab(wrapper, 'categories');

    expect(wrapper.find('[data-testid="category-tab-all"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="category-tab-1"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="category-tab-2"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="category-tab-3"]').exists()).toBe(false);
  });

  it('переключает вкладку и фильтрует дочерние категории', async () => {
    const wrapper = mount(Admin, { global: { plugins: [router] } });
    await flushPromises();

    await switchSectionTab(wrapper, 'categories');

    const tab = wrapper.find('[data-testid="category-tab-1"]');
    expect(tab.exists()).toBe(true);

    await tab.trigger('click');
    await flushPromises();

    expect(wrapper.find('[data-testid="category-row-3"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="category-row-4"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="category-row-1"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="category-row-2"]').exists()).toBe(false);
  });

  it('показывает empty-state для вкладки без потомков', async () => {
    // У ноутбуков есть потомок, поэтому для теста убираем потомков у категории 2
    const emptyCategories = mockCategories.map((c) =>
      c.parent_id === 2 ? { ...c, parent_id: null } : c
    );
    mockGet.mockImplementation((url, config) =>
      defaultMockGet(url, config, emptyCategories)
    );

    const wrapper = mount(Admin, { global: { plugins: [router] } });
    await flushPromises();

    await switchSectionTab(wrapper, 'categories');

    const tab = wrapper.find('[data-testid="category-tab-2"]');
    await tab.trigger('click');
    await flushPromises();

    expect(wrapper.find('[data-testid="categories-empty"]').text()).toContain('В этой категории пока нет подкатегорий');
  });

  it('ищет категории по названию', async () => {
    vi.useFakeTimers();
    const wrapper = mount(Admin, { global: { plugins: [router] } });
    await flushPromises();

    await switchSectionTab(wrapper, 'categories');

    const searchInput = wrapper.find('[data-testid="category-search-input"]');
    await searchInput.setValue('iphone');
    vi.advanceTimersByTime(300);
    await flushPromises();

    expect(wrapper.find('[data-testid="category-row-3"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="category-row-4"]').exists()).toBe(false);
    vi.useRealTimers();
  });

  it('блокирует пользователя по клику', async () => {
    mockPatch.mockResolvedValue({
      data: { id: 2, email: 'user@example.com', full_name: 'Пользователь', role: 'user', is_active: false },
    });

    const wrapper = mount(Admin, { global: { plugins: [router] } });
    await flushPromises();

    await switchSectionTab(wrapper, 'users');

    const buttons = wrapper.findAll('[data-testid="user-row"] .admin__btn--danger');
    expect(buttons.length).toBeGreaterThan(0);

    await buttons[0].trigger('click');
    await flushPromises();

    expect(mockPatch).toHaveBeenCalledTimes(1);
    expect(mockPatch.mock.calls[0][0]).toMatch(/\/admin\/users\/\d+\/toggle-active/);
  });

  it('открывает модал создания категории', async () => {
    const wrapper = mount(Admin, { global: { plugins: [router] } });
    await flushPromises();

    await switchSectionTab(wrapper, 'categories');

    const addBtn = wrapper.find('[data-testid="add-category-btn"]');
    expect(addBtn.exists()).toBe(true);
    expect(addBtn.text()).toContain('Добавить');

    await addBtn.trigger('click');
    await flushPromises();

    expect(wrapper.text()).toContain('Новая категория');
    expect(wrapper.find('[data-testid="category-parent-select"]').exists()).toBe(true);
  });

  it('показывает селектор родителя с опциями в модалке редактирования', async () => {
    const wrapper = mount(Admin, { global: { plugins: [router] } });
    await flushPromises();

    await switchSectionTab(wrapper, 'categories');

    const editBtn = wrapper.find('[data-testid="category-row-3"] .admin__icon-btn--edit');
    await editBtn.trigger('click');
    await flushPromises();

    expect(wrapper.text()).toContain('Редактировать категорию');
    const select = wrapper.find('[data-testid="category-parent-select"]');
    expect(select.exists()).toBe(true);
    // Редактируемая категория не должна быть в опциях
    expect(select.html()).not.toContain('iPhone');
    expect(select.html()).toContain('Смартфоны');
    expect(select.html()).toContain('Без родителя');
  });

  it('отображает фичатоглы', async () => {
    const wrapper = mount(Admin, { global: { plugins: [router] } });
    await flushPromises();

    await switchSectionTab(wrapper, 'feature-flags');

    const table = wrapper.find('[data-testid="feature-flags-table"]');
    expect(table.exists()).toBe(true);
    expect(table.text()).toContain('google_oauth');
    expect(table.text()).toContain('Включён');
  });

  it('переключает фичатогл по клику', async () => {
    const wrapper = mount(Admin, { global: { plugins: [router] } });
    await flushPromises();

    await switchSectionTab(wrapper, 'feature-flags');

    const button = wrapper.find('[data-testid="feature-flag-google_oauth"]');
    expect(button.exists()).toBe(true);
    expect(button.text()).toContain('Выключить');

    await button.trigger('click');
    await flushPromises();

    expect(mockPatch).toHaveBeenCalledWith('/admin/feature-flags/google_oauth', { enabled: false });
    expect(toastFn).toHaveBeenCalledWith('Флаг "google_oauth" выключен', 'success');
  });

  it('открывает модал заказа с вкладкой CDEK', async () => {
    const wrapper = mount(Admin, { global: { plugins: [router] } });
    await flushPromises();

    await switchSectionTab(wrapper, 'orders');

    expect(wrapper.text()).toContain('TRK987654321');

    const editBtn = wrapper.find('[data-testid="orders-table"] .admin__icon-btn--edit');
    expect(editBtn.exists()).toBe(true);
    await editBtn.trigger('click');
    await flushPromises();

    expect(wrapper.text()).toContain('Заказ №101');
    expect(wrapper.find('[data-testid="order-modal-tab-order"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="order-modal-tab-cdek"]').exists()).toBe(true);

    const cdekTab = wrapper.find('[data-testid="order-modal-tab-cdek"]');
    await cdekTab.trigger('click');
    await flushPromises();

    const cdekPanel = wrapper.find('[data-testid="order-modal-cdek-tab"]');
    expect(cdekPanel.exists()).toBe(true);
    expect(cdekPanel.text()).toContain('f47ac10b-58cc-4372-a567-0e02b2c3d479');
    expect(cdekPanel.text()).toContain('CDEK123456');
    expect(cdekPanel.text()).toContain('TRK987654321');
    expect(cdekPanel.text()).toContain('ACCEPTED');
    expect(cdekPanel.text()).toContain('Москва');
    expect(cdekPanel.text()).toContain('Принят');
    expect(cdekPanel.text()).toContain('Создан');

    const trackingLink = wrapper.find('[data-testid="order-modal-cdek-tracking-link"]');
    expect(trackingLink.exists()).toBe(true);
    expect(trackingLink.attributes('href')).toBe(mockOrders[0].cdek_order.tracking_url);
  });

  it('показывает кнопку «Подтвердить отправку» для paid заказа', async () => {
    const wrapper = mount(Admin, { global: { plugins: [router] } });
    await flushPromises();

    await switchSectionTab(wrapper, 'orders');

    const shipBtn = wrapper.find('[data-testid="admin-order-ship-btn-101"]');
    expect(shipBtn.exists()).toBe(true);
    expect(shipBtn.text()).toContain('Подтвердить отправку');
  });

  it('не показывает кнопку «Подтвердить отправку» для других статусов', async () => {
    const mixedOrders = [
      { ...mockOrders[0], id: 201, status: 'pending' },
      { ...mockOrders[0], id: 202, status: 'shipped' },
      { ...mockOrders[0], id: 203, status: 'delivered' },
      { ...mockOrders[0], id: 204, status: 'cancelled' },
    ];
    mockGet.mockImplementation((url, config) => {
      if (url === '/admin/orders') return Promise.resolve({ data: mixedOrders });
      return defaultMockGet(url, config);
    });

    const wrapper = mount(Admin, { global: { plugins: [router] } });
    await flushPromises();

    await switchSectionTab(wrapper, 'orders');

    expect(wrapper.find('[data-testid="admin-order-ship-btn-201"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="admin-order-ship-btn-202"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="admin-order-ship-btn-203"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="admin-order-ship-btn-204"]').exists()).toBe(false);
  });

  it('подтверждает отправку paid заказа по клику', async () => {
    const wrapper = mount(Admin, { global: { plugins: [router] } });
    await flushPromises();

    await switchSectionTab(wrapper, 'orders');

    const shipBtn = wrapper.find('[data-testid="admin-order-ship-btn-101"]');
    expect(shipBtn.exists()).toBe(true);

    await shipBtn.trigger('click');
    await flushPromises();

    expect(mockPost).toHaveBeenCalledTimes(1);
    expect(mockPost).toHaveBeenCalledWith('/admin/orders/101/ship/');
    expect(toastFn).toHaveBeenCalledWith('Заказ отправлен', 'success');
  });

  it('отображает данные получателя в модалке заказа', async () => {
    const wrapper = mount(Admin, { global: { plugins: [router] } });
    await flushPromises();

    await switchSectionTab(wrapper, 'orders');

    const editBtn = wrapper.find('[data-testid="orders-table"] .admin__icon-btn--edit');
    expect(editBtn.exists()).toBe(true);
    await editBtn.trigger('click');
    await flushPromises();

    const recipientBlock = wrapper.find('[data-testid="order-modal-recipient"]');
    expect(recipientBlock.exists()).toBe(true);
    expect(wrapper.find('[data-testid="order-modal-recipient-name"]').text()).toContain('Иванов');
    expect(wrapper.find('[data-testid="order-modal-recipient-name"]').text()).toContain('Иванович');
    expect(wrapper.find('[data-testid="order-modal-recipient-phone"]').text()).toBe('+79990001122');
  });
});
