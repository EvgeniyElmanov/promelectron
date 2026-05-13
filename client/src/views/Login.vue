<template>
  <div class="login-container">
    <h2>Вход</h2>
    <form @submit.prevent="handleLogin" data-testid="login-form">
      <input v-model="email" type="email" placeholder="Email" data-testid="login-email" required />
      <input v-model="password" type="password" placeholder="Пароль" data-testid="login-password" required />
      <button type="submit" data-testid="login-submit">Войти</button>
    </form>
    <div class="oauth-buttons">
      <button @click="loginWithGoogle" class="oauth-button google">Войти через Google</button>
      <button @click="loginWithYandex" class="oauth-button yandex">Войти через Яндекс</button>
    </div>
    <p v-if="error" class="error" data-testid="login-error">{{ error }}</p>
    <p>
      Нет аккаунта? <router-link to="/register">Зарегистрироваться</router-link>
    </p>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/services/api';
import { useAuth } from '@/composables/useAuth';

const email = ref('');
const password = ref('');
const error = ref('');
const router = useRouter();
const { setAuth } = useAuth();

const handleLogin = async () => {
  try {
    const response = await api.post('/login', {
      email: email.value,
      password: password.value,
    });

    setAuth(response.data.access_token, response.data.user);
    router.push('/');
  } catch (err) {
    error.value = err.response?.data?.detail || 'Ошибка входа';
  }
};

const loginWithGoogle = async () => {
  try {
    const response = await api.get('/auth/google/login');
    window.location.href = response.data.url;
  } catch (err) {
    error.value = err.response?.data?.detail || 'Ошибка входа через Google';
  }
};

const loginWithYandex = async () => {
  try {
    const response = await api.get('/auth/yandex/login');
    window.location.href = response.data.url;
  } catch (err) {
    error.value = err.response?.data?.detail || 'Ошибка входа через Яндекс';
  }
};
</script>

<style scoped>
.login-container {
  max-width: 400px;
  margin: 0 auto;
  padding: 2rem;
}

.oauth-buttons {
  margin: 1.5rem 0;
}

.oauth-button {
  display: block;
  width: 100%;
  padding: 0.75rem;
  margin-bottom: 0.5rem;
  border: none;
  border-radius: 4px;
  color: white;
  font-weight: bold;
  cursor: pointer;
}

.oauth-button.google {
  background-color: #4285F4;
}

.oauth-button.yandex {
  background-color: #FF0000;
}

.error {
  color: #dc3545;
  margin-top: 0.5rem;
}
</style>
