import { ref, watch, nextTick, onUnmounted } from 'vue';

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

let titleCounter = 0;

const resolve = (value) => (typeof value === 'function' ? value() : value && value.value !== undefined ? value.value : value);

export const useModal = ({ isOpen, onClose, closeOnEscape = true }) => {
  const dialogRef = ref(null);
  const titleId = `modal-title-${++titleCounter}`;
  let triggerEl = null;

  const focusableElements = () => {
    const dialog = dialogRef.value;
    return dialog ? Array.from(dialog.querySelectorAll(FOCUSABLE_SELECTOR)) : [];
  };

  const focusFirst = () => {
    const first = focusableElements()[0];
    (first || dialogRef.value)?.focus();
  };

  const onKeydown = (event) => {
    if (event.key === 'Escape') {
      // Кооперация с лайтбоксом AdminOrderModal: наш листенер регистрируется при
      // открытии модалки — раньше листенера лайтбокса, поэтому отработаем первыми;
      // гард closeOnEscape перестраховывает независимо от порядка листенеров.
      if (!event.defaultPrevented && resolve(closeOnEscape)) {
        onClose();
      }
      return;
    }
    if (event.key !== 'Tab') return;
    const dialog = dialogRef.value;
    if (!dialog) return;
    const focusable = focusableElements();
    if (focusable.length === 0) {
      event.preventDefault();
      return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    const active = document.activeElement;
    if (event.shiftKey) {
      if (active === first || !dialog.contains(active)) {
        event.preventDefault();
        last.focus();
      }
    } else if (active === last || !dialog.contains(active)) {
      event.preventDefault();
      first.focus();
    }
  };

  const attach = () => document.addEventListener('keydown', onKeydown);
  const detach = () => document.removeEventListener('keydown', onKeydown);

  let opened = false;

  const open = async () => {
    opened = true;
    triggerEl = document.activeElement;
    attach();
    await nextTick();
    focusFirst();
  };

  const close = () => {
    opened = false;
    detach();
    if (triggerEl && document.contains(triggerEl) && typeof triggerEl.focus === 'function') {
      triggerEl.focus();
    }
    triggerEl = null;
  };

  watch(
    () => resolve(isOpen),
    (isOpened) => {
      if (isOpened) {
        open();
      } else if (opened) {
        close();
      }
    },
    { immediate: true }
  );

  // Модалка может размонтироваться из открытого состояния (родительский v-if)
  // без перехода isOpen → false: фокус всё равно возвращаем инициатору.
  onUnmounted(() => {
    if (opened) close();
  });

  return { dialogRef, titleId };
};
