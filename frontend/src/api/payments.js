import api from '@/services/api';

export const createPayment = (orderId) => api.post(`/payments/${orderId}/`);

export const createGuestPayment = (orderId, guestEmail) =>
  api.post(`/payments/guest/${orderId}/`, { guest_email: guestEmail });

export const syncPaymentStatusByOrder = (orderId) =>
  api.post(`/payments/sync-by-order/${orderId}/`);

export const confirmMockPayment = (orderId) =>
  api.post(`/payments/${orderId}/mock-confirm/`);

export const confirmGuestMockPayment = (orderId, guestEmail) =>
  api.post(`/payments/guest/${orderId}/mock-confirm/`, { guest_email: guestEmail });
