import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useOrderSubmission, buildCalculateItems } from '@/composables/useOrderSubmission';

const mockCalculateDelivery = vi.hoisted(() => vi.fn());
const mockToast = vi.hoisted(() => vi.fn());

vi.mock('@/api/cdek', () => ({
  calculateDelivery: mockCalculateDelivery,
}));

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ add: mockToast }),
}));

const makeError = (status, detail = 'Ошибка') => ({
  response: { status, data: { detail } },
});

const selectedDelivery = {
  tariff_code: 136,
  tariff_name: 'Посылка склад-склад',
  delivery_mode: 'PVZ',
  delivery_point: 'MSK123',
  to_location: null,
  price: 350,
  period_min: 2,
  period_max: 4,
  shipping_address: 'ПВЗ MSK123, Тестовая, 1',
};

const items = [
  { product_id: 1, quantity: 2, weight_grams: 500, length_cm: 20, width_cm: 15, height_cm: 5 },
  { product_id: 2, quantity: 1 },
];

const makeContext = (onDeliveryChange = vi.fn()) => ({
  items,
  supplierId: 1,
  selectedDelivery: { ...selectedDelivery },
  onDeliveryChange,
});

describe('buildCalculateItems', () => {
  it('собирает items в форме серверного пересчёта (с реальным quantity)', () => {
    expect(buildCalculateItems(items)).toEqual([
      { weight_grams: 500, quantity: 2, length_cm: 20, width_cm: 15, height_cm: 5 },
      { weight_grams: 1000, quantity: 1, length_cm: 10, width_cm: 10, height_cm: 10 },
    ]);
  });

  it('читает габариты из вложенного product', () => {
    const withProduct = [{ quantity: 3, product: { weight_grams: 250 } }];
    expect(buildCalculateItems(withProduct)).toEqual([
      { weight_grams: 250, quantity: 3, length_cm: 10, width_cm: 10, height_cm: 10 },
    ]);
  });
});

describe('useOrderSubmission.handleOrderCreateError', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('409: пересчитывает тариф, обновляет доставку и показывает notice со старой и новой ценой', async () => {
    mockCalculateDelivery.mockResolvedValue({
      tariffs: [
        { tariff_code: 137, tariff_name: 'Другой', price: 999 },
        { tariff_code: 136, tariff_name: 'Посылка склад-склад', price: 420, period_min: 3, period_max: 5 },
      ],
    });
    const onDeliveryChange = vi.fn();
    const { deliveryNotice, handleOrderCreateError } = useOrderSubmission();

    const handled = await handleOrderCreateError(
      makeError(409, 'Стоимость доставки устарела. Пересчитайте доставку и повторите заказ.'),
      makeContext(onDeliveryChange),
    );

    expect(handled).toBe(true);
    expect(mockCalculateDelivery).toHaveBeenCalledWith({
      items: buildCalculateItems(items),
      supplier_id: 1,
      to_location: undefined,
      delivery_point: 'MSK123',
    });
    expect(onDeliveryChange).toHaveBeenCalledWith(expect.objectContaining({
      tariff_code: 136,
      price: 420,
      period_min: 3,
      period_max: 5,
    }));
    expect(deliveryNotice.value).toEqual({ type: 'price-update', oldPrice: 350, newPrice: 420 });
    expect(mockToast).toHaveBeenCalledWith(
      expect.stringContaining('350'),
      'info',
      expect.any(Number),
    );
  });

  it('409 без доступного тарифа: сбрасывает доставку и просит перевыбрать', async () => {
    mockCalculateDelivery.mockResolvedValue({ tariffs: [{ tariff_code: 137, price: 999 }] });
    const onDeliveryChange = vi.fn();
    const { deliveryNotice, handleOrderCreateError } = useOrderSubmission();

    const handled = await handleOrderCreateError(makeError(409), makeContext(onDeliveryChange));

    expect(handled).toBe(true);
    expect(onDeliveryChange).toHaveBeenCalledWith(null);
    expect(deliveryNotice.value).toBeNull();
    expect(mockToast).toHaveBeenCalledWith(
      expect.stringContaining('Перевыберите доставку'),
      'error',
      expect.any(Number),
    );
  });

  it('409 при падении пересчёта: показывает исходный detail, notice не появляется', async () => {
    mockCalculateDelivery.mockRejectedValue(new Error('network'));
    const onDeliveryChange = vi.fn();
    const { deliveryNotice, handleOrderCreateError } = useOrderSubmission();

    const handled = await handleOrderCreateError(
      makeError(409, 'Стоимость доставки устарела.'),
      makeContext(onDeliveryChange),
    );

    expect(handled).toBe(true);
    expect(onDeliveryChange).not.toHaveBeenCalled();
    expect(deliveryNotice.value).toBeNull();
    expect(mockToast).toHaveBeenCalledWith('Стоимость доставки устарела.', 'error', expect.any(Number));
  });

  it('503: дружелюбное сообщение о недоступности, пересчёт не вызывается', async () => {
    const onDeliveryChange = vi.fn();
    const { deliveryNotice, handleOrderCreateError } = useOrderSubmission();

    const handled = await handleOrderCreateError(makeError(503), makeContext(onDeliveryChange));

    expect(handled).toBe(true);
    expect(mockCalculateDelivery).not.toHaveBeenCalled();
    expect(onDeliveryChange).not.toHaveBeenCalled();
    expect(deliveryNotice.value).toEqual({ type: 'unavailable' });
    expect(mockToast).toHaveBeenCalledWith(
      expect.stringContaining('временно недоступен'),
      'error',
      expect.any(Number),
    );
  });

  it('прочие статусы (422/500): не обрабатываются, поведение вызывающего кода не меняется', async () => {
    const { deliveryNotice, handleOrderCreateError } = useOrderSubmission();

    for (const status of [422, 500, 400]) {
      const handled = await handleOrderCreateError(makeError(status), makeContext());
      expect(handled).toBe(false);
    }
    expect(mockCalculateDelivery).not.toHaveBeenCalled();
    expect(mockToast).not.toHaveBeenCalled();
    expect(deliveryNotice.value).toBeNull();
  });

  it('dismissDeliveryNotice скрывает notice', async () => {
    const { deliveryNotice, dismissDeliveryNotice, handleOrderCreateError } = useOrderSubmission();
    await handleOrderCreateError(makeError(503), makeContext());
    expect(deliveryNotice.value).not.toBeNull();

    dismissDeliveryNotice();
    expect(deliveryNotice.value).toBeNull();
  });
});
