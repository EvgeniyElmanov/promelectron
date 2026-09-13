<template>
  <div class="supplier-products" data-testid="supplier-products">
    <div class="supplier-products__header">
      <h1 class="supplier-products__title">Мои товары</h1>
      <AppButton size="sm" data-testid="supplier-product-add" @click="openCreateModal">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="12" y1="5" x2="12" y2="19"/>
          <line x1="5" y1="12" x2="19" y2="12"/>
        </svg>
        Добавить
      </AppButton>
    </div>

    <div v-if="loading" class="supplier-products__list">
      <div class="supplier-product-card" v-for="i in 3" :key="'sk' + i">
        <div style="width: 100%; height: 80px; border-radius: 14px; background: linear-gradient(90deg, var(--color-bg) 25%, #e8ecf1 50%, var(--color-bg) 75%); background-size: 200% 100%; animation: shimmer 1.5s infinite;" />
      </div>
    </div>

    <div v-else-if="products.length === 0" class="supplier-products__empty">
      <p>У вас пока нет товаров</p>
      <AppButton data-testid="supplier-product-add-empty" @click="openCreateModal">
        Добавить первый товар
      </AppButton>
    </div>

    <div v-else class="supplier-products__list">
      <div
        v-for="product in products"
        :key="product.id"
        class="supplier-product-card"
        :class="{ 'supplier-product-card--inactive': !product.is_active }"
        data-testid="supplier-product-card"
      >
        <div class="supplier-product-card__info">
          <p class="supplier-product-card__name">{{ product.name }}</p>
          <p class="supplier-product-card__price">{{ formatPrice(product.price) }}</p>
          <p class="supplier-product-card__stock">В наличии: {{ product.stock }}</p>
          <span v-if="!product.is_active" class="supplier-product-card__badge">Неактивен</span>
        </div>
        <div class="supplier-product-card__actions">
          <AppButton variant="secondary" size="sm" aria-label="Редактировать" :data-testid="`supplier-product-edit-${product.id}`" @click="openEditModal(product)">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
          </AppButton>
          <AppButton variant="danger" size="sm" aria-label="Удалить" :data-testid="`supplier-product-delete-${product.id}`" @click="deleteProduct(product.id)">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
            </svg>
          </AppButton>
        </div>
      </div>
    </div>

    <ProductFormModal
      v-if="showModal"
      :product="editingProduct"
      @close="closeModal"
      @saved="fetchProducts"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import api from '@/services/api';
import { useToast } from '@/composables/useToast';
import ProductFormModal from '@/components/ProductFormModal.vue';
import AppButton from '@/components/ui/AppButton.vue';

const products = ref([]);
const loading = ref(false);
const showModal = ref(false);
const editingProduct = ref(null);
const { add: toast } = useToast();

const formatPrice = (price) => {
  return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(price);
};

const fetchProducts = async () => {
  loading.value = true;
  try {
    const { data } = await api.get('/products/my');
    products.value = data;
  } catch {
    toast('Не удалось загрузить товары', 'error');
  } finally {
    loading.value = false;
  }
};

const openCreateModal = () => {
  editingProduct.value = null;
  showModal.value = true;
};

const openEditModal = (product) => {
  editingProduct.value = product;
  showModal.value = true;
};

const closeModal = () => {
  showModal.value = false;
  editingProduct.value = null;
};

const deleteProduct = async (id) => {
  if (!confirm('Удалить товар?')) return;
  try {
    await api.delete(`/products/${id}`);
    toast('Товар удалён', 'success');
    fetchProducts();
  } catch (err) {
    toast(err.response?.data?.detail || 'Ошибка удаления', 'error');
  }
};

onMounted(fetchProducts);
</script>

<style scoped>
.supplier-products {
  padding: 16px;
  min-height: 100vh;
  background: var(--color-bg);
}

.supplier-products__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.supplier-products__title {
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text);
}

.supplier-products__loading,
.supplier-products__empty {
  text-align: center;
  padding: 40px 20px;
  color: var(--color-text-secondary);
}

.supplier-products__empty .app-button {
  margin-top: 12px;
}

.supplier-products__list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.supplier-product-card {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 14px 16px;
  border-radius: 14px;
  background: var(--color-bg-white);
  gap: 12px;
}

.supplier-product-card--inactive {
  opacity: 0.7;
}

.supplier-product-card__info {
  flex: 1;
  min-width: 0;
}

.supplier-product-card__name {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.supplier-product-card__price {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-primary);
  margin-bottom: 2px;
}

.supplier-product-card__stock {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.supplier-product-card__badge {
  display: inline-block;
  margin-top: 6px;
  padding: 2px 8px;
  border-radius: 6px;
  background: #f0f0f0;
  color: #888;
  font-size: 12px;
}

.supplier-product-card__actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.supplier-product-card__actions .app-button {
  padding: 0 var(--space-3);
}
</style>
