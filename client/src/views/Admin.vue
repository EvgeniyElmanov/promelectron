<template>
  <div class="admin" data-testid="admin-page">
    <h1 class="admin__title">Панель администратора</h1>

    <div class="admin__section">
      <div class="admin__section-header">
        <h2 class="admin__section-title">Категории</h2>
        <button class="admin__btn admin__btn--primary" @click="openCreateModal">+ Добавить</button>
      </div>

      <div v-if="loading" class="admin__loading">Загрузка...</div>

      <div v-else-if="categories.length === 0" class="admin__empty">Нет категорий</div>

      <div v-else class="admin__table-wrapper">
        <table class="admin__table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Название</th>
              <th>Описание</th>
              <th class="admin__table-actions">Действия</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="cat in categories" :key="cat.id">
              <td>{{ cat.id }}</td>
              <td>{{ cat.name }}</td>
              <td>{{ cat.description || '—' }}</td>
              <td class="admin__table-actions">
                <button class="admin__icon-btn admin__icon-btn--edit" @click="openEditModal(cat)">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
                    <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
                  </svg>
                </button>
                <button class="admin__icon-btn admin__icon-btn--delete" @click="deleteCategory(cat.id)">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"/>
                    <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
                  </svg>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Modal -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <div class="modal__header">
          <h3>{{ isEdit ? 'Редактировать категорию' : 'Новая категория' }}</h3>
          <button class="modal__close" @click="closeModal">&times;</button>
        </div>
        <form class="modal__form" @submit.prevent="handleSubmit">
          <div class="field">
            <label class="field__label">Название <span class="required">*</span></label>
            <input v-model="form.name" class="field__input" placeholder="Например, Смартфоны" required />
          </div>
          <div class="field">
            <label class="field__label">Описание</label>
            <textarea v-model="form.description" class="field__input field__input--textarea" rows="3" placeholder="Описание категории..." />
          </div>
          <div v-if="error" class="form-error">{{ error }}</div>
          <button type="submit" class="modal__submit" :disabled="submitting">
            {{ submitting ? 'Сохранение...' : (isEdit ? 'Сохранить' : 'Создать') }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import api from '@/services/api';
import { useToast } from '@/composables/useToast';

const categories = ref([]);
const loading = ref(false);
const showModal = ref(false);
const isEdit = ref(false);
const editingId = ref(null);
const error = ref('');
const submitting = ref(false);
const { toast } = useToast();

const form = ref({ name: '', description: '' });

const fetchCategories = async () => {
  loading.value = true;
  try {
    const { data } = await api.get('/categories');
    categories.value = data;
  } catch {
    toast('Не удалось загрузить категории', 'error');
  } finally {
    loading.value = false;
  }
};

const openCreateModal = () => {
  isEdit.value = false;
  editingId.value = null;
  form.value = { name: '', description: '' };
  error.value = '';
  showModal.value = true;
};

const openEditModal = (cat) => {
  isEdit.value = true;
  editingId.value = cat.id;
  form.value = { name: cat.name, description: cat.description || '' };
  error.value = '';
  showModal.value = true;
};

const closeModal = () => {
  showModal.value = false;
};

const handleSubmit = async () => {
  error.value = '';
  submitting.value = true;
  try {
    if (isEdit.value) {
      await api.put(`/categories/${editingId.value}`, form.value);
      toast('Категория обновлена', 'success');
    } else {
      await api.post('/categories/', form.value);
      toast('Категория создана', 'success');
    }
    closeModal();
    fetchCategories();
  } catch (err) {
    error.value = err.response?.data?.detail || 'Ошибка сохранения';
  } finally {
    submitting.value = false;
  }
};

const deleteCategory = async (id) => {
  if (!confirm('Удалить категорию?')) return;
  try {
    await api.delete(`/categories/${id}`);
    toast('Категория удалена', 'success');
    fetchCategories();
  } catch (err) {
    toast(err.response?.data?.detail || 'Ошибка удаления', 'error');
  }
};

onMounted(fetchCategories);
</script>

<style scoped>
.admin {
  padding: 16px;
  min-height: 100vh;
  background: var(--color-bg);
}

.admin__title {
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: 20px;
}

.admin__section {
  background: var(--color-bg-white);
  border-radius: 16px;
  padding: 16px;
}

.admin__section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.admin__section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
}

.admin__btn {
  padding: 10px 16px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  border: none;
}

.admin__btn--primary {
  background: var(--color-primary);
  color: #fff;
}

.admin__loading,
.admin__empty {
  text-align: center;
  padding: 40px 20px;
  color: var(--color-text-secondary);
}

.admin__table-wrapper {
  overflow-x: auto;
}

.admin__table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.admin__table th,
.admin__table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid var(--color-border);
}

.admin__table th {
  font-weight: 600;
  color: var(--color-text-secondary);
  font-size: 13px;
}

.admin__table-actions {
  white-space: nowrap;
  width: 1%;
}

.admin__icon-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-right: 6px;
}

.admin__icon-btn--edit {
  background: #e8f0fe;
  color: var(--color-primary);
}

.admin__icon-btn--delete {
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

.required {
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
}

.modal__submit:disabled {
  opacity: 0.6;
}
</style>
