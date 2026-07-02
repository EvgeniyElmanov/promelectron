import api from '@/services/api';

export const getAdminUserDetail = (userId) => api.get(`/admin/users/${userId}/`);
