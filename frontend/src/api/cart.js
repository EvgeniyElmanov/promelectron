import api from '@/services/api';

export const selectCartItem = (itemId, selected) =>
  api.patch(`/cart/select/${itemId}/`, { selected });

export const selectAllCartItems = () => api.post('/cart/select-all/');

export const deselectAllCartItems = () => api.post('/cart/deselect-all/');
