<template>
  <div class="supplier-dashboard" data-testid="supplier-dashboard-page">
    <h1 class="supplier-dashboard__title">Дашборд поставщика</h1>

    <!-- KPI Cards -->
    <div class="supplier-dashboard__kpi-grid">
      <div v-for="kpi in kpiData" :key="kpi.key" class="supplier-dashboard__kpi-card" :data-testid="`kpi-${kpi.key}`">
        <div class="supplier-dashboard__kpi-icon" :style="{ background: kpi.bg }"></div>
        <div class="supplier-dashboard__kpi-value">{{ kpi.value }}</div>
        <div class="supplier-dashboard__kpi-label">{{ kpi.label }}</div>
      </div>
    </div>

    <!-- CDEK Settings -->
    <div v-if="supplier" class="supplier-dashboard__section supplier-dashboard__settings">
      <div class="supplier-dashboard__section-header">
        <h2 class="supplier-dashboard__section-title">Настройки доставки СДЭК</h2>
      </div>
      <div class="field">
        <label class="field__label">Код ПВЗ СДЭК (куда вы несёте заказы) <span class="required">*</span></label>
        <input
          v-model="supplier.cdek_shipment_point"
          class="field__input"
          placeholder="Например, MSK1"
          data-testid="supplier-cdek-pvz"
        />
      </div>
      <div class="field">
        <label class="field__label">Имя / название отправителя</label>
        <input
          v-model="supplier.sender_name"
          class="field__input"
          placeholder="Иван Иванов или ООО Поставщик"
        />
      </div>
      <div class="field">
        <label class="field__label">Телефон отправителя</label>
        <input
          v-model="supplier.sender_phone"
          class="field__input"
          type="tel"
          placeholder="+7 (999) 000-00-00"
        />
      </div>
      <button
        class="supplier-dashboard__save-btn"
        :disabled="savingSupplier"
        @click="saveSupplier"
      >
        {{ savingSupplier ? 'Сохранение...' : 'Сохранить настройки' }}
      </button>
    </div>

    <!-- Quick Links -->
    <div class="supplier-dashboard__quick-links">
      <router-link to="/my-products" class="supplier-dashboard__quick-link" data-testid="link-my-products">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4H6z"/>
          <line x1="3" y1="6" x2="21" y2="6"/>
          <path d="M16 10a4 4 0 01-8 0"/>
        </svg>
        Мои товары
      </router-link>
      <router-link to="/supplier-orders" class="supplier-dashboard__quick-link" data-testid="link-supplier-orders">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
          <line x1="16" y1="13" x2="8" y2="13"/>
          <line x1="16" y1="17" x2="8" y2="17"/>
          <polyline points="10 9 9 9 8 9"/>
        </svg>
        Мои заказы
      </router-link>
    </div>

    <!-- Charts Row -->
    <div class="supplier-dashboard__charts-row">
      <!-- Orders Chart -->
      <div class="supplier-dashboard__section supplier-dashboard__chart-section">
        <div class="supplier-dashboard__section-header">
          <h2 class="supplier-dashboard__section-title">Заказы за 30 дней</h2>
        </div>
        <div v-if="loading" class="supplier-dashboard__loading">Загрузка...</div>
        <div v-else-if="ordersByDay.length === 0" class="supplier-dashboard__empty" data-testid="orders-empty">
          Нет данных
        </div>
        <div v-else class="supplier-dashboard__chart">
          <div class="supplier-dashboard__chart-bars">
            <div
              v-for="item in ordersByDay"
              :key="item.date"
              class="supplier-dashboard__chart-bar-wrap"
            >
              <div class="supplier-dashboard__chart-bar-track">
                <div
                  class="supplier-dashboard__chart-bar"
                  :style="{ height: getBarHeight(item.orders) }"
                ></div>
              </div>
              <div class="supplier-dashboard__chart-label">{{ formatShortDate(item.date) }}</div>
              <div class="supplier-dashboard__chart-tooltip">{{ item.orders }} заказов</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Top Products -->
      <div class="supplier-dashboard__section supplier-dashboard__chart-section">
        <div class="supplier-dashboard__section-header">
          <h2 class="supplier-dashboard__section-title">Топ товаров</h2>
        </div>
        <div v-if="loading" class="supplier-dashboard__loading">Загрузка...</div>
        <div v-else-if="topProducts.length === 0" class="supplier-dashboard__empty" data-testid="products-empty">
          Нет данных
        </div>
        <div v-else class="supplier-dashboard__top-products">
          <div
            v-for="(product, idx) in topProducts"
            :key="product.id"
            class="supplier-dashboard__top-product"
            data-testid="top-product-item"
          >
            <div class="supplier-dashboard__top-product-rank">{{ idx + 1 }}</div>
            <div class="supplier-dashboard__top-product-info">
              <div class="supplier-dashboard__top-product-name">{{ product.name }}</div>
              <div class="supplier-dashboard__top-product-meta">{{ product.sold }} продано</div>
            </div>
            <div class="supplier-dashboard__top-product-revenue">{{ formatPrice(product.revenue) }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Top Products Table -->
    <div class="supplier-dashboard__section">
      <div class="supplier-dashboard__section-header">
        <h2 class="supplier-dashboard__section-title">Топ товаров (таблица)</h2>
      </div>
      <div v-if="loading" class="supplier-dashboard__loading">Загрузка...</div>
      <div v-else-if="topProducts.length === 0" class="supplier-dashboard__empty">Нет данных</div>
      <div v-else class="supplier-dashboard__table-wrapper">
        <table class="supplier-dashboard__table" data-testid="top-products-table">
          <thead>
            <tr>
              <th>№</th>
              <th>Название</th>
              <th>Продано</th>
              <th>Выручка</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(product, idx) in topProducts" :key="product.id">
              <td>{{ idx + 1 }}</td>
              <td>{{ product.name }}</td>
              <td>{{ product.sold }}</td>
              <td>{{ formatPrice(product.revenue) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import api from '@/services/api';
import { useToast } from '@/composables/useToast';

const { add: toast } = useToast();

const loading = ref(true);
const savingSupplier = ref(false);
const supplier = ref(null);
const kpi = ref({
  total_orders: 0,
  pending_orders: 0,
  shipped_orders: 0,
  delivered_orders: 0,
  total_revenue: 0,
  total_products: 0,
});
const ordersByDay = ref([]);
const topProducts = ref([]);

const kpiData = computed(() => [
  {
    key: 'total_orders',
    label: 'Всего заказов',
    value: kpi.value.total_orders,
    bg: '#e8f0fe',
  },
  {
    key: 'pending_orders',
    label: 'Ожидают отправки',
    value: kpi.value.pending_orders,
    bg: '#fff3e0',
  },
  {
    key: 'shipped_orders',
    label: 'Отправлено',
    value: kpi.value.shipped_orders,
    bg: '#e6f5e6',
  },
  {
    key: 'delivered_orders',
    label: 'Доставлено',
    value: kpi.value.delivered_orders,
    bg: '#e0f2f1',
  },
  {
    key: 'total_revenue',
    label: 'Выручка',
    value: formatPrice(kpi.value.total_revenue),
    bg: '#f3e5f5',
  },
  {
    key: 'total_products',
    label: 'Товаров',
    value: kpi.value.total_products,
    bg: '#fce4ec',
  },
]);

const maxOrders = computed(() => {
  if (!ordersByDay.value.length) return 1;
  return Math.max(...ordersByDay.value.map((d) => d.orders), 1);
});

function getBarHeight(orders) {
  return `${(orders / maxOrders.value) * 100}%`;
}

function formatShortDate(dateStr) {
  const d = new Date(dateStr);
  return `${d.getDate()}.${d.getMonth() + 1}`;
}

function formatPrice(value) {
  if (value === undefined || value === null) return '—';
  return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(value);
}

async function fetchDashboard() {
  loading.value = true;
  try {
    const [analyticsRes, supplierRes] = await Promise.all([
      api.get('/api/v1/analytics/supplier'),
      api.get('/api/v1/users/supplier/profile').catch(() => ({ data: null })),
    ]);
    kpi.value = analyticsRes.data.kpi || kpi.value;
    ordersByDay.value = analyticsRes.data.orders_by_day || [];
    topProducts.value = analyticsRes.data.top_products || [];
    supplier.value = supplierRes.data;
  } catch {
    toast('Не удалось загрузить аналитику', 'error');
  } finally {
    loading.value = false;
  }
}

async function saveSupplier() {
  if (!supplier.value) return;
  savingSupplier.value = true;
  try {
    const { data } = await api.patch('/api/v1/users/supplier/profile', {
      cdek_shipment_point: supplier.value.cdek_shipment_point,
      sender_name: supplier.value.sender_name,
      sender_phone: supplier.value.sender_phone,
    });
    supplier.value = data;
    toast('Настройки сохранены', 'success');
  } catch (err) {
    toast(err.response?.data?.detail || 'Не удалось сохранить настройки', 'error');
  } finally {
    savingSupplier.value = false;
  }
}

onMounted(fetchDashboard);
</script>

<style scoped>
.supplier-dashboard {
  padding: 16px;
  min-height: 100vh;
  background: var(--color-bg);
}

.supplier-dashboard__title {
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 20px;
}

/* KPI */
.supplier-dashboard__kpi-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

@media (min-width: 768px) {
  .supplier-dashboard__kpi-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (min-width: 1024px) {
  .supplier-dashboard__kpi-grid {
    grid-template-columns: repeat(6, 1fr);
  }
}

.supplier-dashboard__kpi-card {
  background: var(--color-bg-white);
  border-radius: 16px;
  padding: 16px;
  display: flex;
  flex-direction: column;
}

.supplier-dashboard__kpi-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-primary);
  margin-bottom: 10px;
}

.supplier-dashboard__kpi-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text);
  line-height: 1.2;
}

.supplier-dashboard__kpi-label {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-top: 4px;
}

/* Quick Links */
.supplier-dashboard__quick-links {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.supplier-dashboard__quick-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: 12px;
  background: var(--color-bg-white);
  color: var(--color-primary);
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
  border: 1px solid var(--color-border);
  transition: background 0.15s, border-color 0.15s;
}

.supplier-dashboard__quick-link:hover {
  background: var(--color-primary-light);
  border-color: var(--color-primary);
}

.supplier-dashboard__settings {
  margin-bottom: 16px;
}

.supplier-dashboard__settings .field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 12px;
}

.supplier-dashboard__settings .field__label {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text);
}

.supplier-dashboard__settings .field__input {
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-white);
  font-size: 15px;
  color: var(--color-text);
  width: 100%;
}

.supplier-dashboard__save-btn {
  width: 100%;
  padding: 12px;
  border-radius: 10px;
  background: var(--color-primary);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  border: none;
  cursor: pointer;
}

.supplier-dashboard__save-btn:disabled {
  opacity: 0.5;
}

/* Charts row */
.supplier-dashboard__charts-row {
  display: grid;
  gap: 16px;
  margin-bottom: 16px;
}

@media (min-width: 1024px) {
  .supplier-dashboard__charts-row {
    grid-template-columns: 2fr 1fr;
  }
}

/* Section */
.supplier-dashboard__section {
  background: var(--color-bg-white);
  border-radius: 16px;
  padding: 16px;
}

.supplier-dashboard__section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.supplier-dashboard__section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
}

.supplier-dashboard__loading,
.supplier-dashboard__empty {
  text-align: center;
  padding: 40px 20px;
  color: var(--color-text-secondary);
}

/* Chart */
.supplier-dashboard__chart {
  padding: 8px 0;
}

.supplier-dashboard__chart-bars {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 8px;
  height: 160px;
  padding-bottom: 24px;
  position: relative;
}

.supplier-dashboard__chart-bar-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
}

.supplier-dashboard__chart-bar-track {
  width: 100%;
  height: 140px;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  background: var(--color-bg);
  border-radius: 6px 6px 0 0;
  overflow: hidden;
}

.supplier-dashboard__chart-bar {
  width: 60%;
  background: var(--color-primary);
  border-radius: 6px 6px 0 0;
  min-height: 4px;
  transition: height 0.3s ease;
}

.supplier-dashboard__chart-label {
  position: absolute;
  bottom: 0;
  font-size: 11px;
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.supplier-dashboard__chart-tooltip {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%) translateY(-4px);
  background: var(--color-text);
  color: #fff;
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 6px;
  white-space: nowrap;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s;
}

.supplier-dashboard__chart-bar-wrap:hover .supplier-dashboard__chart-tooltip {
  opacity: 1;
}

/* Top Products */
.supplier-dashboard__top-products {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.supplier-dashboard__top-product {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  border-radius: 12px;
  background: var(--color-bg);
}

.supplier-dashboard__top-product-rank {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.supplier-dashboard__top-product-info {
  flex: 1;
  min-width: 0;
}

.supplier-dashboard__top-product-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.supplier-dashboard__top-product-meta {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-top: 2px;
}

.supplier-dashboard__top-product-revenue {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
}

/* Table */
.supplier-dashboard__table-wrapper {
  overflow-x: auto;
}

.supplier-dashboard__table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.supplier-dashboard__table th,
.supplier-dashboard__table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid var(--color-border);
}

.supplier-dashboard__table th {
  font-weight: 600;
  color: var(--color-text-secondary);
  font-size: 13px;
}
</style>
