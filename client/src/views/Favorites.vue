<template>
  <div class="favorites">
    <div class="favorites__header">
      <h1 class="favorites__title" data-testid="favorites-title">Избранное</h1>
    </div>

    <div v-if="loading" class="favorites__grid">
      <SkeletonProductCard v-for="i in 4" :key="'sk' + i" />
    </div>

    <div v-else-if="favorites.length === 0" class="favorites__empty" data-testid="favorites-empty">
      <p>У вас пока нет избранных товаров</p>
      <router-link to="/" class="favorites__link">Перейти к покупкам</router-link>
    </div>

    <div v-else class="favorites__grid">
      <ProductCard
        v-for="item in favorites"
        :key="item.id"
        :product="item.product"
        data-testid="favorite-item"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/services/api';
import ProductCard from '@/components/ProductCard.vue';
import SkeletonProductCard from '@/components/SkeletonProductCard.vue';

const router = useRouter();

const favorites = ref([]);
const loading = ref(false);

const fetchFavorites = async () => {
  loading.value = true;
  try {
    const { data } = await api.get('/favorites/');
    favorites.value = data;
  } catch (err) {
    if (err?.response?.status === 401) {
      router.push('/login');
    }
  } finally {
    loading.value = false;
  }
};

onMounted(fetchFavorites);
</script>

<style scoped>
.favorites {
  background: var(--color-bg);
  min-height: 100vh;
  padding: 12px;
}

.favorites__header {
  padding: 10px 0 16px;
}

.favorites__title {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text);
}

.favorites__loading {
  text-align: center;
  padding: 40px;
  color: var(--color-text-secondary);
  font-size: 14px;
}

.favorites__empty {
  text-align: center;
  padding: 60px 20px;
  color: var(--color-text-secondary);
  font-size: 15px;
}

.favorites__empty p {
  margin-bottom: 16px;
}

.favorites__link {
  display: inline-block;
  padding: 12px 24px;
  border-radius: 12px;
  background: var(--color-primary);
  color: #fff;
  font-size: 15px;
  font-weight: 500;
}

.favorites__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

@media (min-width: 768px) {
  .favorites {
    padding: 16px;
  }
  
  .favorites__grid {
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
  }
}

@media (min-width: 1024px) {
  .favorites__grid {
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
  }
}

@media (min-width: 1280px) {
  .favorites__grid {
    grid-template-columns: repeat(5, 1fr);
    gap: 16px;
  }
}
</style>
