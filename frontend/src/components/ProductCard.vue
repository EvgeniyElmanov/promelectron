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
      <div class="product-card__badges">
        <AppBadge
          v-if="isOutOfStock"
          variant="out-of-stock"
          data-testid="out-of-stock-badge"
        >Нет в наличии</AppBadge>
        <template v-else>
          <span v-if="discountPercent" class="product-card__badge product-card__badge--sale" data-testid="sale-badge">−{{ discountPercent }}%</span>
          <span v-if="product.is_hit" class="product-card__badge product-card__badge--hit" data-testid="hit-badge">ХИТ</span>
          <span v-else-if="product.is_new" class="product-card__badge product-card__badge--new" data-testid="new-badge">НОВИНКА</span>
        </template>
      </div>
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
      <div
        v-if="hasRating"
        class="product-card__rating"
        data-testid="product-rating"
      >
        <span class="product-card__star" aria-hidden="true">★</span>
        {{ formattedRating }}
        <span class="product-card__reviews">({{ product.reviews_count }})</span>
      </div>
      <div v-if="product.brand" class="product-card__brand" data-testid="product-brand">{{ product.brand }}</div>
      <div class="product-card__name" data-testid="product-name">{{ product.name }}</div>
      <div
        class="product-card__stock"
        :class="{ 'product-card__stock--out': isOutOfStock }"
        data-testid="stock-status"
      >
        {{ isOutOfStock ? 'Нет в наличии' : 'В наличии' }}
      </div>
      <div class="product-card__price-row">
        <div class="product-card__price" data-testid="product-price">{{ formattedPrice }} ₽</div>
        <div
          v-if="formattedOldPrice"
          class="product-card__old-price"
          data-testid="product-old-price"
        >{{ formattedOldPrice }} ₽</div>
      </div>
      <div class="product-card__actions">
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
        <button
          class="product-card__compare"
          data-testid="compare-button"
          title="Сравнение скоро появится"
          aria-disabled="true"
          @click.stop
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M10 3H4a1 1 0 00-1 1v16a1 1 0 001 1h6"/>
            <path d="M14 21h6a1 1 0 001-1V4a1 1 0 00-1-1h-6"/>
            <line x1="12" y1="3" x2="12" y2="21"/>
          </svg>
        </button>
      </div>
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

// §13 / D-03–D-04: бренд, рейтинг, старая цена и бейджи рендерятся только при
// наличии optional-полей API — без них карточка выглядит как раньше.
const formattedOldPrice = computed(() =>
  props.product.old_price ? formatPrice(props.product.old_price) : null
);

const discountPercent = computed(() => {
  const { price, old_price: oldPrice } = props.product;
  if (!price || !oldPrice || oldPrice <= price) return null;
  return Math.round((1 - price / oldPrice) * 100);
});

const hasRating = computed(() =>
  typeof props.product.average_rating === 'number' && props.product.reviews_count > 0
);

const formattedRating = computed(() =>
  hasRating.value ? props.product.average_rating.toFixed(1) : ''
);

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

.product-card__badges {
  position: absolute;
  top: 8px;
  left: 8px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.product-card__badge {
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-semibold);
  line-height: 1.4;
  color: var(--color-white);
}

.product-card__badge--sale {
  background: var(--color-danger);
}

.product-card__badge--hit {
  background: var(--color-primary);
}

.product-card__badge--new {
  background: var(--color-success);
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

.product-card__rating {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--font-size-caption);
  font-weight: var(--font-weight-medium);
  color: var(--color-text);
}

.product-card__star {
  color: var(--color-star);
}

.product-card__reviews {
  color: var(--color-text-muted);
  font-weight: var(--font-weight-regular);
}

.product-card__brand {
  font-size: var(--font-size-caption);
  color: var(--color-text-muted);
}

.product-card__stock {
  font-size: var(--font-size-caption);
  color: var(--color-success);
}

.product-card__stock--out {
  color: var(--color-danger);
}

.product-card__price-row {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
}

.product-card__old-price {
  font-size: var(--font-size-caption);
  color: var(--color-text-muted);
  text-decoration: line-through;
}

.product-card__actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-top: 4px;
}

.product-card__compare {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-white);
  color: var(--color-text-muted);
  opacity: 0.6;
  cursor: not-allowed;
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

.product-card__cart-btn.product-card__cart-btn--in-cart,
.product-card__cart-btn.product-card__cart-btn--in-cart:hover {
  background: var(--color-success);
  color: var(--color-white);
}

.product-card__actions .product-card__cart-btn {
  margin-top: 0;
  flex: 1;
}

@media (max-width: 767px) {
  .product-card__cart-btn {
    min-height: 44px;
  }
}
</style>
