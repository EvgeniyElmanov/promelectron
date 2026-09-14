<template>
  <div v-if="visible" class="modal-overlay" data-testid="user-detail-modal-overlay" @click.self="close">
    <div
      ref="dialogRef"
      class="modal user-detail-modal"
      data-testid="user-detail-modal"
      role="dialog"
      aria-modal="true"
      :aria-labelledby="titleId"
      tabindex="-1"
    >
      <div class="modal__header">
        <h3 :id="titleId">{{ isGuest ? 'Гостевой заказ' : 'Детали пользователя' }}</h3>
        <button class="modal__close" data-testid="user-detail-modal-close" aria-label="Закрыть" @click="close">&times;</button>
      </div>

      <div v-if="isGuest" class="user-detail-modal__content">
        <div class="info-list" data-testid="user-detail-guest-info">
          <div class="info-row">
            <span class="info-label">Имя</span>
            <span class="info-value" data-testid="user-detail-guest-name">{{ guestName }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Email</span>
            <span class="info-value" data-testid="user-detail-guest-email">{{ guestEmail }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">Телефон</span>
            <span class="info-value" data-testid="user-detail-guest-phone">{{ guestPhone }}</span>
          </div>
        </div>
      </div>

      <div v-else-if="loading" class="user-detail-modal__loading">Загрузка...</div>

      <div v-else-if="error" class="form-error">{{ error }}</div>

      <template v-else>
        <div class="user-detail-modal__tabs">
          <button
            class="user-detail-modal__tab"
            :class="{ 'user-detail-modal__tab--active': activeTab === 'profile' }"
            data-testid="user-detail-tab-profile"
            @click="activeTab = 'profile'"
          >
            Профиль
          </button>
          <button
            class="user-detail-modal__tab"
            :class="{ 'user-detail-modal__tab--active': activeTab === 'orders' }"
            data-testid="user-detail-tab-orders"
            @click="activeTab = 'orders'"
          >
            Заказы
          </button>
        </div>

        <div v-show="activeTab === 'profile'" class="user-detail-modal__content" data-testid="user-detail-profile-panel">
          <div class="info-list">
            <div class="info-row">
              <span class="info-label">ID</span>
              <span class="info-value" data-testid="user-detail-id">{{ detail?.id ?? '—' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Email</span>
              <span class="info-value" data-testid="user-detail-email">{{ displayEmail }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">ФИО</span>
              <span class="info-value" data-testid="user-detail-full-name">{{ fullName }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Телефон</span>
              <span class="info-value" data-testid="user-detail-phone">{{ displayPhone }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Страна</span>
              <span class="info-value" data-testid="user-detail-country">{{ displayCountry }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Адрес доставки</span>
              <span class="info-value" data-testid="user-detail-address">{{ displayAddress }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Роль</span>
              <span class="info-value" data-testid="user-detail-role">{{ displayRole }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Статус</span>
              <span class="info-value" data-testid="user-detail-active">{{ displayActiveStatus }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Email подтверждён</span>
              <span class="info-value" data-testid="user-detail-email-verified">{{ displayVerification }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">Дата регистрации</span>
              <span class="info-value" data-testid="user-detail-created-at">{{ displayCreatedAt }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">OAuth-источник</span>
              <span class="info-value" data-testid="user-detail-oauth">{{ displayOAuth }}</span>
            </div>
          </div>
        </div>

        <div v-show="activeTab === 'orders'" class="user-detail-modal__content" data-testid="user-detail-orders-panel">
          <div v-if="userOrders.length === 0" class="user-detail-modal__empty">Нет заказов</div>
          <div v-else class="admin__table-wrapper">
            <table class="admin__table" data-testid="user-detail-orders-table">
              <thead>
                <tr>
                  <th>№</th>
                  <th>Сумма</th>
                  <th>Статус</th>
                  <th>Дата</th>
                  <th class="admin__table-actions">Действия</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="order in userOrders" :key="order.id">
                  <td :data-testid="`user-detail-order-id-${order.id}`">{{ order.id }}</td>
                  <td :data-testid="`user-detail-order-total-${order.id}`">{{ formatPrice(order.total_price) }}</td>
                  <td>
                    <span class="admin__status-badge" :class="'admin__status-badge--' + order.status">
                      {{ orderStatusLabel(order.status) }}
                    </span>
                  </td>
                  <td :data-testid="`user-detail-order-date-${order.id}`">{{ formatShortDate(order.created_at) }}</td>
                  <td class="admin__table-actions">
                    <AppButton
                      variant="secondary"
                      size="sm"
                      :data-testid="`user-detail-order-open-${order.id}`"
                      @click="openOrder(order)"
                    >
                      Открыть
                    </AppButton>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue';
import { getAdminUserDetail } from '@/api/admin';
import { formatPriceCurrency as formatPrice } from '@/utils/price';
import { formatShortDate, formatDate } from '@/utils/date';
import { orderStatusLabel } from '@/utils/order';
import { useModal } from '@/composables/useModal';
import AppButton from '@/components/ui/AppButton.vue';

const props = defineProps({
  userId: {
    type: [Number, String],
    default: null,
  },
  guestData: {
    type: Object,
    default: null,
  },
  visible: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['update:visible', 'view-order']);

const detail = ref(null);
const loading = ref(false);
const error = ref('');
const activeTab = ref('profile');

const isGuest = computed(() => props.userId === null || props.userId === undefined);

const reset = () => {
  detail.value = null;
  error.value = '';
  activeTab.value = 'profile';
};

const close = () => {
  emit('update:visible', false);
};

const { dialogRef, titleId } = useModal({
  isOpen: () => props.visible,
  onClose: close,
});

const fetchDetail = async () => {
  if (isGuest.value) return;
  loading.value = true;
  error.value = '';
  try {
    const { data } = await getAdminUserDetail(props.userId);
    detail.value = data;
  } catch (err) {
    error.value = err.response?.data?.detail || 'Не удалось загрузить данные пользователя';
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
  }
);

watch(
  () => props.userId,
  () => {
    if (props.visible) {
      if (isGuest.value) {
        reset();
        detail.value = null;
      } else {
        detail.value = null;
        fetchDetail();
      }
    }
  }
);

const fullName = computed(() => {
  const d = detail.value;
  if (!d) return '—';
  const parts = [d.last_name, d.first_name, d.patronymic].filter(Boolean);
  if (parts.length) return parts.join(' ');
  return d.full_name || d.email || `Пользователь #${d.id}`;
});

const displayEmail = computed(() => detail.value?.email || '—');
const displayPhone = computed(() => detail.value?.phone || '—');
const displayCountry = computed(() => detail.value?.country_code || '—');
const displayRole = computed(() => {
  const labels = { user: 'Покупатель', admin: 'Админ', supplier: 'Поставщик' };
  return labels[detail.value?.role] || detail.value?.role || '—';
});
const displayActiveStatus = computed(() => (detail.value?.is_active ? 'Активен' : 'Заблокирован'));
const displayVerification = computed(() => (detail.value?.email_verified ? 'Подтверждён' : 'Не подтверждён'));
const displayCreatedAt = computed(() => formatDate(detail.value?.created_at));
const displayOAuth = computed(() => {
  const accounts = detail.value?.social_accounts || [];
  if (!accounts.length) return '—';
  return accounts.map((a) => a.provider).join(', ');
});

const displayAddress = computed(() => {
  const address = detail.value?.shipping_address;
  if (!address) return '—';
  const parts = [address.city, address.street, address.house, address.apartment].filter(Boolean);
  return parts.length ? parts.join(', ') : '—';
});

const userOrders = computed(() => detail.value?.orders || []);

const guestName = computed(() => props.guestData?.guest_name || '—');
const guestEmail = computed(() => props.guestData?.guest_email || '—');
const guestPhone = computed(() => props.guestData?.guest_phone || '—');

const openOrder = (order) => {
  emit('view-order', order);
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
  padding: 20px 16px calc(24px + var(--bottom-nav-height, 60px) + env(safe-area-inset-bottom, 0px));
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

.user-detail-modal__tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 8px;
}

.user-detail-modal__tab {
  padding: 8px 16px;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-white);
  color: var(--color-text-secondary);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
}

.user-detail-modal__tab--active {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

.user-detail-modal__content {
  margin-top: 4px;
}

.user-detail-modal__loading,
.user-detail-modal__empty {
  text-align: center;
  padding: 40px 20px;
  color: var(--color-text-secondary);
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
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

.form-error {
  padding: 10px 12px;
  border-radius: 10px;
  background: #fff0f0;
  color: var(--color-danger);
  font-size: 14px;
}

.admin__table-wrapper {
  overflow-x: auto;
}

.admin__table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.admin__table th,
.admin__table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid var(--color-border);
}

.admin__table th {
  font-weight: 600;
  color: var(--color-text-secondary);
  font-size: 13px;
}

.admin__table-actions {
  white-space: nowrap;
  width: 1%;
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
</style>
