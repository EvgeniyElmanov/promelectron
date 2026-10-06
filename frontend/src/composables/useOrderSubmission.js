import { ref } from 'vue';
import { calculateDelivery } from '@/api/cdek';
import { useToast } from '@/composables/useToast';
import { formatPrice } from '@/utils/price';

// gh-269: сервер (#211) сверяет цену доставки с расчётом СДЭК при создании
// заказа. 409 «Стоимость доставки устарела» → фронт пересчитывает тариф,
// обновляет выбранную доставку и просит подтверждение по новой цене
// (авто-retry запрещён — деньги); 503 → «недоступен» + повтор.
// Общий обработчик для Cart.vue и GuestCheckout.vue, чтобы пути не разъехались.

const TOAST_DURATION = 6000;

// Тело /cdek/calculate/ повторяет серверный пересчёт
// (OrderService._resolve_delivery_price): те же поля и реальное quantity,
// иначе цена на фронте снова разойдётся со сверкой при повторном сабмите.
export const buildCalculateItems = (items) =>
  items.map((item) => {
    const product = item.product || item;
    return {
      weight_grams: product.weight_grams || 1000,
      quantity: item.quantity || 1,
      length_cm: product.length_cm || 10,
      width_cm: product.width_cm || 10,
      height_cm: product.height_cm || 10,
    };
  });

export const useOrderSubmission = () => {
  const { add: toast } = useToast();

  const recalculating = ref(false);
  // { type: 'price-update', oldPrice, newPrice } — ждёт подтверждения;
  // { type: 'unavailable' } — СДЭК недоступен, можно повторить.
  const deliveryNotice = ref(null);

  const dismissDeliveryNotice = () => {
    deliveryNotice.value = null;
  };

  const recalculateTariff = async ({ items, supplierId, selectedDelivery }) => {
    const { tariffs } = await calculateDelivery({
      items: buildCalculateItems(items),
      supplier_id: supplierId,
      to_location: selectedDelivery.to_location ?? undefined,
      delivery_point: selectedDelivery.delivery_point ?? undefined,
    });
    return (
      (tariffs || []).find(
        (t) => Number(t.tariff_code) === Number(selectedDelivery.tariff_code),
      ) ?? null
    );
  };

  /**
   * Обработать ошибку создания заказа (409/503 от сверки цены доставки).
   * Возвращает true, если ошибка обработана, иначе false — вызывающий код
   * показывает свой стандартный toast с detail.
   */
  const handleOrderCreateError = async (
    err,
    { items, supplierId, selectedDelivery, onDeliveryChange },
  ) => {
    const status = err?.response?.status;

    if (status === 503) {
      deliveryNotice.value = { type: 'unavailable' };
      toast('Сервис доставки временно недоступен. Попробуйте повторить позже.', 'error', TOAST_DURATION);
      return true;
    }

    if (status !== 409) {
      return false;
    }

    recalculating.value = true;
    try {
      const tariff = await recalculateTariff({ items, supplierId, selectedDelivery });
      if (!tariff) {
        // Тариф исчез из ответа СДЭК — пересчитывать нечего, нужен перевыбор.
        onDeliveryChange(null);
        toast('Выбранный тариф доставки больше недоступен. Перевыберите доставку.', 'error', TOAST_DURATION);
        return true;
      }
      const oldPrice = Number(selectedDelivery.price) || 0;
      const newPrice = Number(tariff.price);
      onDeliveryChange({
        ...selectedDelivery,
        price: newPrice,
        period_min: tariff.period_min ?? selectedDelivery.period_min,
        period_max: tariff.period_max ?? selectedDelivery.period_max,
      });
      deliveryNotice.value = { type: 'price-update', oldPrice, newPrice };
      toast(
        `Стоимость доставки изменилась: ${formatPrice(oldPrice)} ₽ → ${formatPrice(newPrice)} ₽`,
        'info',
        TOAST_DURATION,
      );
      return true;
    } catch {
      // Пересчёт сам упал (СДЭК не ответил и т.п.) — показываем исходный detail.
      const detail = err.response?.data?.detail;
      toast(detail || 'Не удалось пересчитать доставку. Перевыберите доставку и повторите заказ.', 'error', TOAST_DURATION);
      return true;
    } finally {
      recalculating.value = false;
    }
  };

  return {
    recalculating,
    deliveryNotice,
    dismissDeliveryNotice,
    handleOrderCreateError,
  };
};
