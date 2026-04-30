<template>
  <header class="header">
    <nav>
      <router-link to="/">Home</router-link> |
      <router-link to="/cart">Cart</router-link> |
      <router-link to="/orders">My Orders</router-link> |
      <router-link to="/profile" v-if="isAuthenticated()">Profile</router-link> |
      <router-link to="/login" v-if="!isAuthenticated()">Login</router-link>
      <a href="#" @click="logout" v-else>Logout</a>
    </nav>
  </header>
</template>

<script setup>
import { useRouter } from 'vue-router';
import { useAuth } from '@/composables/useAuth';

const router = useRouter();
const { isAuthenticated } = useAuth();

const logout = () => {
  localStorage.removeItem('access_token');
  router.push('/login');
};
</script>

<style scoped>
.header {
  padding: 1rem;
  background-color: #f5f5f5;
  border-bottom: 1px solid #ddd;
}
</style>
