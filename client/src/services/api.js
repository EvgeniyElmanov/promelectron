import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

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
      const isAuthPage = window.location.pathname === '/login' || window.location.pathname === '/register';
      const isAuthRequest = error.config?.url?.includes('/login') || error.config?.url?.includes('/register');
      if (!isAuthPage && !isAuthRequest) {
        localStorage.removeItem('access_token');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;
