import api from '@/services/api';

export const createGuestOrder = (payload) => api.post('/orders/create-guest/', payload);

export const getOrder = (orderId) => api.get(`/orders/${orderId}/`);

export const getGuestOrder = (orderId, guestEmail) =>
  api.get(`/orders/guest/${orderId}/?guest_email=${encodeURIComponent(guestEmail)}`);
