import { ref, computed } from 'vue';
import { jwtDecode } from 'jwt-decode';
import { resendVerification as apiResendVerification } from '@/api/auth';

// Модульный уровень — единое состояние для всех компонентов
const token = ref(localStorage.getItem('access_token') || null);
const currentUser = ref(null);

export const useAuth = () => {
  const isAuthenticated = computed(() => !!token.value);
  const user = computed(() => currentUser.value);
  const emailVerified = computed(() => !!currentUser.value?.email_verified);

  const getToken = () => token.value;

  const getUserRole = () => {
    if (!token.value) return null;
    try {
      const decoded = jwtDecode(token.value);
      return decoded.role;
    } catch {
      return null;
    }
  };

  const isAdmin = computed(() => getUserRole() === 'admin');
  const isSupplier = computed(() => getUserRole() === 'supplier');

  const setAuth = (newToken, userData = null) => {
    token.value = newToken;
    currentUser.value = userData;
    if (newToken) {
      localStorage.setItem('access_token', newToken);
    } else {
      localStorage.removeItem('access_token');
    }
  };

  const setUser = (userData) => {
    if (userData) {
      currentUser.value = userData;
    }
  };

  const logout = () => {
    setAuth(null, null);
  };

  const resendVerification = async (email) => {
    const payload = email ? { email } : {};
    const { data } = await apiResendVerification(payload);
    return data;
  };

  return {
    token,
    user,
    emailVerified,
    isAuthenticated,
    isAdmin,
    isSupplier,
    getToken,
    getUserRole,
    setAuth,
    setUser,
    logout,
    resendVerification,
  };
};
