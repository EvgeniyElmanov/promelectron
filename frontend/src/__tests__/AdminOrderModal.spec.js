import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import AdminOrderModal from '../components/admin/AdminOrderModal.vue';

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPut = vi.fn();

vi.mock('@/services/api', () => ({
  default: {
    get: (...args) => mockGet(...args),
    post: (...args) => mockPost(...args),
    put: (...args) => mockPut(...args),
  },
}));

const toastFn = vi.fn();
vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ add: toastFn }),
}));

const buildDetail = (overrides = {}) => ({
  id: 101,
  user_id: 2,
  status: 'paid',
  total_price: '1298.00',
  items_total: '998.00',
  delivery_price: '300.00',
  shipping_address: 'г. Москва, ул. Ленина, д. 1',
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
  items: [
    {
      id: 1,
      product_id: 10,
      product_name: 'Кабель USB-C',
      sku: 'CBL-001',
      image_url: 'https://img.example.com/cable.jpg',
      quantity: 2,
      price_at_time: '499.00',
      line_total: '998.00',
    },
    {
      id: 2,
      product_id: 11,
      product_name: 'Адаптер',
      sku: null,
      image_url: null,
      quantity: 1,
      price_at_time: '0.00',
      line_total: '0.00',
    },
  ],
  buyer: { name: 'Иван Иванов', email: 'ivan@example.com', phone: '+79990001122' },
  payment: {
    id: 5,
    status: 'succeeded',
    yookassa_payment_id: 'yk-123',
    paid_at: '2026-05-18T11:00:00Z',
    amount: '1298.00',
  },
  cdek_order: {
    id: 1,
    cdek_uuid: 'f47ac10b-58cc-4372-a567-0e02b2c3d479',
    cdek_number: 'CDEK123456',
    tracking_number: 'TRK987654321',
    cdek_status: 'ACCEPTED',
    status_date_time: '2026-05-19T10:00:00Z',
    status_city: 'Москва',
    tracking_url: 'https://cdek.ru/track?number=TRK987654321',
    status_history: [
      { id: 1, cdek_status: 'CREATED', cdek_status_name: 'Создан', status_date_time: '2026-05-18T12:00:00Z', city: null },
      { id: 2, cdek_status: 'ACCEPTED', cdek_status_name: 'Принят', status_date_time: '2026-05-19T10:00:00Z', city: 'Москва' },
    ],
  },
  ...overrides,
});

let detailResponse = buildDetail();

const mountModal = (props = {}) =>
  mount(AdminOrderModal, {
    props: { visible: true, orderId: 101, ...props },
  });

describe('AdminOrderModal.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    toastFn.mockClear();
    window.confirm = vi.fn();
    detailResponse = buildDetail();
    mockGet.mockImplementation((url) => {
      if (url === '/admin/orders/101/') return Promise.resolve({ data: detailResponse });
      return Promise.resolve({ data: {} });
    });
    mockPost.mockResolvedValue({ data: {} });
    mockPut.mockResolvedValue({ data: {} });
  });

  it('загружает детали заказа и показывает шапку', async () => {
    const wrapper = mountModal();
    await flushPromises();

    expect(mockGet).toHaveBeenCalledWith('/admin/orders/101/');
    expect(wrapper.text()).toContain('Заказ №101');
    expect(wrapper.text()).toContain('Оплачен');
    expect(wrapper.find('[data-testid="order-modal-delivery-method"]').text()).toBe('CDEK');
  });

  it('показывает состав заказа с миниатюрами и итогами', async () => {
    const wrapper = mountModal();
    await flushPromises();

    const items = wrapper.find('[data-testid="order-modal-items"]');
    expect(items.text()).toContain('Кабель USB-C');
    expect(items.text()).toContain('CBL-001');
    expect(items.text()).toContain('Адаптер');

    const thumb = wrapper.find('[data-testid="order-modal-item-thumb-1"] img');
    expect(thumb.exists()).toBe(true);
    expect(thumb.attributes('src')).toBe('https://img.example.com/cable.jpg');

    // Позиция без фото — placeholder
    expect(wrapper.find('[data-testid="order-modal-item-thumb-2"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="order-modal-item-2"] .order-modal__item-thumb--placeholder').exists()).toBe(true);

    expect(wrapper.find('[data-testid="order-modal-items-total"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="order-modal-delivery-price"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="order-modal-total-price"]').exists()).toBe(true);
    // Скидки нет — строки не должно быть
    expect(wrapper.find('[data-testid="order-modal-discount-row"]').exists()).toBe(false);
  });

  it('показывает строку скидки, если суммы не сходятся', async () => {
    detailResponse = buildDetail({ total_price: '898.00' });
    const wrapper = mountModal();
    await flushPromises();

    expect(wrapper.find('[data-testid="order-modal-discount-row"]').exists()).toBe(true);
  });

  it('открывает и закрывает лайтбокс по клику', async () => {
    const wrapper = mountModal();
    await flushPromises();

    expect(wrapper.find('[data-testid="order-image-lightbox"]').exists()).toBe(false);

    await wrapper.find('[data-testid="order-modal-item-thumb-1"]').trigger('click');
    expect(wrapper.find('[data-testid="order-image-lightbox"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="order-image-lightbox"] img').attributes('src')).toBe('https://img.example.com/cable.jpg');

    await wrapper.find('[data-testid="order-image-lightbox"]').trigger('click');
    expect(wrapper.find('[data-testid="order-image-lightbox"]').exists()).toBe(false);
  });

  it('закрывает лайтбокс по Escape', async () => {
    const wrapper = mountModal();
    await flushPromises();

    await wrapper.find('[data-testid="order-modal-item-thumb-1"]').trigger('click');
    expect(wrapper.find('[data-testid="order-image-lightbox"]').exists()).toBe(true);

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    await wrapper.vm.$nextTick();
    expect(wrapper.find('[data-testid="order-image-lightbox"]').exists()).toBe(false);
  });

  it('показывает данные покупателя', async () => {
    const wrapper = mountModal();
    await flushPromises();

    expect(wrapper.find('[data-testid="order-modal-buyer-name"]').text()).toBe('Иван Иванов');
    expect(wrapper.find('[data-testid="order-modal-buyer-email"]').text()).toBe('ivan@example.com');
    expect(wrapper.find('[data-testid="order-modal-buyer-phone"]').text()).toBe('+79990001122');
  });

  it('показывает гостевые данные покупателя без ошибок', async () => {
    detailResponse = buildDetail({
      user_id: null,
      buyer: { name: 'Гост Гостев', email: 'guest@example.com', phone: '+79998887766' },
    });
    const wrapper = mountModal();
    await flushPromises();

    expect(wrapper.find('[data-testid="order-modal-buyer-name"]').text()).toBe('Гост Гостев');
    expect(wrapper.find('[data-testid="order-modal-buyer-email"]').text()).toBe('guest@example.com');
  });

  it('показывает получателя и адрес доставки', async () => {
    const wrapper = mountModal();
    await flushPromises();

    expect(wrapper.find('[data-testid="order-modal-recipient-name"]').text()).toBe('Иванов Иван Иванович');
    expect(wrapper.find('[data-testid="order-modal-recipient-phone"]').text()).toBe('+79990001122');
    expect(wrapper.find('[data-testid="order-modal-shipping-address"]').text()).toBe('г. Москва, ул. Ленина, д. 1');
  });

  it('показывает способ и статус оплаты', async () => {
    const wrapper = mountModal();
    await flushPromises();

    expect(wrapper.find('[data-testid="order-modal-payment-method"]').text()).toBe('ЮKassa');
    expect(wrapper.find('[data-testid="order-modal-payment-status"]').text()).toBe('succeeded');
    expect(wrapper.find('[data-testid="order-modal-payment-paid-at"]').exists()).toBe(true);
  });

  it('показывает «—» в оплате при отсутствии платежа', async () => {
    detailResponse = buildDetail({ payment: null });
    const wrapper = mountModal();
    await flushPromises();

    expect(wrapper.find('[data-testid="order-modal-payment-method"]').text()).toBe('—');
    expect(wrapper.find('[data-testid="order-modal-payment-status"]').exists()).toBe(false);
  });

  it('кнопка «Подтвердить отправку» видна только для paid', async () => {
    detailResponse = buildDetail({ status: 'pending' });
    const wrapper = mountModal();
    await flushPromises();

    expect(wrapper.find('[data-testid="admin-order-ship-btn-101"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="admin-order-cancel-btn-101"]').exists()).toBe(true);
  });

  it('кнопки ship/cancel скрыты для shipped/delivered/cancelled', async () => {
    for (const status of ['shipped', 'delivered', 'cancelled']) {
      detailResponse = buildDetail({ status });
      const wrapper = mountModal();
      await flushPromises();

      expect(wrapper.find('[data-testid="admin-order-ship-btn-101"]').exists()).toBe(false);
      expect(wrapper.find('[data-testid="admin-order-cancel-btn-101"]').exists()).toBe(false);
      wrapper.unmount();
    }
  });

  it('для cancelled заказа селект статуса disabled', async () => {
    detailResponse = buildDetail({ status: 'cancelled' });
    const wrapper = mountModal();
    await flushPromises();

    const select = wrapper.find('[data-testid="order-modal-status-select"]');
    expect(select.attributes('disabled')).toBeDefined();
    expect(select.element.value).toBe('cancelled');
  });

  it('ship: отправляет запрос, обновляет детали и эмитит updated, модалка открыта', async () => {
    const wrapper = mountModal();
    await flushPromises();

    const getCallsBefore = mockGet.mock.calls.filter(([url]) => url === '/admin/orders/101/').length;

    await wrapper.find('[data-testid="admin-order-ship-btn-101"]').trigger('click');
    await flushPromises();

    expect(mockPost).toHaveBeenCalledWith('/admin/orders/101/ship/');
    expect(toastFn).toHaveBeenCalledWith('Заказ отправлен', 'success');
    expect(wrapper.emitted('updated')).toBeTruthy();
    expect(wrapper.emitted('update:visible')).toBeFalsy();

    const getCallsAfter = mockGet.mock.calls.filter(([url]) => url === '/admin/orders/101/').length;
    expect(getCallsAfter).toBe(getCallsBefore + 1);
  });

  it('cancel: confirm, запрос, updated и закрытие модалки', async () => {
    window.confirm.mockReturnValue(true);
    const wrapper = mountModal();
    await flushPromises();

    await wrapper.find('[data-testid="admin-order-cancel-btn-101"]').trigger('click');
    await flushPromises();

    expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining('возвращены'));
    expect(mockPost).toHaveBeenCalledWith('/admin/orders/101/cancel/');
    expect(toastFn).toHaveBeenCalledWith('Заказ отменён', 'success');
    expect(wrapper.emitted('updated')).toBeTruthy();
    expect(wrapper.emitted('update:visible')[0]).toEqual([false]);
  });

  it('cancel: для pending заказа confirm без предупреждения о возврате', async () => {
    window.confirm.mockReturnValue(true);
    detailResponse = buildDetail({ status: 'pending' });
    const wrapper = mountModal();
    await flushPromises();

    await wrapper.find('[data-testid="admin-order-cancel-btn-101"]').trigger('click');
    await flushPromises();

    expect(window.confirm).toHaveBeenCalledWith('Отменить заказ?');
    expect(mockPost).toHaveBeenCalledWith('/admin/orders/101/cancel/');
  });

  it('cancel: при отказе в confirm запрос не уходит', async () => {
    window.confirm.mockReturnValue(false);
    const wrapper = mountModal();
    await flushPromises();

    await wrapper.find('[data-testid="admin-order-cancel-btn-101"]').trigger('click');
    await flushPromises();

    expect(mockPost).not.toHaveBeenCalled();
    expect(wrapper.emitted('updated')).toBeFalsy();
  });

  it('save: PUT без trailing slash, обновление деталей, updated, модалка открыта', async () => {
    const wrapper = mountModal();
    await flushPromises();

    await wrapper.find('[data-testid="order-modal-status-select"]').setValue('shipped');
    await wrapper.find('form.modal__form').trigger('submit');
    await flushPromises();

    expect(mockPut).toHaveBeenCalledWith('/admin/orders/101', { status: 'shipped', tracking_number: 'TRK987654321' });
    expect(toastFn).toHaveBeenCalledWith('Заказ обновлён', 'success');
    expect(wrapper.emitted('updated')).toBeTruthy();
    expect(wrapper.emitted('update:visible')).toBeFalsy();
  });

  it('показывает вкладку CDEK с историей статусов и ссылкой', async () => {
    const wrapper = mountModal();
    await flushPromises();

    await wrapper.find('[data-testid="order-modal-tab-cdek"]').trigger('click');
    await flushPromises();

    const panel = wrapper.find('[data-testid="order-modal-cdek-tab"]');
    expect(panel.text()).toContain('f47ac10b-58cc-4372-a567-0e02b2c3d479');
    expect(panel.text()).toContain('CDEK123456');
    expect(panel.text()).toContain('ACCEPTED');
    expect(panel.text()).toContain('Принят');
    expect(panel.text()).toContain('Создан');

    const link = wrapper.find('[data-testid="order-modal-cdek-tracking-link"]');
    expect(link.attributes('href')).toBe('https://cdek.ru/track?number=TRK987654321');
  });

  it('скрывает вкладку CDEK и показывает «—» в доставке без cdek_order', async () => {
    detailResponse = buildDetail({ cdek_order: null });
    const wrapper = mountModal();
    await flushPromises();

    expect(wrapper.find('[data-testid="order-modal-tab-cdek"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="order-modal-delivery-method"]').text()).toBe('—');
  });

  it('показывает ошибку при неудачной загрузке деталей', async () => {
    mockGet.mockRejectedValue({ response: { data: { detail: 'Not found' } } });
    const wrapper = mountModal();
    await flushPromises();

    expect(wrapper.find('[data-testid="order-modal-error"]').text()).toBe('Not found');
  });
});
