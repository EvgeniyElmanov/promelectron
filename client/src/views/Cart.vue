<template>
  <div class="cart" data-testid="cart-page">
    <h2 data-testid="cart-title">Cart</h2>
    <div v-if="loading" class="loading">
      Loading cart...
    </div>
    <div v-else-if="cart.items && cart.items.length > 0">
      <div class="cart-items">
        <div v-for="item in cart.items" :key="item.id" class="cart-item" data-testid="cart-item">
          <div class="item-details">
            <h3>{{ item.product?.name || 'Product' }}</h3>
            <p>{{ item.product?.description || 'No description' }}</p>
            <p>Price: ${{ item.product?.price || 0 }}</p>
          </div>
          <div class="item-controls">
            <button @click="updateQuantity(item.id, item.quantity - 1)" :disabled="item.quantity <= 1">-</button>
            <span>{{ item.quantity }}</span>
            <button @click="updateQuantity(item.id, item.quantity + 1)" :disabled="item.quantity >= (item.product?.stock || 0)">+</button>
            <button @click="removeItem(item.id)" class="remove-btn">Remove</button>
          </div>
        </div>
      </div>
      <div class="cart-summary">
        <h3>Total: ${{ totalPrice.toFixed(2) }}</h3>
        <button @click="createOrder" :disabled="creatingOrder" class="checkout-btn" data-testid="checkout-button">
          {{ creatingOrder ? 'Оформление заказа...' : 'Оформить заказ' }}
        </button>
      </div>
    </div>
    <div v-else class="empty-cart">
      <p>Your cart is empty.</p>
      <router-link to="/" class="browse-link">Browse Products</router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/services/api';
import { useToast } from '@/composables/useToast';

const cart = ref({ items: [] });
const loading = ref(true);
const creatingOrder = ref(false);
const router = useRouter();
const { add: toast } = useToast();

const fetchCart = async () => {
  try {
    const response = await api.get('/cart/');
    cart.value = response.data;
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
    await fetchCart(); // Refresh cart data
  } catch (err) {
    console.error('Failed to update quantity:', err);
    toast('Не удалось обновить количество', 'error');
  }
};

const removeItem = async (itemId) => {
  try {
    await api.delete(`/cart/remove/${itemId}`);
    await fetchCart(); // Refresh cart data
  } catch (err) {
    console.error('Failed to remove item:', err);
    toast('Не удалось удалить товар', 'error');
  }
};

const createOrder = async () => {
  if (creatingOrder.value) return;
  
  creatingOrder.value = true;
  try {
    const response = await api.post('/orders/create');
    toast('Заказ успешно создан!', 'success');
    router.push('/orders');
  } catch (err) {
    console.error('Failed to create order:', err);
    toast('Не удалось создать заказ', 'error');
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
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.item-details {
  flex: 1;
}

.item-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.item-controls button {
  padding: 0.25rem 0.5rem;
  border: 1px solid #ccc;
  background: white;
  border-radius: 4px;
  cursor: pointer;
}

.item-controls button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.remove-btn {
  background-color: #ff4444;
  color: white;
  border-color: #ff4444;
  margin-left: 1rem;
}

.checkout-btn {
  background-color: #4CAF50;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  font-size: 1rem;
  border-radius: 4px;
  cursor: pointer;
}

.checkout-btn:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.empty-cart {
  text-align: center;
  padding: 2rem;
}

.browse-link {
  color: #007bff;
  text-decoration: none;
}

.browse-link:hover {
  text-decoration: underline;
}

.loading {
  text-align: center;
  padding: 2rem;
}
</style>
