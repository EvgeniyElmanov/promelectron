import { ref, computed } from 'vue';
import {
  getRecipients,
  createRecipient,
  updateRecipient,
  deleteRecipient,
  setDefaultRecipient,
} from '@/api/recipients';

const recipients = ref([]);
const loading = ref(false);
const error = ref(null);

export const useRecipients = () => {
  const defaultRecipient = computed(() =>
    recipients.value.find((r) => r.is_default) || null
  );

  const loadRecipients = async () => {
    loading.value = true;
    error.value = null;
    try {
      const { data } = await getRecipients();
      recipients.value = data || [];
    } catch (err) {
      error.value = err.response?.data?.detail || 'Не удалось загрузить получателей';
      recipients.value = [];
    } finally {
      loading.value = false;
    }
  };

  const addRecipient = async (payload) => {
    loading.value = true;
    error.value = null;
    try {
      const { data } = await createRecipient(payload);
      recipients.value.push(data);
      return data;
    } catch (err) {
      error.value = err.response?.data?.detail || 'Не удалось создать получателя';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const editRecipient = async (recipientId, payload) => {
    loading.value = true;
    error.value = null;
    try {
      const { data } = await updateRecipient(recipientId, payload);
      const idx = recipients.value.findIndex((r) => r.id === recipientId);
      if (idx !== -1) {
        recipients.value[idx] = data;
      }
      return data;
    } catch (err) {
      error.value = err.response?.data?.detail || 'Не удалось обновить получателя';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const removeRecipient = async (recipientId) => {
    loading.value = true;
    error.value = null;
    try {
      await deleteRecipient(recipientId);
      recipients.value = recipients.value.filter((r) => r.id !== recipientId);
    } catch (err) {
      error.value = err.response?.data?.detail || 'Не удалось удалить получателя';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const makeDefaultRecipient = async (recipientId) => {
    loading.value = true;
    error.value = null;
    try {
      const { data } = await setDefaultRecipient(recipientId);
      recipients.value = recipients.value.map((r) =>
        r.id === recipientId ? { ...r, is_default: true } : { ...r, is_default: false }
      );
      return data;
    } catch (err) {
      error.value = err.response?.data?.detail || 'Не удалось назначить получателя по умолчанию';
      throw err;
    } finally {
      loading.value = false;
    }
  };

  return {
    recipients,
    loading,
    error,
    defaultRecipient,
    loadRecipients,
    addRecipient,
    editRecipient,
    removeRecipient,
    makeDefaultRecipient,
  };
};
