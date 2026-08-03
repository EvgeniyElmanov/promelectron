import api from '@/services/api';

export const getAdminUserDetail = (userId) => api.get(`/admin/users/${userId}/`);

export const getAdminOrder = (orderId) => api.get(`/admin/orders/${orderId}/`);

// Существующий backend endpoint без trailing slash — не меняем (см. spec D-API).
export const updateAdminOrder = (orderId, payload) => api.put(`/admin/orders/${orderId}`, payload);
