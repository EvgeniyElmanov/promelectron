<template>
  <div class="profile-container">
    <h2>User Profile</h2>
    
    <!-- Loading State -->
    <div v-if="loading" class="loading-container">
      <div class="spinner"></div>
      <span>Loading profile...</span>
    </div>
    
    <!-- Error State -->
    <div v-else-if="error" class="error-container">
      <strong>Error! </strong>
      <span>{{ error }}</span>
      <button @click="fetchUserProfile" class="retry-button">
        Try Again
      </button>
    </div>
    
    <!-- User Data -->
    <div v-else-if="user" class="profile-card">
      <div class="profile-grid">
        <div class="profile-field">
          <label>Full Name</label>
          <p>{{ user.full_name || 'Not provided' }}</p>
        </div>
        
        <div class="profile-field">
          <label>Email</label>
          <p>{{ user.email }}</p>
        </div>
        
        <div class="profile-field">
          <label>Role</label>
          <span class="role-badge" :class="user.role">
            {{ user.role }}
          </span>
        </div>
        
        <div class="profile-field">
          <label>Member Since</label>
          <p>{{ formatDate(user.created_at) }}</p>
        </div>
      </div>
      
      <div class="logout-section">
        <button
          @click="logout"
          class="logout-button"
        >
          Logout
        </button>
      </div>
    </div>
    
    <!-- Empty State -->
    <div v-else class="empty-state">
      <p>No user data available</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import api from '@/services/api';
import { useRouter } from 'vue-router';

const user = ref(null);
const loading = ref(true);
const error = ref(null);
const router = useRouter();

const formatDate = (dateString) => {
  if (!dateString) return 'Not available';
  const options = { year: 'numeric', month: 'long', day: 'numeric' };
  return new Date(dateString).toLocaleDateString(undefined, options);
};

const fetchUserProfile = async () => {
  try {
    loading.value = true;
    error.value = null;
    const response = await api.get('/auth/profile');
    user.value = response.data;
  } catch (err) {
    console.error('Failed to fetch user profile:', err);
    error.value = err.response?.data?.detail || 'Failed to load profile. Please try again.';
  } finally {
    loading.value = false;
  }
};

const logout = () => {
  // Remove token from localStorage
  localStorage.removeItem('access_token');
  // Redirect to login page
  router.push('/login');
};

onMounted(fetchUserProfile);
</script>

<style scoped>
.profile-container {
  max-width: 600px;
  margin: 0 auto;
  padding: 1rem;
}

.profile-container h2 {
  font-size: 1.5rem;
  font-weight: bold;
  margin-bottom: 1.5rem;
  color: #333;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 10rem;
}

.spinner {
  border: 4px solid rgba(0, 0, 0, 0.1);
  border-left-color: #007bff;
  border-radius: 50%;
  width: 2rem;
  height: 2rem;
  animation: spin 1s linear infinite;
  margin-right: 1rem;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.error-container {
  background-color: #f8d7da;
  border: 1px solid #f5c6cb;
  color: #721c24;
  padding: 1rem;
  border-radius: 0.375rem;
  margin-bottom: 1rem;
}

.retry-button {
  margin-top: 0.5rem;
  background-color: #dc3545;
  color: white;
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
}

.retry-button:hover {
  background-color: #c82333;
}

.profile-card {
  background-color: white;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  border-radius: 0.5rem;
  padding: 1.5rem;
}

.profile-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

@media (max-width: 640px) {
  .profile-grid {
    grid-template-columns: 1fr;
  }
}

.profile-field {
  margin-bottom: 1rem;
}

.profile-field label {
  display: block;
  font-weight: bold;
  margin-bottom: 0.25rem;
  color: #555;
  font-size: 0.875rem;
}

.profile-field p {
  color: #333;
  font-size: 1rem;
}

.role-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  border-radius: 9999px;
  font-weight: 500;
}

.role-badge.user {
  background-color: #e1f0fa;
  color: #1a56bb;
}

.role-badge.admin {
  background-color: #e1f5ee;
  color: #046c4e;
}

.role-badge.supplier {
  background-color: #f0e1fa;
  color: #6d28d9;
}

.logout-section {
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid #eee;
}

.logout-button {
  background-color: #dc3545;
  color: white;
  font-weight: bold;
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 0.25rem;
  cursor: pointer;
  transition: background-color 0.15s ease-in-out;
}

.logout-button:hover {
  background-color: #c82333;
}

.empty-state {
  text-align: center;
  padding: 2.5rem;
  color: #666;
}
</style>
