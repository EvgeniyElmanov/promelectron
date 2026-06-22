import { ref, computed } from 'vue';
import { createGuestOrder } from '@/api/orders';
import { createGuestPayment } from '@/api/payments';

const PHONE_REGEX = /^\+7\d{10}$/;
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const NAME_REGEX = /^[A-Za-zА-Яа-яЁё\- ]+$/;

export const useGuestCheckout = () => {
  const submitting = ref(false);

  const validateGuestForm = ({ email, firstName, lastName, phone }) => {
    const errors = {};
    if (!email.trim()) {
      errors.email = 'Укажите email';
    } else if (!EMAIL_REGEX.test(email.trim())) {
      errors.email = 'Некорректный email';
    }
    if (!firstName.trim()) {
      errors.firstName = 'Укажите имя';
    } else if (!NAME_REGEX.test(firstName.trim())) {
      errors.firstName = 'Имя содержит недопустимые символы';
    }
    if (!lastName.trim()) {
      errors.lastName = 'Укажите фамилию';
    } else if (!NAME_REGEX.test(lastName.trim())) {
      errors.lastName = 'Фамилия содержит недопустимые символы';
    }
    if (!phone.trim()) {
      errors.phone = 'Укажите телефон';
    } else if (!PHONE_REGEX.test(phone.trim())) {
      errors.phone = 'Телефон должен быть в формате +7XXXXXXXXXX';
    }
    return errors;
  };

  const buildGuestOrderPayload = ({
    items,
    selectedDelivery,
    email,
    firstName,
    lastName,
    phone,
    saveAddress,
  }) => ({
    items: items.map((i) => ({ product_id: i.product_id, quantity: i.quantity })),
    cdek_delivery: { ...selectedDelivery },
    guest_email: email.trim(),
    guest_phone: phone.trim(),
    recipient_first_name: firstName.trim(),
    recipient_last_name: lastName.trim(),
    save_address: saveAddress,
  });

  const submitGuestCheckout = async ({
    items,
    selectedDelivery,
    email,
    firstName,
    lastName,
    phone,
    saveAddress,
  }) => {
    const validationErrors = validateGuestForm({ email, firstName, lastName, phone });
    const firstErrorKey = Object.keys(validationErrors)[0];
    if (firstErrorKey) {
      const error = new Error(validationErrors[firstErrorKey]);
      error.field = firstErrorKey;
      error.errors = validationErrors;
      throw error;
    }
    if (!selectedDelivery?.tariff_code) {
      throw new Error('Выберите доставку СДЭК');
    }
    if (!items?.length) {
      throw new Error('Корзина пуста');
    }

    submitting.value = true;
    try {
      const orderPayload = buildGuestOrderPayload({
        items,
        selectedDelivery,
        email,
        firstName,
        lastName,
        phone,
        saveAddress,
      });
      const { data: order } = await createGuestOrder(orderPayload);

      const { data: payment } = await createGuestPayment(order.id, order.guest_email || email.trim());

      return { order, payment };
    } finally {
      submitting.value = false;
    }
  };

  const isSubmitting = computed(() => submitting.value);

  return {
    submitting: isSubmitting,
    validateGuestForm,
    buildGuestOrderPayload,
    submitGuestCheckout,
  };
};
