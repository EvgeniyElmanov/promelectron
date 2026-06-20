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
