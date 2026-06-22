import { ref } from 'vue';
import { getMyAddresses, createMyAddress } from '@/api/users';

const addresses = ref([]);
const loading = ref(false);
const error = ref(null);

export const useUserAddresses = () => {
  const fetchAddresses = async () => {
    loading.value = true;
    error.value = null;
    try {
      const { data } = await getMyAddresses();
      addresses.value = data;
      return data;
    } catch (err) {
      error.value = err.response?.data?.detail || 'Не удалось загрузить адреса';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const addAddress = async (addressData) => {
    error.value = null;
    try {
      const { data } = await createMyAddress(addressData);
      addresses.value.push(data);
      return data;
    } catch (err) {
      error.value = err.response?.data?.detail || 'Не удалось сохранить адрес';
      throw err;
    }
  };

  return {
    addresses,
    loading,
    error,
    fetchAddresses,
    addAddress,
  };
};
