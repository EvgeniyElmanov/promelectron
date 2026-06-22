import api from '@/services/api';

export const getMyAddresses = () => api.get('/users/me/addresses/');

export const createMyAddress = (addressData) =>
  api.post('/users/me/addresses/', addressData);
