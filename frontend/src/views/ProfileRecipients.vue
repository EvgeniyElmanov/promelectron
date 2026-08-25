<template>
  <div class="profile-recipients" data-testid="profile-recipients-page">
    <div class="profile-recipients__header">
      <button class="profile-recipients__back" @click="router.back()">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 12H5M12 19l-7-7 7-7"/>
        </svg>
      </button>
      <h1 class="profile-recipients__title">Получатели</h1>
      <button
        class="profile-recipients__add"
        data-testid="recipient-add-btn"
        @click="openCreate"
      >
        + Новый
      </button>
    </div>

    <div v-if="loading" class="profile-recipients__loading">Загрузка...</div>

    <div v-else-if="recipients.length === 0" class="profile-recipients__empty" data-testid="recipients-empty">
      <p>У вас пока нет сохранённых получателей.</p>
      <button class="profile-recipients__empty-btn" @click="openCreate">Добавить получателя</button>
    </div>

    <div v-else class="profile-recipients__list">
      <div
        v-for="recipient in recipients"
        :key="recipient.id"
        class="recipient-card"
        :class="{ 'recipient-card--default': recipient.is_default }"
        :data-testid="`recipient-card-${recipient.id}`"
      >
        <div class="recipient-card__main">
          <div class="recipient-card__name" data-testid="recipient-card-name">
            {{ recipient.last_name }} {{ recipient.first_name }}
            <span v-if="recipient.patronymic">{{ recipient.patronymic }}</span>
          </div>
          <div class="recipient-card__phone" data-testid="recipient-card-phone">{{ recipient.phone }}</div>
          <div v-if="recipient.is_default" class="recipient-card__badge">По умолчанию</div>
        </div>
        <div class="recipient-card__actions">
          <button
            v-if="!recipient.is_default"
            class="recipient-card__btn recipient-card__btn--default"
            :data-testid="`recipient-set-default-${recipient.id}`"
            :disabled="loading"
            @click="handleSetDefault(recipient.id)"
          >
            По умолчанию
          </button>
          <button
            class="recipient-card__btn recipient-card__btn--edit"
            :data-testid="`recipient-edit-${recipient.id}`"
            @click="openEdit(recipient)"
          >
            Изменить
          </button>
          <button
            class="recipient-card__btn recipient-card__btn--delete"
            :data-testid="`recipient-delete-${recipient.id}`"
            :disabled="loading"
            @click="handleDelete(recipient.id)"
          >
            Удалить
          </button>
        </div>
      </div>
    </div>

    <!-- Recipient Modal -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <div class="modal__header">
          <h3>{{ isEdit ? 'Редактировать получателя' : 'Новый получатель' }}</h3>
          <button class="modal__close" @click="closeModal">&times;</button>
        </div>
        <form class="modal__form" @submit.prevent="handleSubmit">
          <div class="field">
            <label class="field__label">Имя <span class="field__required">*</span></label>
            <input
              v-model="form.first_name"
              class="field__input"
              :class="{ 'field__input--error': formErrors.first_name }"
              placeholder="Иван"
              data-testid="recipient-form-first-name"
            />
            <span v-if="formErrors.first_name" class="field__error">{{ formErrors.first_name }}</span>
          </div>
          <div class="field">
            <label class="field__label">Фамилия <span class="field__required">*</span></label>
            <input
              v-model="form.last_name"
              class="field__input"
              :class="{ 'field__input--error': formErrors.last_name }"
              placeholder="Иванов"
              data-testid="recipient-form-last-name"
            />
            <span v-if="formErrors.last_name" class="field__error">{{ formErrors.last_name }}</span>
          </div>
          <div class="field">
            <label class="field__label">Страна <span class="field__required">*</span></label>
            <select
              v-model="form.country_code"
              class="field__input"
              data-testid="recipient-form-country-code"
            >
              <option value="RU">Россия</option>
              <option value="KZ">Казахстан</option>
              <option value="BY">Беларусь</option>
            </select>
          </div>
          <div v-if="form.country_code === 'RU'" class="field">
            <label class="field__label">Отчество</label>
            <input
              v-model="form.patronymic"
              class="field__input"
              :class="{ 'field__input--error': formErrors.patronymic }"
              placeholder="Иванович"
              data-testid="recipient-form-patronymic"
            />
            <span v-if="formErrors.patronymic" class="field__error">{{ formErrors.patronymic }}</span>
          </div>
          <div class="field">
            <label class="field__label">Телефон <span class="field__required">*</span></label>
            <input
              v-model="form.phone"
              class="field__input"
              :class="{ 'field__input--error': formErrors.phone }"
              type="tel"
              placeholder="+7 (999) 000-00-00"
              data-testid="recipient-form-phone"
            />
            <span v-if="formErrors.phone" class="field__error">{{ formErrors.phone }}</span>
          </div>
          <label class="field field--checkbox">
            <input
              v-model="form.is_default"
              type="checkbox"
              data-testid="recipient-form-is-default"
            />
            <span>Получатель по умолчанию</span>
          </label>
          <div v-if="formError" class="form-error">{{ formError }}</div>
          <button type="submit" class="modal__submit" :disabled="loading" data-testid="recipient-form-submit">
            {{ loading ? 'Сохранение...' : (isEdit ? 'Сохранить' : 'Добавить') }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from '@/composables/useToast';
import { useRecipients } from '@/composables/useRecipients';
import { normalizePhone } from '@/composables/useGuestCheckout';

const PHONE_REGEX = /^\+7\d{10}$/;
const NAME_REGEX = /^[A-Za-zА-Яа-яЁё\- ]+$/;

const router = useRouter();
const { add: toast } = useToast();
const {
  recipients,
  loading,
  loadRecipients,
  addRecipient,
  editRecipient,
  removeRecipient,
  makeDefaultRecipient,
} = useRecipients();

const showModal = ref(false);
const isEdit = ref(false);
const editingId = ref(null);
const form = ref({
  first_name: '',
  last_name: '',
  patronymic: '',
  phone: '',
  country_code: 'RU',
  is_default: false,
});
const formErrors = ref({});
const formError = ref('');

const openCreate = () => {
  isEdit.value = false;
  editingId.value = null;
  form.value = {
    first_name: '',
    last_name: '',
    patronymic: '',
    phone: '',
    country_code: 'RU',
    is_default: false,
  };
  formErrors.value = {};
  formError.value = '';
  showModal.value = true;
};

const openEdit = (recipient) => {
  isEdit.value = true;
  editingId.value = recipient.id;
  form.value = {
    first_name: recipient.first_name || '',
    last_name: recipient.last_name || '',
    patronymic: recipient.patronymic || '',
    phone: recipient.phone || '',
    country_code: recipient.country_code || 'RU',
    is_default: recipient.is_default || false,
  };
  formErrors.value = {};
  formError.value = '';
  showModal.value = true;
};

const closeModal = () => {
  showModal.value = false;
};

const validateForm = () => {
  const errors = {};
  const firstName = form.value.first_name.trim();
  const lastName = form.value.last_name.trim();
  const patronymic = form.value.patronymic.trim();
  const phone = normalizePhone(form.value.phone);

  if (!firstName) {
    errors.first_name = 'Укажите имя';
  } else if (!NAME_REGEX.test(firstName)) {
    errors.first_name = 'Имя содержит недопустимые символы';
  }

  if (!lastName) {
    errors.last_name = 'Укажите фамилию';
  } else if (!NAME_REGEX.test(lastName)) {
    errors.last_name = 'Фамилия содержит недопустимые символы';
  }

  if (form.value.country_code === 'RU' && patronymic && !NAME_REGEX.test(patronymic)) {
    errors.patronymic = 'Отчество содержит недопустимые символы';
  }

  if (!form.value.phone.trim()) {
    errors.phone = 'Укажите телефон';
  } else if (!PHONE_REGEX.test(phone)) {
    errors.phone = 'Телефон должен быть в формате +7XXXXXXXXXX';
  }

  formErrors.value = errors;
  return Object.keys(errors).length === 0;
};

const handleSubmit = async () => {
  formError.value = '';
  if (!validateForm()) return;

  const payload = {
    first_name: form.value.first_name.trim(),
    last_name: form.value.last_name.trim(),
    phone: normalizePhone(form.value.phone),
    country_code: form.value.country_code,
    is_default: form.value.is_default,
  };
  if (form.value.country_code === 'RU' && form.value.patronymic.trim()) {
    payload.patronymic = form.value.patronymic.trim();
  }

  try {
    if (isEdit.value) {
      await editRecipient(editingId.value, payload);
      toast('Получатель обновлён', 'success');
    } else {
      await addRecipient(payload);
      toast('Получатель добавлен', 'success');
    }
    closeModal();
  } catch (err) {
    formError.value = err.response?.data?.detail || 'Не удалось сохранить получателя';
  }
};

const handleDelete = async (recipientId) => {
  if (!confirm('Удалить получателя?')) return;
  try {
    await removeRecipient(recipientId);
    toast('Получатель удалён', 'success');
  } catch (err) {
    toast(err.response?.data?.detail || 'Не удалось удалить получателя', 'error');
  }
};

const handleSetDefault = async (recipientId) => {
  try {
    await makeDefaultRecipient(recipientId);
    toast('Получатель по умолчанию обновлён', 'success');
  } catch (err) {
    toast(err.response?.data?.detail || 'Не удалось назначить получателя по умолчанию', 'error');
  }
};

onMounted(() => {
  loadRecipients();
});
</script>

<style scoped>
.profile-recipients {
  max-width: 600px;
  margin: 0 auto;
  padding: 16px 16px calc(24px + var(--bottom-nav-height, 56px) + env(safe-area-inset-bottom, 0px));
  min-height: 100vh;
  background: var(--color-bg);
}

.profile-recipients__header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.profile-recipients__back {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: none;
  background: var(--color-bg-white);
  color: var(--color-text);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.profile-recipients__title {
  flex: 1;
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text);
}

.profile-recipients__add {
  padding: 8px 14px;
  border-radius: 10px;
  border: none;
  background: var(--color-primary);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.profile-recipients__loading,
.profile-recipients__empty {
  text-align: center;
  padding: 40px 20px;
  color: var(--color-text-secondary);
  font-size: 14px;
}

.profile-recipients__empty-btn {
  margin-top: 16px;
  padding: 12px 20px;
  border-radius: 12px;
  background: var(--color-primary);
  color: #fff;
  font-size: 15px;
  font-weight: 500;
}

.profile-recipients__list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.recipient-card {
  background: var(--color-bg-white);
  border-radius: 16px;
  padding: 16px;
  border: 2px solid transparent;
}

.recipient-card--default {
  border-color: var(--color-primary);
}

.recipient-card__main {
  margin-bottom: 12px;
}

.recipient-card__name {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 4px;
}

.recipient-card__name span {
  margin-left: 4px;
}

.recipient-card__phone {
  font-size: 14px;
  color: var(--color-text-secondary);
}

.recipient-card__badge {
  display: inline-block;
  margin-top: 8px;
  padding: 4px 10px;
  border-radius: 20px;
  background: #e8f0fe;
  color: var(--color-primary);
  font-size: 12px;
  font-weight: 500;
}

.recipient-card__actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.recipient-card__btn {
  padding: 8px 12px;
  border-radius: 10px;
  border: none;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}

.recipient-card__btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.recipient-card__btn--default {
  background: #e8f0fe;
  color: var(--color-primary);
}

.recipient-card__btn--edit {
  background: var(--color-bg);
  color: var(--color-text);
}

.recipient-card__btn--delete {
  background: #fff0f0;
  color: var(--color-danger);
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  z-index: 200;
}

@media (min-width: 640px) {
  .modal-overlay {
    align-items: center;
  }
}

.modal {
  background: var(--color-bg-white);
  width: 100%;
  max-width: 480px;
  max-height: 90vh;
  overflow-y: auto;
  border-radius: 20px 20px 0 0;
  padding: 20px 16px calc(24px + var(--bottom-nav-height, 60px) + env(safe-area-inset-bottom, 0px));
}

@media (min-width: 640px) {
  .modal {
    border-radius: 16px;
    padding: 24px;
  }
}

.modal__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.modal__header h3 {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text);
}

.modal__close {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--color-bg);
  border: none;
  font-size: 20px;
  color: var(--color-text);
  cursor: pointer;
}

.modal__form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field--checkbox {
  flex-direction: row;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--color-text);
  cursor: pointer;
}

.field--checkbox input {
  width: 18px;
  height: 18px;
  accent-color: var(--color-primary);
  flex-shrink: 0;
}

.field__label {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text);
}

.field__required {
  color: var(--color-danger);
}

.field__input {
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-white);
  font-size: 15px;
  color: var(--color-text);
  width: 100%;
}

.field__input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.field__input--error {
  border-color: var(--color-danger);
}

.field__error {
  font-size: 12px;
  color: var(--color-danger);
}

.form-error {
  padding: 10px 12px;
  border-radius: 10px;
  background: #fff0f0;
  color: var(--color-danger);
  font-size: 14px;
}

.modal__submit {
  width: 100%;
  padding: 14px;
  border-radius: 12px;
  background: var(--color-primary);
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  border: none;
  cursor: pointer;
}

.modal__submit:disabled {
  opacity: 0.6;
}
</style>
