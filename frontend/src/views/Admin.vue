<template>
  <div class="admin" data-testid="admin-page">
    <h1 class="admin__title">Панель администратора</h1>

    <!-- Section Tab Navigation -->
    <div class="admin__tabs">
      <button
        v-for="tab in sectionTabs"
        :key="tab.key"
        class="admin__tab"
        :class="{ 'admin__tab--active': activeSectionTab === tab.key }"
        :data-testid="`admin-section-tab-${tab.key}`"
        @click="activeSectionTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- Dashboard Tab -->
    <div v-show="activeSectionTab === 'dashboard'" class="admin__tab-panel" data-testid="admin-section-panel-dashboard">
      <!-- KPI Cards -->
      <div class="admin__kpi-grid">
        <div v-for="kpi in kpiData" :key="kpi.key" class="admin__kpi-card">
          <div class="admin__kpi-icon" :style="{ background: kpi.bg }"></div>
          <div class="admin__kpi-value">{{ kpi.value }}</div>
          <div class="admin__kpi-label">{{ kpi.label }}</div>
        </div>
      </div>

      <!-- Charts Row -->
      <div class="admin__charts-row">
        <!-- Orders Chart -->
        <div class="admin__section admin__chart-section">
          <div class="admin__section-header">
            <h2 class="admin__section-title">Заказы за 7 дней</h2>
          </div>
          <div v-if="loading.ordersByDay" class="admin__loading">Загрузка...</div>
          <div v-else-if="ordersByDay.length === 0" class="admin__empty">Нет данных</div>
          <div v-else class="admin__chart">
            <div class="admin__chart-bars">
              <div
                v-for="item in ordersByDay"
                :key="item.date"
                class="admin__chart-bar-wrap"
              >
                <div class="admin__chart-bar-track">
                  <div
                    class="admin__chart-bar"
                    :style="{ height: getBarHeight(item.orders) }"
                  ></div>
                </div>
                <div class="admin__chart-label">{{ formatShortDate(item.date) }}</div>
                <div class="admin__chart-tooltip">{{ item.orders }} заказов</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Top Products -->
        <div class="admin__section admin__chart-section">
          <div class="admin__section-header">
            <h2 class="admin__section-title">Топ товаров</h2>
          </div>
          <div v-if="loading.topProducts" class="admin__loading">Загрузка...</div>
          <div v-else-if="topProducts.length === 0" class="admin__empty">Нет данных</div>
          <div v-else class="admin__top-products">
            <div
              v-for="(product, idx) in topProducts"
              :key="product.id"
              class="admin__top-product"
            >
              <div class="admin__top-product-rank">{{ idx + 1 }}</div>
              <div class="admin__top-product-info">
                <div class="admin__top-product-name">{{ product.name }}</div>
                <div class="admin__top-product-meta">{{ product.sold }} продано</div>
              </div>
              <div class="admin__top-product-revenue">{{ formatPrice(product.revenue) }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Users Tab -->
    <div v-show="activeSectionTab === 'users'" class="admin__tab-panel" data-testid="admin-section-panel-users">
      <div class="admin__section">
        <div class="admin__section-header">
          <h2 class="admin__section-title">Пользователи</h2>
        </div>
        <div v-if="loading.users" class="admin__loading">Загрузка...</div>
        <div v-else-if="users.length === 0" class="admin__empty">Нет пользователей</div>
        <div v-else class="admin__table-wrapper">
          <table class="admin__table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Email</th>
                <th>Имя</th>
                <th>Роль</th>
                <th>Статус</th>
                <th class="admin__table-actions">Действия</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="u in users" :key="u.id" data-testid="user-row">
                <td>{{ u.id }}</td>
                <td>{{ u.email }}</td>
                <td>{{ u.full_name || '—' }}</td>
                <td>
                  <span class="admin__role-badge" :class="`admin__role-badge--${u.role}`">
                    {{ roleLabel(u.role) }}
                  </span>
                </td>
                <td>
                  <span class="admin__status-badge" :class="u.is_active ? 'admin__status-badge--active' : 'admin__status-badge--inactive'">
                    {{ u.is_active ? 'Активен' : 'Заблокирован' }}
                  </span>
                </td>
                <td class="admin__table-actions">
                  <button
                    class="admin__btn admin__btn--small"
                    :class="u.is_active ? 'admin__btn--danger' : 'admin__btn--success'"
                    @click="toggleUser(u.id)"
                    :disabled="submittingUser === u.id"
                  >
                    {{ u.is_active ? 'Заблокировать' : 'Разблокировать' }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Categories Tab -->
    <div v-show="activeSectionTab === 'categories'" class="admin__tab-panel" data-testid="admin-section-panel-categories">
      <div class="admin__section" data-testid="categories-section">
        <div class="admin__section-header">
          <h2 class="admin__section-title">Категории</h2>
          <button class="admin__btn admin__btn--primary" @click="openCreateModal" data-testid="add-category-btn">+ Добавить</button>
        </div>

        <div class="admin__category-tabs">
          <button
            class="admin__category-tab"
            :class="{ 'admin__category-tab--active': activeCategoryTab === null }"
            data-testid="category-tab-all"
            @click="setCategoryActiveTab(null)"
          >
            Все
          </button>
          <button
            v-for="root in rootCategories"
            :key="root.id"
            class="admin__category-tab"
            :class="{ 'admin__category-tab--active': activeCategoryTab === root.id }"
            :data-testid="`category-tab-${root.id}`"
            @click="setCategoryActiveTab(root.id)"
          >
            {{ root.name }}
          </button>
        </div>

        <div class="admin__category-search">
          <input
            v-model="categorySearchQuery"
            type="text"
            class="field__input"
            placeholder="Поиск по названию..."
            data-testid="category-search-input"
            @input="onCategorySearchInput(categorySearchQuery)"
          />
        </div>

        <SkeletonAdminTable v-if="categoryLoading" />

        <div v-else-if="displayedCategories.length === 0" class="admin__empty" data-testid="categories-empty">
          <template v-if="activeCategoryTab === null">Нет категорий</template>
          <template v-else>В этой категории пока нет подкатегорий</template>
        </div>

        <div v-else class="admin__table-wrapper">
          <table class="admin__table" data-testid="categories-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Название</th>
                <th>Описание</th>
                <th>Товаров</th>
                <th class="admin__table-actions">Действия</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="cat in displayedCategories" :key="cat.id" :data-testid="`category-row-${cat.id}`">
                <td>{{ cat.id }}</td>
                <td>{{ cat.name }}</td>
                <td>{{ cat.description || '—' }}</td>
                <td>{{ cat.product_count ?? 0 }}</td>
                <td class="admin__table-actions">
                  <button class="admin__icon-btn admin__icon-btn--edit" @click="openEditModal(cat)">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
                      <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
                    </svg>
                  </button>
                  <button class="admin__icon-btn admin__icon-btn--delete" @click="deleteCategory(cat.id)">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <polyline points="3 6 5 6 21 6"/>
                      <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
                    </svg>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>

          <button
            v-if="activeCategoryTab === null && displayedCategories.length < categoryTotal"
            class="admin__load-more"
            data-testid="categories-load-more"
            @click="loadMoreCategories"
          >
            Показать ещё
          </button>
        </div>
      </div>
    </div>

    <!-- Delivery Tab -->
    <div v-show="activeSectionTab === 'delivery'" class="admin__tab-panel" data-testid="admin-section-panel-delivery">
      <div class="admin__section">
        <div class="admin__section-header">
          <h2 class="admin__section-title">Способы доставки</h2>
          <button class="admin__btn admin__btn--primary" @click="openCreateDeliveryModal">+ Добавить</button>
        </div>

        <SkeletonAdminTable v-if="loading.delivery" />

        <div v-else-if="deliveryMethods.length === 0" class="admin__empty">Нет способов доставки</div>

        <div v-else class="admin__table-wrapper">
          <table class="admin__table" data-testid="delivery-methods-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Название</th>
                <th>Цена</th>
                <th>Срок</th>
                <th>Статус</th>
                <th class="admin__table-actions">Действия</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="method in deliveryMethods" :key="method.id">
                <td>{{ method.id }}</td>
                <td>{{ method.name }}</td>
                <td>{{ method.base_price > 0 ? formatPrice(method.base_price) : 'Бесплатно' }}</td>
                <td>{{ method.estimated_days || '—' }}</td>
                <td>
                  <span class="admin__status-badge" :class="method.is_active ? 'admin__status-badge--active' : 'admin__status-badge--inactive'">
                    {{ method.is_active ? 'Активен' : 'Неактивен' }}
                  </span>
                </td>
                <td class="admin__table-actions">
                  <button class="admin__icon-btn admin__icon-btn--edit" @click="openEditDeliveryModal(method)">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
                      <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
                    </svg>
                  </button>
                  <button class="admin__icon-btn admin__icon-btn--delete" @click="deleteDeliveryMethod(method.id)">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <polyline points="3 6 5 6 21 6"/>
                      <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
                    </svg>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Orders Tab -->
    <div v-show="activeSectionTab === 'orders'" class="admin__tab-panel" data-testid="admin-section-panel-orders">
      <div class="admin__section">
        <div class="admin__section-header">
          <h2 class="admin__section-title">Заказы</h2>
          <select v-model="orderFilterStatus" class="admin__filter-select" @change="fetchOrders">
            <option v-for="s in orderStatuses" :key="s.value" :value="s.value">{{ s.label }}</option>
          </select>
        </div>

        <SkeletonAdminTable v-if="loading.orders" />

        <div v-else-if="orders.length === 0" class="admin__empty">Нет заказов</div>

        <div v-else class="admin__table-wrapper">
          <table class="admin__table" data-testid="orders-table">
            <thead>
              <tr>
                <th>№</th>
                <th>Пользователь</th>
                <th>Сумма</th>
                <th>Статус</th>
                <th>Доставка</th>
                <th>Трек-номер</th>
                <th>Дата</th>
                <th class="admin__table-actions">Действия</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="order in orders" :key="order.id">
                <td>{{ order.id }}</td>
                <td>{{ order.user_id }}</td>
                <td>{{ formatPrice(order.total_price) }}</td>
                <td>
                  <span class="admin__status-badge" :class="'admin__status-badge--' + order.status">
                    {{ statusLabel(order.status) }}
                  </span>
                </td>
                <td>{{ order.delivery_method?.name || '—' }}</td>
                <td>{{ order.tracking_number || '—' }}</td>
                <td>{{ formatShortDate(order.created_at) }}</td>
                <td class="admin__table-actions">
                  <button class="admin__icon-btn admin__icon-btn--edit" @click="openEditOrderModal(order)">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
                      <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
                    </svg>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Feature Flags Tab -->
    <div v-show="activeSectionTab === 'feature-flags'" class="admin__tab-panel" data-testid="admin-section-panel-feature-flags">
      <div class="admin__section">
        <div class="admin__section-header">
          <h2 class="admin__section-title">Фичатоглы</h2>
        </div>
        <div v-if="loading.featureFlags" class="admin__loading">Загрузка...</div>
        <div v-else-if="featureFlags.length === 0" class="admin__empty">Нет настроенных тоглов</div>
        <div v-else class="admin__table-wrapper">
          <table class="admin__table" data-testid="feature-flags-table">
            <thead>
              <tr>
                <th>Флаг</th>
                <th>Состояние</th>
                <th>Источник</th>
                <th class="admin__table-actions">Действия</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="flag in featureFlags" :key="flag.name">
                <td>{{ flag.name }}</td>
                <td>
                  <span class="admin__status-badge" :class="flag.enabled ? 'admin__status-badge--active' : 'admin__status-badge--inactive'">
                    {{ flag.enabled ? 'Включён' : 'Выключен' }}
                  </span>
                </td>
                <td>{{ sourceLabel(flag.source) }}</td>
                <td class="admin__table-actions">
                  <button
                    class="admin__btn admin__btn--small"
                    :class="flag.enabled ? 'admin__btn--danger' : 'admin__btn--success'"
                    @click="toggleFeatureFlag(flag.name, !flag.enabled)"
                    :disabled="loading.featureFlags"
                    :data-testid="`feature-flag-${flag.name}`"
                  >
                    {{ flag.enabled ? 'Выключить' : 'Включить' }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Category Modal -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <div class="modal__header">
          <h3>{{ isEdit ? 'Редактировать категорию' : 'Новая категория' }}</h3>
          <button class="modal__close" @click="closeModal">&times;</button>
        </div>
        <form class="modal__form" @submit.prevent="handleSubmit">
          <div class="field">
            <label class="field__label">Название <span class="required">*</span></label>
            <input v-model="form.name" class="field__input" placeholder="Например, Смартфоны" required data-testid="category-name-input" />
          </div>
          <div class="field">
            <label class="field__label">Описание</label>
            <textarea v-model="form.description" class="field__input field__input--textarea" rows="3" placeholder="Описание категории..." data-testid="category-description-input" />
          </div>
          <div class="field">
            <label class="field__label">Родительская категория</label>
            <select v-model="form.parent_id" class="field__input" data-testid="category-parent-select">
              <option :value="null">Без родителя</option>
              <option v-for="option in parentSelectOptions" :key="option.id" :value="option.id">
                {{ option.name }}
              </option>
            </select>
          </div>
          <div v-if="error" class="form-error">{{ error }}</div>
          <button type="submit" class="modal__submit" :disabled="submitting" data-testid="category-submit-btn">
            {{ submitting ? 'Сохранение...' : (isEdit ? 'Сохранить' : 'Создать') }}
          </button>
        </form>
      </div>
    </div>

    <!-- Delivery Modal -->
    <div v-if="showDeliveryModal" class="modal-overlay" @click.self="closeDeliveryModal">
      <div class="modal">
        <div class="modal__header">
          <h3>{{ isEditDelivery ? 'Редактировать доставку' : 'Новый способ доставки' }}</h3>
          <button class="modal__close" @click="closeDeliveryModal">&times;</button>
        </div>
        <form class="modal__form" @submit.prevent="handleDeliverySubmit">
          <div class="field">
            <label class="field__label">Название <span class="required">*</span></label>
            <input v-model="deliveryForm.name" class="field__input" placeholder="Например, Курьер" required data-testid="delivery-name-input" />
          </div>
          <div class="field">
            <label class="field__label">Описание</label>
            <textarea v-model="deliveryForm.description" class="field__input field__input--textarea" rows="2" placeholder="Описание..." data-testid="delivery-description-input" />
          </div>
          <div class="field">
            <label class="field__label">Цена (₽)</label>
            <input v-model.number="deliveryForm.base_price" type="number" min="0" step="0.01" class="field__input" placeholder="0" data-testid="delivery-price-input" />
          </div>
          <div class="field">
            <label class="field__label">Срок доставки</label>
            <input v-model="deliveryForm.estimated_days" class="field__input" placeholder="Например, 1-3 дня" data-testid="delivery-days-input" />
          </div>
          <div class="field">
            <label class="field__label">
              <input v-model="deliveryForm.is_active" type="checkbox" data-testid="delivery-active-checkbox" />
              Активен
            </label>
          </div>
          <div v-if="deliveryError" class="form-error">{{ deliveryError }}</div>
          <button type="submit" class="modal__submit" :disabled="submittingDelivery" data-testid="delivery-submit-btn">
            {{ submittingDelivery ? 'Сохранение...' : (isEditDelivery ? 'Сохранить' : 'Создать') }}
          </button>
        </form>
      </div>
    </div>

    <!-- Order Status Modal -->
    <div v-if="showOrderModal" class="modal-overlay" @click.self="closeOrderModal">
      <div class="modal">
        <div class="modal__header">
          <h3>Заказ №{{ editingOrder?.id }}</h3>
          <button class="modal__close" @click="closeOrderModal">&times;</button>
        </div>
        <div class="order-modal__tabs">
          <button
            class="order-modal__tab"
            :class="{ 'order-modal__tab--active': activeOrderModalTab === 'order' }"
            data-testid="order-modal-tab-order"
            @click="activeOrderModalTab = 'order'"
          >
            Заказ
          </button>
          <button
            v-if="editingOrder?.cdek_order"
            class="order-modal__tab"
            :class="{ 'order-modal__tab--active': activeOrderModalTab === 'cdek' }"
            data-testid="order-modal-tab-cdek"
            @click="activeOrderModalTab = 'cdek'"
          >
            CDEK
          </button>
        </div>
        <form v-show="activeOrderModalTab === 'order'" class="modal__form" @submit.prevent="handleOrderSubmit">
          <div class="field">
            <label class="field__label">Статус</label>
            <select v-model="orderForm.status" class="field__input">
              <option value="pending">Ожидает оплаты</option>
              <option value="paid">Оплачен</option>
              <option value="shipped">Отправлен</option>
              <option value="delivered">Доставлен</option>
              <option value="cancelled">Отменён</option>
            </select>
          </div>
          <div class="field">
            <label class="field__label">Трек-номер</label>
            <input v-model="orderForm.tracking_number" class="field__input" placeholder="Например, 1234567890" />
          </div>
          <button type="submit" class="modal__submit" :disabled="submittingOrderStatus">
            {{ submittingOrderStatus ? 'Сохранение...' : 'Сохранить' }}
          </button>
        </form>
        <div v-show="activeOrderModalTab === 'cdek'" class="order-modal__cdek" data-testid="order-modal-cdek-tab">
          <div class="info-list">
            <div class="info-row">
              <span class="info-label">cdek_uuid</span>
              <span class="info-value info-value--monospace">{{ editingOrder.cdek_order.cdek_uuid || '—' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">cdek_number</span>
              <span class="info-value info-value--monospace">{{ editingOrder.cdek_order.cdek_number || '—' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">tracking_number</span>
              <span class="info-value info-value--monospace">{{ editingOrder.cdek_order.tracking_number || '—' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">cdek_status</span>
              <span class="info-value">{{ editingOrder.cdek_order.cdek_status || '—' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">status_date_time</span>
              <span class="info-value">{{ editingOrder.cdek_order.status_date_time ? formatShortDate(editingOrder.cdek_order.status_date_time) : '—' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">status_city</span>
              <span class="info-value">{{ editingOrder.cdek_order.status_city || '—' }}</span>
            </div>
          </div>
          <div v-if="editingOrder.cdek_order.tracking_url" class="order-modal__cdek-track">
            <a
              :href="editingOrder.cdek_order.tracking_url"
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
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue';
import api from '@/services/api';
import { useToast } from '@/composables/useToast';
import { useCategories } from '@/composables/useCategories';
import SkeletonAdminTable from '@/components/SkeletonAdminTable.vue';

const { add: toast } = useToast();
const {
  allCategories,
  displayedCategories,
  rootCategories,
  activeTab: activeCategoryTab,
  searchQuery: categorySearchQuery,
  loading: categoryLoading,
  total: categoryTotal,
  fetchAllCategories,
  fetchDisplayedCategories,
  setActiveTab: setCategoryActiveTab,
  setSearchQuery: setCategorySearchQuery,
  loadMore: loadMoreCategories,
} = useCategories();

let categorySearchTimeout = null;
const CATEGORY_SEARCH_DEBOUNCE_MS = 300;

const onCategorySearchInput = (value) => {
  if (categorySearchTimeout) {
    clearTimeout(categorySearchTimeout);
  }
  categorySearchTimeout = setTimeout(() => {
    categorySearchTimeout = null;
    setCategorySearchQuery(value);
  }, CATEGORY_SEARCH_DEBOUNCE_MS);
};

onUnmounted(() => {
  if (categorySearchTimeout) {
    clearTimeout(categorySearchTimeout);
    categorySearchTimeout = null;
  }
});

// Section tabs
const sectionTabs = [
  { key: 'dashboard', label: 'Дашборд' },
  { key: 'users', label: 'Пользователи' },
  { key: 'categories', label: 'Категории' },
  { key: 'delivery', label: 'Способы доставки' },
  { key: 'orders', label: 'Заказы' },
  { key: 'feature-flags', label: 'Фичатоглы' },
];
const activeSectionTab = ref('dashboard');

// Loading states
const loading = ref({
  stats: false,
  ordersByDay: false,
  topProducts: false,
  users: false,
  delivery: false,
  orders: false,
  featureFlags: false,
});

// Data
const stats = ref({ total_orders: 0, total_revenue: 0, total_users: 0, total_products: 0 });
const ordersByDay = ref([]);
const topProducts = ref([]);
const users = ref([]);
const deliveryMethods = ref([]);
const orders = ref([]);
const featureFlags = ref([]);
const orderFilterStatus = ref('');
const orderStatuses = [
  { value: '', label: 'Все' },
  { value: 'pending', label: 'Ожидает оплаты' },
  { value: 'paid', label: 'Оплачен' },
  { value: 'shipped', label: 'Отправлен' },
  { value: 'delivered', label: 'Доставлен' },
  { value: 'cancelled', label: 'Отменён' },
];

// Modal
const showModal = ref(false);
const isEdit = ref(false);
const editingId = ref(null);
const error = ref('');
const submitting = ref(false);
const form = ref({ name: '', description: '', parent_id: null });
const submittingUser = ref(null);

// Delivery Modal
const showDeliveryModal = ref(false);
const isEditDelivery = ref(false);
const editingDeliveryId = ref(null);
const deliveryError = ref('');
const submittingDelivery = ref(false);
const deliveryForm = ref({ name: '', description: '', base_price: 0, estimated_days: '', is_active: true });

// Order Status Modal
const showOrderModal = ref(false);
const editingOrder = ref(null);
const orderForm = ref({ status: '', tracking_number: '' });
const submittingOrderStatus = ref(false);
const activeOrderModalTab = ref('order');

const cdekStatusHistory = computed(() => {
  const history = editingOrder.value?.cdek_order?.status_history || [];
  return [...history].sort((a, b) => {
    const aDate = a.status_date_time ? new Date(a.status_date_time) : 0;
    const bDate = b.status_date_time ? new Date(b.status_date_time) : 0;
    return bDate - aDate;
  });
});

// KPI computed
const kpiData = computed(() => [
  {
    key: 'orders',
    label: 'Всего заказов',
    value: stats.value.total_orders,
    bg: '#e8f0fe',
    icon: 'svg-orders',
  },
  {
    key: 'revenue',
    label: 'Выручка',
    value: formatPrice(stats.value.total_revenue),
    bg: '#e6f5e6',
    icon: 'svg-revenue',
  },
  {
    key: 'users',
    label: 'Пользователей',
    value: stats.value.total_users,
    bg: '#fff3e0',
    icon: 'svg-users',
  },
  {
    key: 'products',
    label: 'Товаров',
    value: stats.value.total_products,
    bg: '#f3e5f5',
    icon: 'svg-products',
  },
]);

const maxOrders = computed(() => {
  if (!ordersByDay.value.length) return 1;
  return Math.max(...ordersByDay.value.map((d) => d.orders), 1);
});

const parentSelectOptions = computed(() =>
  allCategories.value.filter((category) => category.id !== editingId.value)
);

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

function roleLabel(role) {
  const labels = { user: 'Покупатель', admin: 'Админ', supplier: 'Поставщик' };
  return labels[role] || role;
}

function statusLabel(status) {
  const labels = {
    pending: 'Ожидает оплаты',
    paid: 'Оплачен',
    shipped: 'Отправлен',
    delivered: 'Доставлен',
    cancelled: 'Отменён',
  };
  return labels[status] || status;
}

function sourceLabel(source) {
  const labels = {
    redis: 'Redis (ручной)',
    env: 'Переменная окружения',
    default: 'По умолчанию',
  };
  return labels[source] || source;
}

// Fetch data
async function fetchDashboard() {
  loading.value.stats = true;
  loading.value.ordersByDay = true;
  loading.value.topProducts = true;

  try {
    const { data } = await api.get('/admin/dashboard');
    stats.value = data;
  } catch {
    toast('Не удалось загрузить статистику', 'error');
  } finally {
    loading.value.stats = false;
  }

  try {
    const { data } = await api.get('/admin/orders-by-day');
    ordersByDay.value = data;
  } catch {
    toast('Не удалось загрузить график заказов', 'error');
  } finally {
    loading.value.ordersByDay = false;
  }

  try {
    const { data } = await api.get('/admin/top-products');
    topProducts.value = data;
  } catch {
    toast('Не удалось загрузить топ товаров', 'error');
  } finally {
    loading.value.topProducts = false;
  }
}

async function fetchUsers() {
  loading.value.users = true;
  try {
    const { data } = await api.get('/admin/users');
    users.value = data;
  } catch {
    toast('Не удалось загрузить пользователей', 'error');
  } finally {
    loading.value.users = false;
  }
}

async function toggleUser(userId) {
  submittingUser.value = userId;
  try {
    const { data } = await api.patch(`/admin/users/${userId}/toggle-active`);
    const idx = users.value.findIndex((u) => u.id === userId);
    if (idx !== -1) users.value[idx] = data;
    toast(data.is_active ? 'Пользователь разблокирован' : 'Пользователь заблокирован', 'success');
  } catch {
    toast('Ошибка при изменении статуса', 'error');
  } finally {
    submittingUser.value = null;
  }
}

const fetchCategoriesSection = async () => {
  try {
    await fetchAllCategories();
    await fetchDisplayedCategories();
  } catch {
    toast('Не удалось загрузить категории', 'error');
  }
};

const openCreateModal = () => {
  isEdit.value = false;
  editingId.value = null;
  form.value = { name: '', description: '', parent_id: null };
  error.value = '';
  showModal.value = true;
};

const openEditModal = (cat) => {
  isEdit.value = true;
  editingId.value = cat.id;
  form.value = { name: cat.name, description: cat.description || '', parent_id: cat.parent_id ?? null };
  error.value = '';
  showModal.value = true;
};

const closeModal = () => {
  showModal.value = false;
};

const handleSubmit = async () => {
  error.value = '';
  submitting.value = true;
  try {
    const payload = {
      name: form.value.name,
      description: form.value.description,
      parent_id: form.value.parent_id,
    };
    if (isEdit.value) {
      await api.put(`/categories/${editingId.value}`, payload);
      toast('Категория обновлена', 'success');
    } else {
      await api.post('/categories/', payload);
      toast('Категория создана', 'success');
    }
    closeModal();
    await fetchAllCategories();
    await fetchDisplayedCategories();
  } catch (err) {
    error.value = err.response?.data?.detail || 'Ошибка сохранения';
  } finally {
    submitting.value = false;
  }
};

const deleteCategory = async (id) => {
  if (!confirm('Удалить категорию?')) return;
  try {
    await api.delete(`/categories/${id}`);
    toast('Категория удалена', 'success');
    await fetchAllCategories();
    await fetchDisplayedCategories();
  } catch (err) {
    toast(err.response?.data?.detail || 'Ошибка удаления', 'error');
  }
};

// Delivery methods
const fetchDeliveryMethodsAdmin = async () => {
  loading.value.delivery = true;
  try {
    const { data } = await api.get('/delivery-methods/');
    deliveryMethods.value = data;
  } catch {
    toast('Не удалось загрузить способы доставки', 'error');
  } finally {
    loading.value.delivery = false;
  }
};

const openCreateDeliveryModal = () => {
  isEditDelivery.value = false;
  editingDeliveryId.value = null;
  deliveryForm.value = { name: '', description: '', base_price: 0, estimated_days: '', is_active: true };
  deliveryError.value = '';
  showDeliveryModal.value = true;
};

const openEditDeliveryModal = (method) => {
  isEditDelivery.value = true;
  editingDeliveryId.value = method.id;
  deliveryForm.value = {
    name: method.name,
    description: method.description || '',
    base_price: method.base_price,
    estimated_days: method.estimated_days || '',
    is_active: method.is_active,
  };
  deliveryError.value = '';
  showDeliveryModal.value = true;
};

const closeDeliveryModal = () => {
  showDeliveryModal.value = false;
};

const handleDeliverySubmit = async () => {
  deliveryError.value = '';
  submittingDelivery.value = true;
  try {
    const payload = {
      ...deliveryForm.value,
      base_price: Number(deliveryForm.value.base_price),
    };
    if (isEditDelivery.value) {
      await api.put(`/delivery-methods/${editingDeliveryId.value}`, payload);
      toast('Способ доставки обновлён', 'success');
    } else {
      await api.post('/delivery-methods/', payload);
      toast('Способ доставки создан', 'success');
    }
    closeDeliveryModal();
    fetchDeliveryMethodsAdmin();
  } catch (err) {
    deliveryError.value = err.response?.data?.detail || 'Ошибка сохранения';
  } finally {
    submittingDelivery.value = false;
  }
};

const deleteDeliveryMethod = async (id) => {
  if (!confirm('Удалить способ доставки?')) return;
  try {
    await api.delete(`/delivery-methods/${id}`);
    toast('Способ доставки удалён', 'success');
    fetchDeliveryMethodsAdmin();
  } catch (err) {
    toast(err.response?.data?.detail || 'Ошибка удаления', 'error');
  }
};

// Orders
const fetchOrders = async () => {
  loading.value.orders = true;
  try {
    const params = {};
    if (orderFilterStatus.value) params.status = orderFilterStatus.value;
    const { data } = await api.get('/admin/orders', { params });
    orders.value = data;
  } catch {
    toast('Не удалось загрузить заказы', 'error');
  } finally {
    loading.value.orders = false;
  }
};

const openEditOrderModal = (order) => {
  editingOrder.value = order;
  orderForm.value = {
    status: order.status,
    tracking_number: order.tracking_number || '',
  };
  activeOrderModalTab.value = 'order';
  showOrderModal.value = true;
};

const closeOrderModal = () => {
  showOrderModal.value = false;
  editingOrder.value = null;
  activeOrderModalTab.value = 'order';
};

const handleOrderSubmit = async () => {
  submittingOrderStatus.value = true;
  try {
    await api.put(`/admin/orders/${editingOrder.value.id}`, orderForm.value);
    toast('Заказ обновлён', 'success');
    closeOrderModal();
    fetchOrders();
  } catch (err) {
    toast(err.response?.data?.detail || 'Ошибка обновления заказа', 'error');
  } finally {
    submittingOrderStatus.value = false;
  }
};

const fetchFeatureFlags = async () => {
  loading.value.featureFlags = true;
  try {
    const { data } = await api.get('/admin/feature-flags');
    featureFlags.value = data;
  } catch {
    toast('Не удалось загрузить фичатоглы', 'error');
  } finally {
    loading.value.featureFlags = false;
  }
};

const toggleFeatureFlag = async (flagName, enabled) => {
  loading.value.featureFlags = true;
  try {
    const { data } = await api.patch(`/admin/feature-flags/${flagName}`, { enabled });
    const idx = featureFlags.value.findIndex((f) => f.name === flagName);
    if (idx !== -1) featureFlags.value[idx] = data;
    toast(`Флаг "${flagName}" ${data.enabled ? 'включён' : 'выключен'}`, 'success');
  } catch (err) {
    toast(err.response?.data?.detail || 'Ошибка при переключении флага', 'error');
  } finally {
    loading.value.featureFlags = false;
  }
};

onMounted(() => {
  fetchDashboard();
  fetchUsers();
  fetchCategoriesSection();
  fetchDeliveryMethodsAdmin();
  fetchOrders();
  fetchFeatureFlags();
});
</script>

<style scoped>
.admin {
  padding: 16px;
  min-height: 100vh;
  background: var(--color-bg);
}

.admin__title {
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 20px;
}

/* Tabs */
.admin__tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  overflow-x: auto;
}

.admin__tab {
  padding: 8px 16px;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-white);
  color: var(--color-text-secondary);
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
  cursor: pointer;
}

.admin__tab--active {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

/* KPI */
.admin__kpi-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

@media (min-width: 768px) {
  .admin__kpi-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

.admin__kpi-card {
  background: var(--color-bg-white);
  border-radius: 16px;
  padding: 16px;
  display: flex;
  flex-direction: column;
}

.admin__kpi-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-primary);
  margin-bottom: 10px;
}

.admin__kpi-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text);
  line-height: 1.2;
}

.admin__kpi-label {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-top: 4px;
}

/* Charts row */
.admin__charts-row {
  display: grid;
  gap: 16px;
  margin-bottom: 16px;
}

@media (min-width: 1024px) {
  .admin__charts-row {
    grid-template-columns: 2fr 1fr;
  }
}

/* Chart */
.admin__chart {
  padding: 8px 0;
}

.admin__chart-bars {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 8px;
  height: 160px;
  padding-bottom: 24px;
  position: relative;
}

.admin__chart-bar-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
}

.admin__chart-bar-track {
  width: 100%;
  height: 140px;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  background: var(--color-bg);
  border-radius: 6px 6px 0 0;
  overflow: hidden;
}

.admin__chart-bar {
  width: 60%;
  background: var(--color-primary);
  border-radius: 6px 6px 0 0;
  min-height: 4px;
  transition: height 0.3s ease;
}

.admin__chart-label {
  position: absolute;
  bottom: 0;
  font-size: 11px;
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.admin__chart-tooltip {
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

.admin__chart-bar-wrap:hover .admin__chart-tooltip {
  opacity: 1;
}

/* Top Products */
.admin__top-products {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.admin__top-product {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  border-radius: 12px;
  background: var(--color-bg);
}

.admin__top-product-rank {
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

.admin__top-product-info {
  flex: 1;
  min-width: 0;
}

.admin__top-product-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.admin__top-product-meta {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-top: 2px;
}

.admin__top-product-revenue {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  white-space: nowrap;
}

/* Section */
.admin__section {
  background: var(--color-bg-white);
  border-radius: 16px;
  padding: 16px;
}

.admin__section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.admin__section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
}

.admin__loading,
.admin__empty {
  text-align: center;
  padding: 40px 20px;
  color: var(--color-text-secondary);
}

/* Table */
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

/* Badges */
.admin__role-badge {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
}

.admin__role-badge--admin {
  background: #e8f0fe;
  color: #1a73e8;
}

.admin__role-badge--supplier {
  background: #fff3e0;
  color: #e65100;
}

.admin__role-badge--user {
  background: #e6f5e6;
  color: #2e7d32;
}

.admin__status-badge {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
}

.admin__status-badge--active {
  background: #e6f5e6;
  color: #2e7d32;
}

.admin__status-badge--inactive {
  background: #fff0f0;
  color: #c62828;
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

.admin__filter-select {
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-white);
  color: var(--color-text);
  font-size: 14px;
  cursor: pointer;
}

/* Buttons */
.admin__btn {
  padding: 10px 16px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  border: none;
  cursor: pointer;
}

.admin__btn--primary {
  background: var(--color-primary);
  color: #fff;
}

.admin__btn--small {
  padding: 6px 12px;
  font-size: 13px;
}

.admin__btn--danger {
  background: #fff0f0;
  color: var(--color-danger);
}

.admin__btn--success {
  background: #e6f5e6;
  color: #2e7d32;
}

.admin__btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.admin__icon-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-right: 6px;
  cursor: pointer;
}

.admin__icon-btn--edit {
  background: #e8f0fe;
  color: var(--color-primary);
}

.admin__icon-btn--delete {
  background: #fff0f0;
  color: var(--color-danger);
}

/* Modal */
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
  max-width: 480px;
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

.field__input--textarea {
  resize: vertical;
  min-height: 80px;
}

.required {
  color: var(--color-danger);
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

/* Category tabs */
.admin__category-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  overflow-x: auto;
  padding-bottom: 4px;
}

.admin__category-tab {
  padding: 8px 16px;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-white);
  color: var(--color-text-secondary);
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
  cursor: pointer;
}

.admin__category-tab--active {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

.admin__category-search {
  margin-bottom: 16px;
}

.admin__category-search .field__input {
  max-width: 400px;
}

.admin__load-more {
  display: block;
  width: 100%;
  margin-top: 12px;
  padding: 12px;
  border-radius: 12px;
  background: var(--color-bg-white);
  color: var(--color-primary);
  font-size: 15px;
  font-weight: 500;
  border: 1px solid var(--color-border);
  cursor: pointer;
  transition: background 0.15s;
}

.admin__load-more:hover {
  background: #e8f0fe;
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

.order-modal__cdek .info-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.order-modal__cdek .info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  font-size: 14px;
}

.order-modal__cdek .info-label {
  color: var(--color-text-secondary);
}

.order-modal__cdek .info-value {
  color: var(--color-text);
  font-weight: 500;
  text-align: right;
  word-break: break-all;
}

.order-modal__cdek .info-value--monospace {
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
</style>
