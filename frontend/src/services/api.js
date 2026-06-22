import axios from 'axios';

const API_BASE_URL = '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
});

// Interceptor для добавления токена
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    
    // Ensure headers object exists
    if (!config.headers) {
      config.headers = {};
    }
    
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor для обработки ошибок авторизации
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      const token = localStorage.getItem('access_token');
      const isAuthPage = window.location.pathname === '/login' || window.location.pathname === '/register';
      const isAuthRequest = error.config?.url?.includes('/login') || error.config?.url?.includes('/register');
      const url = error.config?.url || '';
      const isPublicRequest = url.includes('/products/')
        || url.includes('/categories')
        || url.includes('/reviews');
      // Перенаправляем на login только если у пользователя был токен (протухшая сессия).
      // Гость без токена не должен улетать на login из-за 401 на необязательных endpoints.
      if (token && !isAuthPage && !isAuthRequest && !isPublicRequest) {
        localStorage.removeItem('access_token');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;
