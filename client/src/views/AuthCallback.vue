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

const route = useRoute();
const router = useRouter();
const error = ref('');
const { setAuth } = useAuth();

onMounted(async () => {
  try {
    const provider = route.query.provider;
    const code = route.query.code;

    if (!provider || !code) {
      error.value = 'Некорректный запрос: отсутствуют параметры provider или code';
      return;
    }

    const response = await api.get(`/auth/${provider}/callback`, {
      params: { code }
    });

    setAuth(response.data.access_token, {
      id: response.data.user_id,
      email: response.data.email,
    });

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