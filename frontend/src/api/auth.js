import api from '@/services/api';

export const requestPasswordReset = (email) =>
  api.post('/auth/password-reset-request/', { email });

export const confirmPasswordReset = (token, newPassword) =>
  api.post('/auth/password-reset/', { token, new_password: newPassword });

export const getOAuthProviders = () => api.get('/auth/providers/');
