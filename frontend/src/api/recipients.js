import api from '@/services/api';

export const getRecipients = () => api.get('/me/recipients/');

export const createRecipient = (payload) => api.post('/me/recipients/', payload);

export const updateRecipient = (recipientId, payload) =>
  api.patch(`/me/recipients/${recipientId}/`, payload);

export const deleteRecipient = (recipientId) =>
  api.delete(`/me/recipients/${recipientId}/`);

export const setDefaultRecipient = (recipientId) =>
  api.post(`/me/recipients/${recipientId}/set-default/`);
