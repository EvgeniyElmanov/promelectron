import { reactive } from 'vue';

const toasts = reactive([]);

let id = 0;

export const useToast = () => {
  const add = (message, type = 'info', duration = 3000) => {
    const toast = { id: ++id, message, type, duration };
    toasts.push(toast);
    setTimeout(() => remove(toast.id), duration);
  };

  const remove = (toastId) => {
    const index = toasts.findIndex((t) => t.id === toastId);
    if (index !== -1) toasts.splice(index, 1);
  };

  return { toasts, add, remove };
};
