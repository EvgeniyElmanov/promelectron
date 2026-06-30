import api from '@/services/api';

export const register = (payload) => api.post('/register/', payload);

export const login = (payload) => api.post('/login/', payload);

export const requestPasswordReset = (email) =>
  api.post('/auth/password-reset-request/', { email });

export const confirmPasswordReset = (token, newPassword) =>
  api.post('/auth/password-reset/', { token, new_password: newPassword });

export const getOAuthProviders = () => api.get('/auth/providers/');

export const resendVerification = (payload = {}) =>
  api.post('/auth/resend-verification/', payload);

export const verifyEmail = (token) =>
  api.get('/auth/verify-email/', { params: { token }, maxRedirects: 0 });
