<template>
  <div class="product-detail">
    <div class="product-detail__header">
      <button class="product-detail__back" data-testid="pdp-back-button" @click="$router.back()">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path d="M15 18l-6-6 6-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
      <h1 class="product-detail__title" data-testid="pdp-title">{{ product.name }}</h1>
      <button
        class="product-detail__fav-btn"
        :class="{ 'product-detail__fav-btn--active': isFavorite }"
        data-testid="pdp-favorite-button"
        @click="toggleFavorite"
      >
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
          <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
    </div>

    <div class="product-detail__main">
      <!-- Left: Gallery -->
      <div class="product-detail__gallery">
        <div
          class="product-detail__image"
          :style="{ background: placeholderBg }"
          data-testid="pdp-image"
        >
          <span class="product-detail__image-letter">{{ product.name?.charAt(0) }}</span>
        </div>
      </div>

      <!-- Right: Info -->
      <div class="product-detail__info">
        <div class="product-detail__price" data-testid="pdp-price">{{ formattedPrice }} ₽</div>

        <div class="product-detail__rating" v-if="product.reviews_count > 0" data-testid="pdp-rating">
          <span class="product-detail__stars">
            <svg v-for="n in 5" :key="n" width="16" height="16" viewBox="0 0 24 24" :fill="n <= Math.round(product.average_rating) ? '#FFB800' : 'none'" :stroke="n <= Math.round(product.average_rating) ? '#FFB800' : '#ccc'" stroke-width="2">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
            </svg>
          </span>
          <span class="product-detail__rating-text">{{ product.average_rating }} · {{ product.reviews_count }} отзывов</span>
        </div>

        <div class="product-detail__actions">
          <button
            class="product-detail__cart-btn"
            data-testid="pdp-add-to-cart"
            :disabled="cartLoading"
            @click="addToCart"
          >
            {{ cartLoading ? '...' : 'В корзину' }}
          </button>
        </div>

        <div class="product-detail__section" v-if="product.description" data-testid="pdp-description">
          <h2 class="product-detail__section-title">Описание</h2>
          <p class="product-detail__description">{{ product.description }}</p>
        </div>
      </div>
    </div>

    <!-- Reviews Section -->
    <div class="product-detail__reviews-wrapper">
      <div class="product-detail__section" data-testid="pdp-reviews-section">
        <h2 class="product-detail__section-title">Отзывы</h2>

        <div v-if="isAuthenticated" class="product-detail__review-form">
          <div class="product-detail__rating-input">
            <button
              v-for="n in 5"
              :key="n"
              class="product-detail__star-btn"
              :class="{ 'product-detail__star-btn--active': n <= newRating }"
              @click="newRating = n"
            >
              <svg width="24" height="24" viewBox="0 0 24 24" :fill="n <= newRating ? '#FFB800' : 'none'" stroke="#ccc" stroke-width="2">
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
              </svg>
            </button>
          </div>
          <textarea
            v-model="newReviewText"
            class="product-detail__review-textarea"
            placeholder="Поделитесь впечатлениями..."
            rows="3"
          />
          <button
            class="product-detail__review-submit"
            :disabled="reviewLoading || newRating === 0"
            data-testid="pdp-submit-review"
            @click="submitReview"
          >
            {{ reviewLoading ? '...' : 'Оставить отзыв' }}
          </button>
        </div>

        <div v-if="reviews.length === 0" class="product-detail__empty" data-testid="pdp-no-reviews">
          Пока нет отзывов
        </div>

        <div v-else class="product-detail__reviews-list">
          <div
            v-for="review in reviews"
            :key="review.id"
            class="product-detail__review"
            data-testid="pdp-review-item"
          >
            <div class="product-detail__review-header">
              <span class="product-detail__review-stars">
                <svg v-for="n in 5" :key="n" width="14" height="14" viewBox="0 0 24 24" :fill="n <= review.rating ? '#FFB800' : 'none'" :stroke="n <= review.rating ? '#FFB800' : '#ccc'" stroke-width="2">
                  <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                </svg>
              </span>
              <span class="product-detail__review-date">{{ formatDate(review.created_at) }}</span>
            </div>
            <p v-if="review.text" class="product-detail__review-text">{{ review.text }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import api from '@/services/api';
import { useAuth } from '@/composables/useAuth';
import { useToast } from '@/composables/useToast';

const route = useRoute();
const router = useRouter();
const { isAuthenticated } = useAuth();
const { add: toast } = useToast();

const product = ref({});
const reviews = ref([]);
const isFavorite = ref(false);
const loading = ref(false);
const cartLoading = ref(false);
const reviewLoading = ref(false);
const newRating = ref(0);
const newReviewText = ref('');

const productId = computed(() => Number(route.params.id));

const placeholderColors = [
  '#E3F2FD', '#FCE4EC', '#E8F5E9', '#FFF3E0',
  '#F3E5F5', '#E0F7FA', '#FFF8E1', '#EDE7F6',
];

const placeholderBg = computed(() =>
  placeholderColors[product.value.id % placeholderColors.length] || '#E3F2FD'
);

const formattedPrice = computed(() => {
  if (!product.value.price) return '0';
  return Number(product.value.price).toLocaleString('ru-RU');
});

const fetchProduct = async () => {
  loading.value = true;
  try {
    const { data } = await api.get(`/products/${productId.value}/detail`);
    product.value = data;
    reviews.value = data.reviews || [];
    isFavorite.value = data.is_favorite || false;
  } catch (err) {
    if (err?.response?.status === 404) {
      router.push('/');
    }
  } finally {
    loading.value = false;
  }
};

const toggleFavorite = async () => {
  if (!isAuthenticated.value) {
    router.push('/login');
    return;
  }
  try {
    if (isFavorite.value) {
      await api.delete(`/favorites/remove/${productId.value}`);
      isFavorite.value = false;
      toast('Удалено из избранного', 'info');
    } else {
      await api.post(`/favorites/add/${productId.value}`);
      isFavorite.value = true;
      toast('Добавлено в избранное', 'success');
    }
  } catch {
    toast('Не удалось обновить избранное', 'error');
  }
};

const addToCart = async () => {
  if (cartLoading.value) return;
  cartLoading.value = true;
  try {
    await api.post('/cart/add', { product_id: productId.value, quantity: 1 });
    toast('Добавлено в корзину', 'success');
  } catch (err) {
    if (err?.response?.status === 401) {
      router.push('/login');
      return;
    }
    toast('Не удалось добавить в корзину', 'error');
  } finally {
    cartLoading.value = false;
  }
};

const submitReview = async () => {
  if (newRating.value === 0 || reviewLoading.value) return;
  reviewLoading.value = true;
  try {
    await api.post(`/reviews/product/${productId.value}`, {
      rating: newRating.value,
      text: newReviewText.value,
    });
    newRating.value = 0;
    newReviewText.value = '';
    await fetchProduct();
    toast('Отзыв опубликован', 'success');
  } catch (err) {
    if (err?.response?.status === 401) {
      router.push('/login');
      return;
    }
    toast('Не удалось опубликовать отзыв', 'error');
  } finally {
    reviewLoading.value = false;
  }
};

const formatDate = (dateStr) => {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });
};

onMounted(fetchProduct);
</script>

<style scoped>
.product-detail {
  background: var(--color-bg);
  min-height: 100vh;
  padding-bottom: 20px;
}

.product-detail__header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: var(--color-bg-white);
  position: sticky;
  top: 0;
  z-index: 50;
  border-bottom: 1px solid var(--color-border);
}

.product-detail__back {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  color: var(--color-text);
  flex-shrink: 0;
}

.product-detail__title {
  flex: 1;
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.product-detail__fav-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  color: var(--color-text-secondary);
  flex-shrink: 0;
  transition: color 0.15s;
}

.product-detail__fav-btn--active {
  color: #ff4242;
}

.product-detail__main {
  display: flex;
  flex-direction: column;
}

.product-detail__gallery {
  background: var(--color-bg-white);
  padding: 16px;
}

.product-detail__image {
  aspect-ratio: 1;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.product-detail__image-letter {
  font-size: 80px;
  font-weight: 700;
  color: rgba(0, 0, 0, 0.12);
  user-select: none;
}

.product-detail__info {
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.product-detail__price {
  font-size: 28px;
  font-weight: 700;
  color: var(--color-text);
  line-height: 1;
}

.product-detail__rating {
  display: flex;
  align-items: center;
  gap: 8px;
}

.product-detail__stars {
  display: flex;
  gap: 2px;
}

.product-detail__rating-text {
  font-size: 14px;
  color: var(--color-text-secondary);
}

.product-detail__actions {
  display: flex;
  gap: 10px;
}

.product-detail__cart-btn {
  flex: 1;
  padding: 14px;
  border-radius: 12px;
  background: var(--color-primary);
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  transition: opacity 0.15s;
}

.product-detail__cart-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.product-detail__section {
  background: var(--color-bg-white);
  border-radius: 12px;
  padding: 14px;
}

.product-detail__section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 10px;
}

.product-detail__description {
  font-size: 14px;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.product-detail__reviews-wrapper {
  padding: 0 12px;
}

.product-detail__review-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--color-border);
}

.product-detail__rating-input {
  display: flex;
  gap: 4px;
}

.product-detail__star-btn {
  padding: 2px;
}

.product-detail__review-textarea {
  width: 100%;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  font-size: 14px;
  resize: vertical;
  font-family: inherit;
}

.product-detail__review-textarea:focus {
  outline: none;
  border-color: var(--color-primary);
}

.product-detail__review-submit {
  align-self: flex-start;
  padding: 10px 20px;
  border-radius: 10px;
  background: var(--color-primary);
  color: #fff;
  font-size: 14px;
  font-weight: 500;
}

.product-detail__review-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.product-detail__empty {
  text-align: center;
  padding: 20px;
  color: var(--color-text-secondary);
  font-size: 14px;
}

.product-detail__reviews-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.product-detail__review {
  padding: 10px;
  background: var(--color-bg);
  border-radius: 10px;
}

.product-detail__review-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.product-detail__review-stars {
  display: flex;
  gap: 2px;
}

.product-detail__review-date {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.product-detail__review-text {
  font-size: 14px;
  color: var(--color-text);
  line-height: 1.4;
}

/* Desktop Layout */
@media (min-width: 768px) {
  .product-detail__main {
    flex-direction: row;
    gap: 20px;
    padding: 20px;
  }
  
  .product-detail__gallery {
    flex: 0 0 45%;
    max-width: 500px;
    padding: 24px;
    border-radius: 16px;
  }
  
  .product-detail__image {
    aspect-ratio: 4 / 3;
  }
  
  .product-detail__info {
    flex: 1;
    padding: 0;
  }
  
  .product-detail__price {
    font-size: 32px;
  }
  
  .product-detail__reviews-wrapper {
    padding: 0 20px;
  }
}
</style>
