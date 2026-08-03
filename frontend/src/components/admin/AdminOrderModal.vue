<template>
  <div v-if="visible" class="modal-overlay" data-testid="order-modal-overlay" @click.self="close">
    <div class="modal order-modal" data-testid="order-modal">
      <div class="modal__header">
        <h3>Заказ №{{ orderId }}</h3>
        <button class="modal__close" data-testid="order-modal-close" @click="close">&times;</button>
      </div>

      <div v-if="loading" class="order-modal__loading">Загрузка...</div>

      <div v-else-if="error" class="form-error" data-testid="order-modal-error">{{ error }}</div>

      <template v-else-if="detail">
        <div class="order-modal__summary">
          <span class="order-modal__date">{{ formatDateTimeShort(detail.created_at) }}</span>
          <span class="admin__status-badge" :class="'admin__status-badge--' + detail.status">
            {{ orderStatusLabel(detail.status) }}
          </span>
          <span class="order-modal__delivery-method" data-testid="order-modal-delivery-method">
            {{ detail.cdek_order ? 'CDEK' : '—' }}
          </span>
        </div>

        <div class="order-modal__tabs">
          <button
            class="order-modal__tab"
            :class="{ 'order-modal__tab--active': activeTab === 'order' }"
            data-testid="order-modal-tab-order"
            @click="activeTab = 'order'"
          >
            Заказ
          </button>
          <button
            v-if="detail.cdek_order"
            class="order-modal__tab"
            :class="{ 'order-modal__tab--active': activeTab === 'cdek' }"
            data-testid="order-modal-tab-cdek"
            @click="activeTab = 'cdek'"
          >
            CDEK
          </button>
        </div>

        <form v-show="activeTab === 'order'" class="modal__form" @submit.prevent="handleSubmit">
          <div class="order-modal__items" data-testid="order-modal-items">
            <div
              v-for="item in detail.items"
              :key="item.id"
              class="order-modal__item"
              :data-testid="`order-modal-item-${item.id}`"
            >
              <button
                v-if="item.image_url"
                type="button"
                class="order-modal__item-thumb-btn"
                :data-testid="`order-modal-item-thumb-${item.id}`"
                @click="openLightbox(item.image_url)"
              >
                <img :src="item.image_url" :alt="item.product_name" class="order-modal__item-thumb" />
              </button>
              <div v-else class="order-modal__item-thumb order-modal__item-thumb--placeholder">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <rect x="3" y="3" width="18" height="18" rx="2"/>
                  <circle cx="8.5" cy="8.5" r="1.5"/>
                  <path d="M21 15l-5-5L5 21"/>
                </svg>
              </div>
              <div class="order-modal__item-info">
                <div class="order-modal__item-name">{{ item.product_name }}</div>
                <div v-if="item.sku" class="order-modal__item-sku">Артикул: {{ item.sku }}</div>
                <div class="order-modal__item-price">{{ item.quantity }} × {{ formatPrice(item.price_at_time) }}</div>
              </div>
              <div class="order-modal__item-total">{{ formatPrice(item.line_total) }}</div>
            </div>
          </div>

          <div class="order-modal__totals" data-testid="order-modal-totals">
            <div class="order-modal__totals-row">
              <span>Товары</span>
              <span data-testid="order-modal-items-total">{{ formatPrice(detail.items_total) }}</span>
            </div>
            <div class="order-modal__totals-row">
              <span>Доставка</span>
              <span data-testid="order-modal-delivery-price">{{ formatPrice(detail.delivery_price) }}</span>
            </div>
            <div v-if="hasDiscount" class="order-modal__totals-row" data-testid="order-modal-discount-row">
              <span>Скидка</span>
              <span data-testid="order-modal-discount">{{ formatPrice(discountAmount) }}</span>
            </div>
            <div class="order-modal__totals-row order-modal__totals-row--grand">
              <span>Итого</span>
              <span data-testid="order-modal-total-price">{{ formatPrice(detail.total_price) }}</span>
            </div>
          </div>

          <div v-if="detail.buyer" class="order-modal__section" data-testid="order-modal-buyer">
            <div class="info-list">
              <div class="info-row">
                <span class="info-label">Покупатель</span>
                <span class="info-value" data-testid="order-modal-buyer-name">{{ detail.buyer.name || '—' }}</span>
              </div>
              <div class="info-row">
                <span class="info-label">Email</span>
                <span class="info-value" data-testid="order-modal-buyer-email">{{ detail.buyer.email || '—' }}</span>
              </div>
              <div class="info-row">
                <span class="info-label">Телефон</span>
                <span class="info-value" data-testid="order-modal-buyer-phone">{{ detail.buyer.phone || '—' }}</span>
              </div>
            </div>
          </div>

          <div v-if="recipientName" class="order-modal__section" data-testid="order-modal-recipient">
            <div class="info-list">
              <div class="info-row">
                <span class="info-label">Получатель</span>
                <span class="info-value" data-testid="order-modal-recipient-name">{{ recipientName }}</span>
              </div>
              <div v-if="recipientPhone" class="info-row">
                <span class="info-label">Телефон</span>
                <span class="info-value" data-testid="order-modal-recipient-phone">{{ recipientPhone }}</span>
              </div>
            </div>
          </div>

          <div class="order-modal__section" data-testid="order-modal-delivery">
            <div class="info-list">
              <div class="info-row">
                <span class="info-label">Адрес доставки</span>
                <span class="info-value" data-testid="order-modal-shipping-address">{{ detail.shipping_address || '—' }}</span>
              </div>
            </div>
          </div>

          <div class="order-modal__section" data-testid="order-modal-payment">
            <div class="info-list">
              <div class="info-row">
                <span class="info-label">Оплата</span>
                <span class="info-value" data-testid="order-modal-payment-method">{{ paymentMethod }}</span>
              </div>
              <div v-if="detail.payment" class="info-row">
                <span class="info-label">Статус оплаты</span>
                <span class="info-value" data-testid="order-modal-payment-status">{{ detail.payment.status || '—' }}</span>
              </div>
              <div v-if="detail.payment?.paid_at" class="info-row">
                <span class="info-label">Оплачен</span>
                <span class="info-value" data-testid="order-modal-payment-paid-at">{{ formatDateTimeShort(detail.payment.paid_at) }}</span>
              </div>
            </div>
          </div>

          <div class="field">
            <label class="field__label">Статус</label>
            <select
              v-model="orderForm.status"
              class="field__input"
              :disabled="detail.status === 'cancelled'"
              data-testid="order-modal-status-select"
            >
              <option value="pending">Ожидает оплаты</option>
              <option value="paid">Оплачен</option>
              <option value="shipped">Отправлен</option>
              <option value="delivered">Доставлен</option>
              <option v-if="orderForm.status === 'cancelled'" value="cancelled" disabled>Отменён</option>
            </select>
          </div>
          <div class="field">
            <label class="field__label">Трек-номер</label>
            <input v-model="orderForm.tracking_number" class="field__input" placeholder="Например, 1234567890" />
          </div>

          <button type="submit" class="modal__submit" :disabled="submitting" data-testid="order-modal-save-btn">
            {{ submitting ? 'Сохранение...' : 'Сохранить' }}
          </button>
          <button
            v-if="detail.status === 'paid'"
            type="button"
            class="admin__btn admin__btn--success"
            :disabled="submitting"
            :data-testid="`admin-order-ship-btn-${detail.id}`"
            @click="handleShip"
          >
            Подтвердить отправку
          </button>
          <button
            v-if="detail.status === 'pending' || detail.status === 'paid'"
            type="button"
            class="admin__btn admin__btn--danger"
            :disabled="submitting"
            :data-testid="`admin-order-cancel-btn-${detail.id}`"
            @click="handleCancel"
          >
            Отменить заказ
          </button>
        </form>

        <div v-if="detail.cdek_order" v-show="activeTab === 'cdek'" class="order-modal__cdek" data-testid="order-modal-cdek-tab">
          <div class="info-list">
            <div class="info-row">
              <span class="info-label">cdek_uuid</span>
              <span class="info-value info-value--monospace">{{ detail.cdek_order.cdek_uuid || '—' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">cdek_number</span>
              <span class="info-value info-value--monospace">{{ detail.cdek_order.cdek_number || '—' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">tracking_number</span>
              <span class="info-value info-value--monospace">{{ detail.cdek_order.tracking_number || '—' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">cdek_status</span>
              <span class="info-value">{{ detail.cdek_order.cdek_status || '—' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">status_date_time</span>
              <span class="info-value">{{ detail.cdek_order.status_date_time ? formatShortDate(detail.cdek_order.status_date_time) : '—' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">status_city</span>
              <span class="info-value">{{ detail.cdek_order.status_city || '—' }}</span>
            </div>
          </div>
          <div v-if="detail.cdek_order.tracking_url" class="order-modal__cdek-track">
            <a
              :href="detail.cdek_order.tracking_url"
              target="_blank"
              rel="noopener noreferrer"
              class="order-modal__track-link"
              data-testid="order-modal-cdek-tracking-link"
            >
              Отследить в CDEK
            </a>
          </div>
          <div v-if="cdekStatusHistory.length" class="order-modal__cdek-history" data-testid="order-modal-cdek-history">
            <h4 class="order-modal__cdek-history-title">История статусов</h4>
            <div class="order-modal__history-list">
              <div
                v-for="entry in cdekStatusHistory"
                :key="entry.id"
                class="order-modal__history-item"
              >
                <div class="order-modal__history-status">{{ entry.cdek_status_name || entry.cdek_status }}</div>
                <div class="order-modal__history-meta">
                  <span v-if="entry.status_date_time">{{ formatShortDate(entry.status_date_time) }}</span>
                  <span v-if="entry.city">{{ entry.city }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <div
        v-if="lightboxUrl"
        class="order-modal__lightbox"
        data-testid="order-image-lightbox"
        @click.self="closeLightbox"
      >
        <button class="order-modal__lightbox-close" data-testid="order-image-lightbox-close" @click="closeLightbox">&times;</button>
        <img :src="lightboxUrl" alt="Фото товара" class="order-modal__lightbox-img" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed, onUnmounted } from 'vue';
import { getAdminOrder, updateAdminOrder } from '@/api/admin';
import { shipOrderAdmin, cancelOrderAdmin } from '@/api/orders';
import { useToast } from '@/composables/useToast';
import { formatPriceCurrency as formatPrice } from '@/utils/price';
import { formatShortDate, formatDateTimeShort } from '@/utils/date';
import { orderStatusLabel } from '@/utils/order';

const props = defineProps({
  orderId: {
    type: [Number, String],
    default: null,
  },
  visible: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['update:visible', 'updated']);

const { add: toast } = useToast();

const detail = ref(null);
const loading = ref(false);
const error = ref('');
const activeTab = ref('order');
const orderForm = ref({ status: '', tracking_number: '' });
const submitting = ref(false);
const lightboxUrl = ref(null);

const reset = () => {
  detail.value = null;
  error.value = '';
  activeTab.value = 'order';
  orderForm.value = { status: '', tracking_number: '' };
  lightboxUrl.value = null;
};

const close = () => {
  emit('update:visible', false);
};

const fetchDetail = async () => {
  if (props.orderId === null || props.orderId === undefined) return;
  loading.value = true;
  error.value = '';
  try {
    const { data } = await getAdminOrder(props.orderId);
    detail.value = data;
    orderForm.value = {
      status: data.status,
      tracking_number: data.tracking_number || '',
    };
  } catch (err) {
    error.value = err.response?.data?.detail || 'Не удалось загрузить заказ';
  } finally {
    loading.value = false;
  }
};

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      reset();
      fetchDetail();
    }
  },
  { immediate: true }
);

watch(
  () => props.orderId,
  () => {
    if (props.visible) {
      reset();
      fetchDetail();
    }
  }
);

const cdekStatusHistory = computed(() => {
  const history = detail.value?.cdek_order?.status_history || [];
  return [...history].sort((a, b) => {
    const aDate = a.status_date_time ? new Date(a.status_date_time) : 0;
    const bDate = b.status_date_time ? new Date(b.status_date_time) : 0;
    return bDate - aDate;
  });
});

const recipientName = computed(() => {
  const r = detail.value?.recipient;
  if (r) {
    return [r.last_name, r.first_name, r.patronymic].filter(Boolean).join(' ');
  }
  return [detail.value?.recipient_last_name, detail.value?.recipient_first_name].filter(Boolean).join(' ');
});

const recipientPhone = computed(() => {
  return detail.value?.recipient?.phone || detail.value?.guest_phone || '';
});

const paymentMethod = computed(() => {
  return detail.value?.payment?.yookassa_payment_id ? 'ЮKassa' : '—';
});

// Скидка считается в копейках, чтобы float-округление не давало ложный показ.
const discountKopecks = computed(() => {
  if (!detail.value) return 0;
  const toKopecks = (v) => Math.round(Number(v) * 100);
  return (
    toKopecks(detail.value.items_total) +
    toKopecks(detail.value.delivery_price) -
    toKopecks(detail.value.total_price)
  );
});

const discountAmount = computed(() => discountKopecks.value / 100);

const hasDiscount = computed(() => discountKopecks.value !== 0);

const openLightbox = (url) => {
  lightboxUrl.value = url;
};

const closeLightbox = () => {
  lightboxUrl.value = null;
};

const onKeydown = (event) => {
  if (event.key === 'Escape' && lightboxUrl.value) {
    closeLightbox();
  }
};

// Esc-listener живёт только пока открыт лайтбокс (F-003, review).
watch(lightboxUrl, (url) => {
  if (url) {
    document.addEventListener('keydown', onKeydown);
  } else {
    document.removeEventListener('keydown', onKeydown);
  }
});

onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown);
});

const handleSubmit = async () => {
  submitting.value = true;
  try {
    await updateAdminOrder(detail.value.id, orderForm.value);
    toast('Заказ обновлён', 'success');
    await fetchDetail();
    emit('updated');
  } catch (err) {
    toast(err.response?.data?.detail || 'Ошибка обновления заказа', 'error');
  } finally {
    submitting.value = false;
  }
};

const handleShip = async () => {
  submitting.value = true;
  try {
    await shipOrderAdmin(detail.value.id);
    toast('Заказ отправлен', 'success');
    await fetchDetail();
    emit('updated');
  } catch (err) {
    toast(err.response?.data?.detail || 'Не удалось подтвердить отправку', 'error');
  } finally {
    submitting.value = false;
  }
};

const handleCancel = async () => {
  let message = 'Отменить заказ?';
  if (detail.value.status === 'paid') {
    message = 'Заказ уже оплачен. При отмене деньги будут автоматически возвращены покупателю. Отменить заказ?';
  }
  if (!confirm(message)) return;
  submitting.value = true;
  try {
    await cancelOrderAdmin(detail.value.id);
    toast('Заказ отменён', 'success');
    emit('updated');
    close();
  } catch (err) {
    toast(err.response?.data?.detail || 'Не удалось отменить заказ', 'error');
  } finally {
    submitting.value = false;
  }
};
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  z-index: 200;
}

@media (min-width: 640px) {
  .modal-overlay {
    align-items: center;
  }
}

.modal {
  background: var(--color-bg-white);
  width: 100%;
  max-width: 560px;
  max-height: 90vh;
  overflow-y: auto;
  border-radius: 20px 20px 0 0;
  padding: 20px 16px calc(24px + var(--bottom-nav-height, 60px));
}

@media (min-width: 640px) {
  .modal {
    border-radius: 16px;
    padding: 24px;
  }
}

.modal__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.modal__header h3 {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text);
}

.modal__close {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--color-bg);
  border: none;
  font-size: 20px;
  color: var(--color-text);
  cursor: pointer;
}

.modal__form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field__label {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text);
}

.field__input {
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-white);
  font-size: 15px;
  color: var(--color-text);
  width: 100%;
}

.field__input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.form-error {
  padding: 10px 12px;
  border-radius: 10px;
  background: #fff0f0;
  color: var(--color-danger);
  font-size: 14px;
}

.modal__submit {
  width: 100%;
  padding: 14px;
  border-radius: 12px;
  background: var(--color-primary);
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  border: none;
  cursor: pointer;
}

.modal__submit:disabled {
  opacity: 0.6;
}

.admin__btn {
  padding: 10px 16px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  border: none;
  cursor: pointer;
}

.admin__btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.admin__btn--success {
  background: #2e7d32;
  color: #fff;
}

.admin__btn--danger {
  background: var(--color-danger);
  color: #fff;
}

.admin__status-badge {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
}

.admin__status-badge--pending {
  background: #fff3e0;
  color: #e65100;
}

.admin__status-badge--paid {
  background: #e8f0fe;
  color: #1a73e8;
}

.admin__status-badge--shipped {
  background: #e6f5e6;
  color: #2e7d32;
}

.admin__status-badge--delivered {
  background: #e0f2f1;
  color: #00695c;
}

.admin__status-badge--cancelled {
  background: #fce4ec;
  color: #c62828;
}

.order-modal__loading {
  text-align: center;
  padding: 40px 20px;
  color: var(--color-text-secondary);
}

.order-modal__summary {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.order-modal__date {
  font-size: 14px;
  color: var(--color-text-secondary);
}

.order-modal__delivery-method {
  font-size: 14px;
  color: var(--color-text-secondary);
}

.order-modal__tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 8px;
}

.order-modal__tab {
  padding: 8px 16px;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-white);
  color: var(--color-text-secondary);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
}

.order-modal__tab--active {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

.order-modal__items {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.order-modal__item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--color-bg);
}

.order-modal__item-thumb-btn {
  padding: 0;
  border: none;
  background: none;
  cursor: zoom-in;
  flex-shrink: 0;
}

.order-modal__item-thumb {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  object-fit: cover;
  display: block;
}

.order-modal__item-thumb--placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-white);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.order-modal__item-info {
  flex: 1;
  min-width: 0;
}

.order-modal__item-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text);
}

.order-modal__item-sku {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.order-modal__item-price {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.order-modal__item-total {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  white-space: nowrap;
}

.order-modal__totals {
  padding: 12px;
  border-radius: 10px;
  background: var(--color-bg);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.order-modal__totals-row {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  color: var(--color-text);
}

.order-modal__totals-row--grand {
  font-weight: 700;
  font-size: 15px;
  border-top: 1px solid var(--color-border);
  padding-top: 8px;
}

.order-modal__section {
  padding: 12px;
  border-radius: 10px;
  background: var(--color-bg);
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  font-size: 14px;
}

.info-label {
  color: var(--color-text-secondary);
}

.info-value {
  color: var(--color-text);
  font-weight: 500;
  text-align: right;
  word-break: break-all;
}

.info-value--monospace {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
}

.order-modal__cdek-track {
  margin-top: 16px;
}

.order-modal__track-link {
  display: inline-block;
  padding: 10px 16px;
  border-radius: 10px;
  background: var(--color-primary);
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
}

.order-modal__cdek-history {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--color-border);
}

.order-modal__cdek-history-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 12px;
}

.order-modal__history-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.order-modal__history-item {
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--color-bg);
}

.order-modal__history-status {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text);
  margin-bottom: 4px;
}

.order-modal__history-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--color-text-secondary);
}

.order-modal__lightbox {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 300;
  cursor: zoom-out;
}

.order-modal__lightbox-img {
  max-width: 90vw;
  max-height: 90vh;
  border-radius: 8px;
}

.order-modal__lightbox-close {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.15);
  border: none;
  font-size: 24px;
  color: #fff;
  cursor: pointer;
}
</style>
