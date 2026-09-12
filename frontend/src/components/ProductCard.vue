<template>
  <div class="product-card" data-testid="product-card" :data-product-id="product.id" @click="goToProduct">
    <div
      class="product-card__image"
      :style="product.images?.length ? {} : { background: placeholderBg }"
    >
      <img
        v-if="product.images?.length"
        :src="getImageUrl(product.images[0], 'small')"
        :srcset="`${getImageUrl(product.images[0], 'small')} 1x, ${getImageUrl(product.images[0], 'medium')} 2x`"
        class="product-card__img"
        alt=""
        width="400"
        height="400"
        decoding="async"
        loading="lazy"
      />
      <span v-else class="product-card__image-letter">{{ product.name.charAt(0) }}</span>
      <AppBadge
        v-if="isOutOfStock"
        variant="out-of-stock"
        class="product-card__badge"
        data-testid="out-of-stock-badge"
      >Нет в наличии</AppBadge>
      <button
        class="product-card__heart"
        :class="{ 'product-card__heart--active': isFavorite }"
        data-testid="favorite-button"
        @click.stop="toggleFavorite"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" :fill="isFavorite ? 'currentColor' : 'none'">
          <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
    </div>
    <div class="product-card__body">
      <div class="product-card__price" data-testid="product-price">{{ formattedPrice }} ₽</div>
      <div class="product-card__name" data-testid="product-name">{{ product.name }}</div>
      <AppButton
        size="sm"
        block
        class="product-card__cart-btn"
        :class="{ 'product-card__cart-btn--in-cart': inCartQty > 0 && !isOutOfStock }"
        data-testid="add-to-cart-button"
        :disabled="isLoading || isOutOfStock"
        @click.stop="addToCart"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4H6z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <line x1="3" y1="6" x2="21" y2="6" stroke="currentColor" stroke-width="2"/>
          <path d="M16 10a4 4 0 01-8 0" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
        <span>{{ isOutOfStock ? 'Нет в наличии' : (isLoading ? '...' : (inCartQty > 0 ? `В корзине · ${inCartQty}` : 'В корзину')) }}</span>
      </AppButton>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/services/api';
import { useAuth } from '@/composables/useAuth';
import { useCart } from '@/composables/useCart';
import { useToast } from '@/composables/useToast';
import { getImageUrl } from '@/composables/useImageUrl';
import { formatPrice } from '@/utils/price';
import { getPlaceholderBg } from '@/utils/placeholderColors';
import AppButton from '@/components/ui/AppButton.vue';
import AppBadge from '@/components/ui/AppBadge.vue';

const props = defineProps({
  product: { type: Object, required: true },
});

const emit = defineEmits(['removed']);

const router = useRouter();
const { isAuthenticated } = useAuth();
const { add: toast } = useToast();
const { addToCart: addToCartStore, getQuantityInCart } = useCart();

const isLoading = ref(false);
const isFavorite = ref(props.product.is_favorite || false);

const inCartQty = computed(() => getQuantityInCart(props.product.id));

const placeholderBg = computed(() => getPlaceholderBg(props.product.id));

const formattedPrice = computed(() => formatPrice(props.product.price));

const isOutOfStock = computed(() => props.product.stock === 0);

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
      emit('removed', props.product.id);
    } else {
      await api.post(`/favorites/add/${props.product.id}`);
      isFavorite.value = true;
    }
  } catch {
    toast('Не удалось обновить избранное', 'error');
  }
};

const addToCart = async () => {
  if (inCartQty.value > 0) {
    router.push('/cart');
    return;
  }
  if (isLoading.value) return;
  isLoading.value = true;
  try {
    await addToCartStore(props.product.id, 1, props.product);
  } catch {
    toast('Не удалось добавить в корзину', 'error');
  } finally {
    isLoading.value = false;
  }
};
</script>

<style scoped>
.product-card {
  background: var(--color-bg-white);
  border-radius: var(--radius-lg);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  cursor: pointer;
  box-shadow: var(--shadow-card);
  transition: transform 0.2s, box-shadow 0.2s;
}

.product-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-card-hover);
}

.product-card__image {
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.product-card__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
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

.product-card__heart svg {
  transition: fill 0.15s ease;
}

.product-card__heart--active {
  color: var(--color-danger);
}

.product-card__heart--active svg {
  animation: heart-pop 0.25s ease;
}

@keyframes heart-pop {
  0% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.25);
  }
  100% {
    transform: scale(1);
  }
}

.product-card__badge {
  position: absolute;
  top: 8px;
  left: 8px;
}

/* Touch target ≥40px без изменения визуального размера (прозрачный хит-бокс) */
@media (max-width: 767px) {
  .product-card__heart::after {
    content: '';
    position: absolute;
    inset: -4px;
  }
}

.product-card__body {
  padding: 8px 10px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.product-card__price {
  font-size: var(--font-size-body-lg);
  font-weight: var(--font-weight-bold);
  color: var(--color-text);
  line-height: 1;
}

.product-card__name {
  font-size: var(--font-size-body-sm);
  color: var(--color-text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 34px;
}

.product-card__cart-btn {
  margin-top: 4px;
}

.product-card__cart-btn.product-card__cart-btn--in-cart,
.product-card__cart-btn.product-card__cart-btn--in-cart:hover {
  background: var(--color-success);
  color: var(--color-white);
}

@media (max-width: 767px) {
  .product-card__cart-btn {
    min-height: 44px;
  }
}
</style>
