<template>
  <div class="register-container">
    <h2>Регистрация</h2>
    <form @submit.prevent="handleRegister">
      <input v-model="name" type="text" placeholder="Имя" required />
      <input v-model="email" type="email" placeholder="Email" required />
      <input v-model="password" type="password" placeholder="Пароль" required />
      <input v-model="confirmPassword" type="password" placeholder="Подтвердите пароль" required />
      <button type="submit">Зарегистрироваться</button>
    </form>
    <p v-if="error">{{ error }}</p>
    <p>
      Уже есть аккаунт? <router-link to="/login">Войти</router-link>
    </p>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/services/api';

const name = ref('');
const email = ref('');
const password = ref('');
const confirmPassword = ref('');
const error = ref('');
const router = useRouter();

const handleRegister = async () => {
  if (password.value !== confirmPassword.value) {
    error.value = 'Пароли не совпадают';
    return;
  }

  try {
    await api.post('/register', {
      name: name.value,
      email: email.value,
      password: password.value,
    });

    // После успешной регистрации перенаправляем на страницу входа
    router.push('/login');
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
</style>