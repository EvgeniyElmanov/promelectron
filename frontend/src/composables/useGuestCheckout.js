import { ref, computed } from 'vue';
import { createGuestOrder } from '@/api/orders';

const PHONE_REGEX = /^\+7\d{10}$/;
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const NAME_REGEX = /^[A-Za-zА-Яа-яЁё\- ]+$/;

export const normalizePhone = (phone) => {
  if (!phone) return '';
  const digits = phone.replace(/\D/g, '');
  if (digits.length === 11 && digits.startsWith('7')) {
    return `+${digits}`;
  }
  if (digits.length === 11 && digits.startsWith('8')) {
    return `+7${digits.slice(1)}`;
  }
  if (digits.length === 10) {
    return `+7${digits}`;
  }
  return phone.trim();
};

export const useGuestCheckout = () => {
  const submitting = ref(false);

  const validateGuestForm = ({ email, firstName, lastName, patronymic, phone, countryCode = 'RU' }) => {
    const errors = {};
    const normalizedEmail = email.trim().toLowerCase();
    if (!normalizedEmail) {
      errors.email = 'Укажите email';
    } else if (!EMAIL_REGEX.test(normalizedEmail)) {
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
    if (countryCode === 'RU') {
      if (!patronymic.trim()) {
        errors.patronymic = 'Укажите отчество';
      } else if (!NAME_REGEX.test(patronymic.trim())) {
        errors.patronymic = 'Отчество содержит недопустимые символы';
      }
    }
    const normalizedPhone = normalizePhone(phone);
    if (!phone.trim()) {
      errors.phone = 'Укажите телефон';
    } else if (!PHONE_REGEX.test(normalizedPhone)) {
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
    patronymic,
    phone,
    countryCode,
    saveAddress,
  }) => ({
    items: items.map((i) => ({ product_id: i.product_id, quantity: i.quantity })),
    cdek_delivery: { ...selectedDelivery },
    guest_email: email.trim().toLowerCase(),
    guest_phone: normalizePhone(phone),
    recipient_first_name: firstName.trim(),
    recipient_last_name: lastName.trim(),
    recipient_patronymic: countryCode === 'RU' ? patronymic.trim() : undefined,
    recipient_phone: normalizePhone(phone),
    recipient_country_code: countryCode || 'RU',
    save_address: saveAddress,
  });

  const submitGuestCheckout = async ({
    items,
    selectedDelivery,
    email,
    firstName,
    lastName,
    patronymic,
    phone,
    countryCode,
    saveAddress,
  }) => {
    const validationErrors = validateGuestForm({
      email,
      firstName,
      lastName,
      patronymic,
      phone,
      countryCode,
    });
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
        patronymic,
        phone,
        countryCode,
        saveAddress,
      });
      const { data: order } = await createGuestOrder(orderPayload);

      return { order };
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
