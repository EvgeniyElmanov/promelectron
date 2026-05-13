<template>
  <div class="register-container">
    <h2>Регистрация</h2>
    <form @submit.prevent="handleRegister" data-testid="register-form">
      <input v-model="fullName" type="text" placeholder="Имя (необязательно)" data-testid="register-name" />
      <input v-model="email" type="email" placeholder="Email" data-testid="register-email" required />
      <input v-model="password" type="password" placeholder="Пароль" data-testid="register-password" required />
      <input v-model="confirmPassword" type="password" placeholder="Подтвердите пароль" data-testid="register-password-confirm" required />
      <button type="submit" data-testid="register-submit">Зарегистрироваться</button>
    </form>
    <p v-if="error" class="error" data-testid="register-error">{{ error }}</p>
    <p>
      Уже есть аккаунт? <router-link to="/login">Войти</router-link>
    </p>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/services/api';
import { useAuth } from '@/composables/useAuth';

const fullName = ref('');
const email = ref('');
const password = ref('');
const confirmPassword = ref('');
const error = ref('');
const router = useRouter();
const { setAuth } = useAuth();

const handleRegister = async () => {
  if (password.value !== confirmPassword.value) {
    error.value = 'Пароли не совпадают';
    return;
  }

  try {
    const response = await api.post('/register', {
      email: email.value,
      password: password.value,
      full_name: fullName.value || null,
    });

    setAuth(response.data.access_token, response.data.user);
    router.push('/');
  } catch (err) {
    error.value = err.response?.data?.detail || 'Ошибка регистрации';
  }
};
</script>

<style scoped>
.register-container {
  max-width: 400px;
  margin: 0 auto;
  padding: 2rem;
}

.error {
  color: #dc3545;
  margin-top: 0.5rem;
}
</style>
