<template>
  <div class="checkout" data-testid="checkout-page">
    <div class="checkout__header">
      <button class="checkout__back" @click="router.back()">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 12H5M12 19l-7-7 7-7"/>
        </svg>
      </button>
      <h1 class="checkout__title">Оплата заказа №{{ orderId }}</h1>
    </div>

    <div v-if="loading" class="checkout__loading">Загрузка...</div>

    <div v-else-if="error" class="checkout__error">
      <p>{{ error }}</p>
      <button class="checkout__retry" @click="fetchOrder">Повторить</button>
    </div>

    <template v-else-if="order">
      <!-- Order Summary -->
      <div class="checkout__card">
        <div class="checkout__section-title">Сумма к оплате</div>
        <div class="checkout__amount">{{ formatPrice(order.total_price) }} ₽</div>
        <div class="checkout__items-count">{{ order.items?.length || 0 }} товаров</div>
        <div v-if="order.delivery_method" class="checkout__delivery-info">
          <div class="checkout__delivery-row">
            <span>Доставка: {{ order.delivery_method.name }}</span>
            <span>{{ Number(order.delivery_method.base_price) > 0 ? formatPrice(order.delivery_method.base_price) + ' ₽' : 'Бесплатно' }}</span>
          </div>
          <div v-if="order.delivery_method.estimated_days" class="checkout__delivery-days">
            Срок: {{ order.delivery_method.estimated_days }} {{ order.delivery_method.estimated_days === 1 ? 'день' : order.delivery_method.estimated_days < 5 ? 'дня' : 'дней' }}
          </div>
        </div>

        <div v-if="recipientName" class="checkout__recipient" data-testid="checkout-recipient">
          <div class="checkout__recipient-label">Получатель</div>
          <div class="checkout__recipient-name">{{ recipientName }}</div>
          <div v-if="recipientPhone" class="checkout__recipient-phone" data-testid="checkout-recipient-phone">{{ recipientPhone }}</div>
        </div>
      </div>

      <!-- Payment Info -->
      <div class="checkout__card">
        <div class="checkout__section-title">Способ оплаты</div>
        <div class="checkout__payment-method">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="1" y="4" width="22" height="16" rx="2" ry="2"/>
            <line x1="1" y1="10" x2="23" y2="10"/>
          </svg>
          <span>Банковская карта или другой способ через ЮKassa</span>
        </div>
        <p class="checkout__payment-note">
          После нажатия «Оплатить» вы будете перенаправлены на защищённую страницу ЮKassa для ввода данных карты.
        </p>
      </div>

      <!-- Security Note -->
      <div class="checkout__security">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
          <path d="M7 11V7a5 5 0 0110 0v4"/>
        </svg>
        <span>Данные карты вводятся на странице ЮKassa. Мы не храним и не обрабатываем их.</span>
      </div>

      <!-- Pay Button -->
      <button
        class="checkout__pay-btn"
        :disabled="processing"
        data-testid="pay-button"
        @click="processPayment"
      >
        <span v-if="processing">Переход к оплате...</span>
        <span v-else>Оплатить {{ formatPrice(order.total_price) }} ₽</span>
      </button>

      <!-- Cancel -->
      <button class="checkout__cancel" @click="cancelPayment" :disabled="processing">
        Отменить
      </button>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuth } from '@/composables/useAuth';
import { useToast } from '@/composables/useToast';
import { getOrder, getGuestOrder } from '@/api/orders';
import { createPayment, createGuestPayment } from '@/api/payments';
import { formatPrice } from '@/utils/price';

const route = useRoute();
const router = useRouter();
const { add: toast } = useToast();
const { isAuthenticated } = useAuth();

const orderId = computed(() => route.params.id);
const guestEmail = computed(() => sessionStorage.getItem('guest_checkout_email') || '');
const isGuest = computed(() => !isAuthenticated.value && Boolean(guestEmail.value));

const order = ref(null);
const loading = ref(true);
const error = ref(null);
const processing = ref(false);

const recipientName = computed(() => {
  const r = order.value?.recipient;
  if (!r) {
    const parts = [order.value?.recipient_first_name, order.value?.recipient_last_name].filter(Boolean);
    return parts.length ? parts.join(' ') : '';
  }
  const parts = [r.last_name, r.first_name, r.patronymic].filter(Boolean);
  return parts.join(' ');
});

const recipientPhone = computed(() => {
  return order.value?.recipient?.phone || order.value?.guest_phone || '';
});

const fetchOrder = async () => {
  loading.value = true;
  error.value = null;
  try {
    const { data } = isGuest.value
      ? await getGuestOrder(orderId.value, guestEmail.value)
      : await getOrder(orderId.value);
    order.value = data;
    if (data.status !== 'pending') {
      const target = isGuest.value
        ? `/payment/success?order_id=${orderId.value}`
        : `/orders/${orderId.value}`;
      await router.replace(target);
      return;
    }
  } catch (err) {
    error.value = err.response?.data?.detail || 'Не удалось загрузить заказ';
  } finally {
    loading.value = false;
  }
};

const processPayment = async () => {
  if (processing.value) return;
  processing.value = true;

  try {
    const { data } = isGuest.value
      ? await createGuestPayment(orderId.value, guestEmail.value)
      : await createPayment(orderId.value);
    const confirmationUrl = data.confirmation_url;

    if (!confirmationUrl) {
      toast('Не удалось получить ссылку на оплату', 'error');
      processing.value = false;
      return;
    }

    // Редирект на страницу оплаты ЮKassa
    window.location.href = confirmationUrl;
  } catch (err) {
    const detail = err.response?.data?.detail;
    toast(detail || 'Ошибка при создании платежа', 'error');
    processing.value = false;
  }
};

const cancelPayment = () => {
  if (confirm('Отменить оплату? Заказ останется в ожидании.')) {
    const target = isGuest.value
      ? `/payment/failed?order_id=${orderId.value}`
      : `/orders/${orderId.value}`;
    router.push(target);
  }
};

onMounted(fetchOrder);
</script>

<style scoped>
.checkout {
  max-width: 480px;
  margin: 0 auto;
  padding: 16px 16px calc(24px + var(--bottom-nav-height, 56px));
  min-height: 100vh;
  background: var(--color-bg);
}

.checkout__header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.checkout__back {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: none;
  background: var(--color-bg-white);
  color: var(--color-text);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.checkout__title {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text);
}

.checkout__card {
  background: var(--color-bg-white);
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 12px;
}

.checkout__section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  margin-bottom: 10px;
}

.checkout__amount {
  font-size: 28px;
  font-weight: 700;
  color: var(--color-text);
  line-height: 1.2;
}

.checkout__items-count {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin-top: 4px;
}

.checkout__payment-method {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-radius: 10px;
  background: var(--color-bg);
  font-size: 14px;
  color: var(--color-text);
}

.checkout__payment-method svg {
  flex-shrink: 0;
  color: var(--color-primary);
}

.checkout__payment-note {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-top: 10px;
  line-height: 1.4;
}

.checkout__security {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border-radius: 10px;
  background: #e8f0fe;
  color: #1a73e8;
  font-size: 13px;
  margin-bottom: 16px;
}

.checkout__pay-btn {
  width: 100%;
  padding: 16px;
  border-radius: 14px;
  background: var(--color-primary);
  color: #fff;
  font-size: 17px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  margin-bottom: 10px;
}

.checkout__pay-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.checkout__cancel {
  width: 100%;
  padding: 14px;
  border-radius: 14px;
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 15px;
  font-weight: 500;
  border: none;
  cursor: pointer;
}

.checkout__loading,
.checkout__error {
  text-align: center;
  padding: 40px 20px;
  color: var(--color-text-secondary);
}

.checkout__error {
  color: var(--color-danger);
}

.checkout__retry {
  margin-top: 12px;
  padding: 10px 20px;
  border-radius: 10px;
  background: var(--color-primary);
  color: #fff;
  border: none;
  font-size: 15px;
  cursor: pointer;
}

.checkout__delivery-info {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border);
}

.checkout__delivery-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  color: var(--color-text);
}

.checkout__delivery-days {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-top: 4px;
}

.checkout__recipient {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border);
}

.checkout__recipient-label {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-bottom: 2px;
}

.checkout__recipient-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
}

.checkout__recipient-phone {
  font-size: 14px;
  color: var(--color-text);
  margin-top: 2px;
}
</style>
