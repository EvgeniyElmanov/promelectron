import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import { ref } from 'vue';
import ProfileRecipients from '../views/ProfileRecipients.vue';

const mockRecipients = ref([]);
const mockLoading = ref(false);
const mockLoadRecipients = vi.fn();
const mockAddRecipient = vi.fn();
const mockEditRecipient = vi.fn();
const mockRemoveRecipient = vi.fn();
const mockMakeDefaultRecipient = vi.fn();

vi.mock('@/composables/useRecipients', () => ({
  useRecipients: () => ({
    recipients: mockRecipients,
    loading: mockLoading,
    loadRecipients: mockLoadRecipients,
    addRecipient: mockAddRecipient,
    editRecipient: mockEditRecipient,
    removeRecipient: mockRemoveRecipient,
    makeDefaultRecipient: mockMakeDefaultRecipient,
  }),
}));

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ add: vi.fn() }),
}));

const router = createRouter({
  history: createWebHistory(),
  routes: [{ path: '/profile/recipients', component: ProfileRecipients }],
});

describe('ProfileRecipients.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRecipients.value = [];
    mockLoading.value = false;
  });

  const mountComponent = async () => {
    await router.push('/profile/recipients');
    await router.isReady();
    return mount(ProfileRecipients, { global: { plugins: [router] } });
  };

  it('отображает заголовок страницы', async () => {
    const wrapper = await mountComponent();
    await flushPromises();

    expect(wrapper.text()).toContain('Получатели');
    expect(wrapper.find('[data-testid="recipient-add-btn"]').exists()).toBe(true);
  });

  it('показывает empty-state, когда нет получателей', async () => {
    const wrapper = await mountComponent();
    await flushPromises();

    expect(wrapper.find('[data-testid="recipients-empty"]').exists()).toBe(true);
    expect(wrapper.text()).toContain('У вас пока нет сохранённых получателей');
  });

  it('отображает список получателей', async () => {
    mockRecipients.value = [
      {
        id: 1,
        first_name: 'Иван',
        last_name: 'Иванов',
        patronymic: 'Иванович',
        phone: '+79990001122',
        country_code: 'RU',
        is_default: true,
      },
    ];
    const wrapper = await mountComponent();
    await flushPromises();

    expect(wrapper.find('[data-testid="recipient-card-1"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="recipient-card-name"]').text()).toContain('Иванов Иван');
    expect(wrapper.find('[data-testid="recipient-card-phone"]').text()).toBe('+79990001122');
  });

  it('открывает модалку создания по клику', async () => {
    const wrapper = await mountComponent();
    await flushPromises();

    await wrapper.find('[data-testid="recipient-add-btn"]').trigger('click');
    await flushPromises();

    expect(wrapper.text()).toContain('Новый получатель');
    expect(wrapper.find('[data-testid="recipient-form-first-name"]').exists()).toBe(true);
  });

  it('создаёт нового получателя', async () => {
    mockAddRecipient.mockResolvedValue({ id: 3 });
    const wrapper = await mountComponent();
    await flushPromises();

    await wrapper.find('[data-testid="recipient-add-btn"]').trigger('click');
    await flushPromises();

    wrapper.vm.form.first_name = 'Иван';
    wrapper.vm.form.last_name = 'Иванов';
    wrapper.vm.form.patronymic = 'Иванович';
    wrapper.vm.form.phone = '+79990001122';
    await flushPromises();

    await wrapper.find('form').trigger('submit');
    await flushPromises();

    expect(mockAddRecipient).toHaveBeenCalledWith(expect.objectContaining({
      first_name: 'Иван',
      last_name: 'Иванов',
      patronymic: 'Иванович',
      phone: '+79990001122',
      country_code: 'RU',
      is_default: false,
    }));
  });

  it('редактирует получателя', async () => {
    mockRecipients.value = [
      {
        id: 1,
        first_name: 'Иван',
        last_name: 'Иванов',
        patronymic: 'Иванович',
        phone: '+79990001122',
        country_code: 'RU',
        is_default: false,
      },
    ];
    mockEditRecipient.mockResolvedValue({ id: 1, first_name: 'Пётр' });
    const wrapper = await mountComponent();
    await flushPromises();

    await wrapper.find('[data-testid="recipient-edit-1"]').trigger('click');
    await flushPromises();

    expect(wrapper.text()).toContain('Редактировать получателя');

    wrapper.vm.form.first_name = 'Пётр';
    await flushPromises();

    await wrapper.find('form').trigger('submit');
    await flushPromises();

    expect(mockEditRecipient).toHaveBeenCalledWith(1, expect.objectContaining({
      first_name: 'Пётр',
    }));
  });

  it('удаляет получателя после подтверждения', async () => {
    mockRecipients.value = [
      {
        id: 1,
        first_name: 'Иван',
        last_name: 'Иванов',
        patronymic: 'Иванович',
        phone: '+79990001122',
        country_code: 'RU',
        is_default: false,
      },
    ];
    mockRemoveRecipient.mockResolvedValue({});
    vi.stubGlobal('confirm', () => true);
    const wrapper = await mountComponent();
    await flushPromises();

    await wrapper.find('[data-testid="recipient-delete-1"]').trigger('click');
    await flushPromises();

    expect(mockRemoveRecipient).toHaveBeenCalledWith(1);
  });

  it('назначает получателя по умолчанию', async () => {
    mockRecipients.value = [
      {
        id: 1,
        first_name: 'Иван',
        last_name: 'Иванов',
        patronymic: 'Иванович',
        phone: '+79990001122',
        country_code: 'RU',
        is_default: false,
      },
    ];
    mockMakeDefaultRecipient.mockResolvedValue({});
    const wrapper = await mountComponent();
    await flushPromises();

    await wrapper.find('[data-testid="recipient-set-default-1"]').trigger('click');
    await flushPromises();

    expect(mockMakeDefaultRecipient).toHaveBeenCalledWith(1);
  });
});
