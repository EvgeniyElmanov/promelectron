<template>
  <div class="profile-container">
    <h2>User Profile</h2>
    <div v-if="user">
      <p><strong>Email:</strong> {{ user.email }}</p>
      <p><strong>Full Name:</strong> {{ user.full_name || 'Not provided' }}</p>
      <p><strong>Role:</strong> {{ user.role }}</p>
      <p><strong>Created At:</strong> {{ user.created_at }}</p>
    </div>
    <div v-else>
      <p>Loading...</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import api from '@/services/api';

const user = ref(null);

const fetchUserProfile = async () => {
  try {
    const response = await api.get('/me'); // Предполагается, что у тебя есть такой эндпоинт
    user.value = response.data;
  } catch (err) {
    console.error('Failed to fetch user profile:', err);
    // Можно добавить сообщение об ошибке
  }
};

onMounted(fetchUserProfile);
</script>

<style scoped>
.profile-container {
  max-width: 600px;
  margin: 0 auto;
  padding: 1rem;
}
</style>
