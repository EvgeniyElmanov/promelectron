<template>
  <div class="product-card" data-testid="product-card" @click="goToProduct">
    <div
      class="product-card__image"
      :style="{ background: placeholderBg }"
    >
      <span class="product-card__image-letter">{{ product.name.charAt(0) }}</span>
      <button
        class="product-card__heart"
        :class="{ 'product-card__heart--active': isFavorite }"
        data-testid="favorite-button"
        @click.stop="toggleFavorite"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
          <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
    </div>
    <div class="product-card__body">
      <div class="product-card__price" data-testid="product-price">{{ formattedPrice }} ₽</div>
      <div class="product-card__name" data-testid="product-name">{{ product.name }}</div>
      <button
        class="product-card__cart-btn"
        data-testid="add-to-cart-button"
        :disabled="isLoading"
        @click.stop="addToCart"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4H6z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <line x1="3" y1="6" x2="21" y2="6" stroke="currentColor" stroke-width="2"/>
          <path d="M16 10a4 4 0 01-8 0" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
        <span>{{ isLoading ? '...' : 'В корзину' }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/services/api';
import { useAuth } from '@/composables/useAuth';

const props = defineProps({
  product: { type: Object, required: true },
});

const router = useRouter();
const { isAuthenticated } = useAuth();

const isLoading = ref(false);
const isFavorite = ref(props.product.is_favorite || false);

const placeholderColors = [
  '#E3F2FD', '#FCE4EC', '#E8F5E9', '#FFF3E0',
  '#F3E5F5', '#E0F7FA', '#FFF8E1', '#EDE7F6',
];

const placeholderBg = computed(() =>
  placeholderColors[props.product.id % placeholderColors.length]
);

const formattedPrice = computed(() => {
  const parts = props.product.price.toFixed(0);
  return Number(parts).toLocaleString('ru-RU');
});

const goToProduct = () => {
  router.push(`/product/${props.product.id}`);
};

const toggleFavorite = async () => {
  if (!isAuthenticated.value) {
    router.push('/login');
    return;
  }
  try {
    if (isFavorite.value) {
      await api.delete(`/favorites/remove/${props.product.id}`);
      isFavorite.value = false;
    } else {
      await api.post(`/favorites/add/${props.product.id}`);
      isFavorite.value = true;
    }
  } catch {
    // silently fail
  }
};

const addToCart = async () => {
  if (isLoading.value) return;
  isLoading.value = true;
  try {
    await api.post('/cart/add', { product_id: props.product.id, quantity: 1 });
  } catch (err) {
    if (err?.response?.status === 401) {
      router.push('/login');
      return;
    }
  } finally {
    isLoading.value = false;
  }
};
</script>

<style scoped>
.product-card {
  background: var(--color-bg-white);
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.product-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.product-card__image {
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.product-card__image-letter {
  font-size: 40px;
  font-weight: 700;
  color: rgba(0, 0, 0, 0.12);
  user-select: none;
}

.product-card__heart {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-secondary);
  transition: color 0.15s;
  cursor: pointer;
}

.product-card__heart--active {
  color: #ff4242;
}

.product-card__body {
  padding: 8px 10px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.product-card__price {
  font-size: 17px;
  font-weight: 700;
  color: var(--color-text);
  line-height: 1;
}

.product-card__name {
  font-size: 13px;
  color: var(--color-text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 34px;
}

.product-card__cart-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 6px 0;
  margin-top: 4px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  background: var(--color-primary-light);
  color: var(--color-primary);
  transition: background 0.15s;
  cursor: pointer;
}

.product-card__cart-btn:hover {
  background: #d4e4ff;
}

.product-card__cart-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
