<template>
  <div class="cart" data-testid="cart-page">
    <h2 data-testid="cart-title">Корзина</h2>
    <div v-if="loading" class="loading">
      Загрузка корзины...
    </div>
    <div v-else-if="cart.items && cart.items.length > 0">
      <div class="cart-items">
        <div v-for="item in cart.items" :key="item.id" class="cart-item" data-testid="cart-item">
          <div class="item-details">
            <h3>{{ item.product?.name || 'Товар' }}</h3>
            <p>{{ item.product?.description || 'Без описания' }}</p>
            <p>Цена: {{ item.product?.price || 0 }} ₽</p>
            <p v-if="item.product?.stock !== undefined" class="stock-info">
              В наличии: {{ item.product.stock }}
            </p>
          </div>
          <div class="item-controls">
            <button @click="updateQuantity(item.id, item.quantity - 1)" :disabled="item.quantity <= 1">-</button>
            <span>{{ item.quantity }}</span>
            <button @click="updateQuantity(item.id, item.quantity + 1)" :disabled="item.quantity >= (item.product?.stock || 0)">+</button>
            <button @click="removeItem(item.id)" class="remove-btn">Удалить</button>
          </div>
        </div>
      </div>
      <div class="cart-summary">
        <AddressForm
          v-model="shippingAddress"
          label="Адрес доставки"
          testid-prefix="cart-"
        />
        <h3>Итого: {{ totalPrice.toFixed(2) }} ₽</h3>
        <button @click="createOrder" :disabled="creatingOrder || !isAddressValid" class="checkout-btn" data-testid="checkout-button">
          {{ creatingOrder ? 'Оформление заказа...' : 'Оформить заказ' }}
        </button>
      </div>
    </div>
    <div v-else class="empty-cart">
      <p>Ваша корзина пуста.</p>
      <router-link to="/" class="browse-link">Перейти в каталог</router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/services/api';
import { useToast } from '@/composables/useToast';
import AddressForm from '@/components/AddressForm.vue';

const cart = ref({ items: [] });
const loading = ref(true);
const creatingOrder = ref(false);
const shippingAddress = ref({
  region: '',
  district: '',
  city: '',
  street: '',
  house: '',
  apartment: '',
});
const router = useRouter();
const { add: toast } = useToast();

const isAddressValid = computed(() => {
  return shippingAddress.value.city?.trim() && shippingAddress.value.street?.trim() && shippingAddress.value.house?.trim();
});

const fetchCart = async () => {
  try {
    const [cartResponse, profileResponse] = await Promise.all([
      api.get('/cart/'),
      api.get('/auth/profile'),
    ]);
    cart.value = cartResponse.data;
    if (profileResponse.data.shipping_address) {
      shippingAddress.value = { ...profileResponse.data.shipping_address };
    }
  } catch (err) {
    console.error('Failed to fetch cart:', err);
    toast('Не удалось загрузить корзину', 'error');
  } finally {
    loading.value = false;
  }
};

const updateQuantity = async (itemId, newQuantity) => {
  if (newQuantity < 1) return;

  try {
    await api.put(`/cart/update/${itemId}`, { quantity: newQuantity });
    await fetchCart();
  } catch (err) {
    console.error('Failed to update quantity:', err);
    toast('Не удалось обновить количество', 'error');
  }
};

const removeItem = async (itemId) => {
  try {
    await api.delete(`/cart/remove/${itemId}`);
    await fetchCart();
  } catch (err) {
    console.error('Failed to remove item:', err);
    toast('Не удалось удалить товар', 'error');
  }
};

const createOrder = async () => {
  if (creatingOrder.value) return;
  if (!isAddressValid.value) {
    toast('Заполните город, улицу и дом', 'error');
    return;
  }

  creatingOrder.value = true;
  try {
    const response = await api.post('/orders/create', {
      shipping_address: { ...shippingAddress.value },
    });
    toast('Заказ успешно создан!', 'success');
    router.push('/orders');
  } catch (err) {
    console.error('Failed to create order:', err);
    const detail = err.response?.data?.detail;
    toast(detail || 'Не удалось создать заказ', 'error');
  } finally {
    creatingOrder.value = false;
  }
};

const totalPrice = computed(() => {
  return cart.value.items.reduce((total, item) => {
    return total + (item.product?.price || 0) * item.quantity;
  }, 0);
});

onMounted(fetchCart);
</script>

<style scoped>
.cart {
  max-width: 800px;
  margin: 0 auto;
  padding: 1rem;
}

.cart-item {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1rem;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  margin-bottom: 1rem;
  background: var(--color-bg-white);
}

@media (min-width: 640px) {
  .cart-item {
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
  }
}

.item-details {
  flex: 1;
  min-width: 0;
}

.item-details h3 {
  margin: 0 0 0.5rem;
  font-size: 1rem;
  word-break: break-word;
}

.item-details p {
  margin: 0.25rem 0;
  color: var(--color-text-secondary);
  font-size: 0.875rem;
}

.stock-info {
  font-size: 0.85rem;
  color: #4a5568;
}

.item-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}

.item-controls button {
  min-width: 36px;
  min-height: 36px;
  padding: 0.25rem 0.5rem;
  border: 1px solid var(--color-border);
  background: var(--color-bg-white);
  border-radius: 8px;
  cursor: pointer;
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.item-controls button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.remove-btn {
  background-color: #fff0f0;
  color: var(--color-danger);
  border-color: transparent;
  margin-left: 0.5rem;
  font-size: 0.875rem;
  padding: 0.25rem 0.75rem;
}

@media (min-width: 640px) {
  .remove-btn {
    margin-left: 1rem;
  }
}

.cart-summary {
  margin-top: 1.5rem;
  padding: 1rem;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background-color: var(--color-bg-white);
}

.checkout-btn {
  width: 100%;
  background-color: var(--color-primary);
  color: white;
  border: none;
  padding: 0.875rem 1.5rem;
  font-size: 1rem;
  font-weight: 600;
  border-radius: 12px;
  cursor: pointer;
  margin-top: 0.75rem;
  transition: opacity 0.15s;
}

.checkout-btn:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.empty-cart {
  text-align: center;
  padding: 3rem 1rem;
}

.browse-link {
  display: inline-block;
  margin-top: 1rem;
  padding: 0.625rem 1.25rem;
  background: var(--color-primary);
  color: #fff;
  text-decoration: none;
  border-radius: 10px;
  font-weight: 500;
}

.loading {
  text-align: center;
  padding: 2rem;
}
</style>
