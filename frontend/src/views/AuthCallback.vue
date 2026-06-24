<template>
  <div class="callback-container">
    <h2>Авторизация...</h2>
    <p v-if="error">{{ error }}</p>
    <div v-else>Пожалуйста, подождите...</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import api from '@/services/api';
import { useAuth } from '@/composables/useAuth';
import { useCart } from '@/composables/useCart';

const route = useRoute();
const router = useRouter();
const error = ref('');
const { setAuth } = useAuth();
const { mergeCartOnLogin } = useCart();

onMounted(async () => {
  try {
    const code = route.query.code;
    const state = route.query.state;

    if (!code || !state) {
      error.value = 'Некорректный запрос: отсутствуют параметры code или state';
      return;
    }

    // Провайдер бэкенд определяет сам по state (server-side), поэтому
    // здесь достаточно передать code и state.
    const response = await api.get('/auth/callback', {
      params: { code, state }
    });

    setAuth(response.data.access_token, response.data.user);

    await mergeCartOnLogin();
    router.push('/');
  } catch (err) {
    error.value = err.response?.data?.detail || 'Ошибка авторизации';
  }
});
</script>

<style scoped>
.callback-container {
  max-width: 400px;
  margin: 0 auto;
  padding: 2rem;
  text-align: center;
}
</style>