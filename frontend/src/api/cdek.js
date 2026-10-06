import api from '@/services/api';

/**
 * Resolve the CDEK shipment city code for a supplier.
 * @param {number|string} supplierId
 * @returns {Promise<number|null>}
 */
export const getSupplierCityCode = async (supplierId) => {
  const { data } = await api.get(`/cdek/supplier-city-code/${supplierId}/`);
  return data.city_code ?? null;
};

/**
 * Calculate CDEK delivery tariffs for cart items.
 * @param {{items: Array, supplier_id: number, to_location?: object, delivery_point?: string}} payload
 * @returns {Promise<{tariffs: Array}>}
 */
export const calculateDelivery = async (payload) => {
  const { data } = await api.post('/cdek/calculate/', payload);
  return data;
};
