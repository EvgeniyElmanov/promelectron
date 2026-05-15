<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <div class="modal__header">
        <h3 class="modal__title">{{ isEdit ? 'Редактировать товар' : 'Новый товар' }}</h3>
        <button class="modal__close" @click="$emit('close')">&times;</button>
      </div>

      <form class="modal__form" @submit.prevent="handleSubmit">
        <div class="field">
          <label class="field__label">Название <span class="required">*</span></label>
          <input
            v-model="form.name"
            type="text"
            class="field__input"
            placeholder="Например, Смартфон Pro"
            required
          />
        </div>

        <div class="field">
          <label class="field__label">Описание</label>
          <textarea
            v-model="form.description"
            class="field__input field__input--textarea"
            rows="3"
            placeholder="Описание товара..."
          />
        </div>

        <div class="field-row">
          <div class="field">
            <label class="field__label">Цена (₽) <span class="required">*</span></label>
            <input
              v-model.number="form.price"
              type="number"
              class="field__input"
              min="0"
              step="0.01"
              required
            />
          </div>

          <div class="field">
            <label class="field__label">В наличии <span class="required">*</span></label>
            <input
              v-model.number="form.stock"
              type="number"
              class="field__input"
              min="0"
              required
            />
          </div>
        </div>

        <div class="field">
          <label class="field__label">Категория <span class="required">*</span></label>
          <select v-model.number="form.category_id" class="field__input" required>
            <option value="" disabled>Выберите категорию</option>
            <option v-for="cat in categories" :key="cat.id" :value="cat.id">
              {{ cat.name }}
            </option>
          </select>
        </div>

        <label class="checkbox">
          <input v-model="form.is_active" type="checkbox" />
          <span>Активен (виден на витрине)</span>
        </label>

        <div v-if="error" class="form-error">{{ error }}</div>

        <button type="submit" class="modal__submit" :disabled="submitting">
          {{ submitting ? 'Сохранение...' : (isEdit ? 'Сохранить' : 'Создать') }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import api from '@/services/api';

const props = defineProps({
  product: { type: Object, default: null },
});

const emit = defineEmits(['close', 'saved']);

const isEdit = !!props.product;

const form = ref({
  name: props.product?.name || '',
  description: props.product?.description || '',
  price: props.product?.price || 0,
  stock: props.product?.stock || 0,
  category_id: props.product?.category_id || '',
  is_active: props.product?.is_active ?? true,
});

const categories = ref([]);
const error = ref('');
const submitting = ref(false);

onMounted(async () => {
  try {
    const { data } = await api.get('/categories');
    categories.value = data;
  } catch {
    // silently fail
  }
});

const handleSubmit = async () => {
  error.value = '';
  submitting.value = true;
  try {
    if (isEdit) {
      await api.put(`/products/${props.product.id}`, form.value);
    } else {
      await api.post('/products/', form.value);
    }
    emit('saved');
    emit('close');
  } catch (err) {
    error.value = err.response?.data?.detail || 'Ошибка сохранения';
  } finally {
    submitting.value = false;
  }
};
</script>

<style scoped>
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
  padding: 20px 16px calc(24px + var(--bottom-nav-height, 60px));
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

.modal__title {
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
  display: flex;
  align-items: center;
  justify-content: center;
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

.field__label {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text);
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

.field__input--textarea {
  resize: vertical;
  min-height: 80px;
}

.field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.required {
  color: var(--color-danger);
}

.checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--color-text);
  cursor: pointer;
}

.checkbox input {
  width: 18px;
  height: 18px;
  accent-color: var(--color-primary);
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
  margin-top: 4px;
}

.modal__submit:disabled {
  opacity: 0.6;
}
</style>
