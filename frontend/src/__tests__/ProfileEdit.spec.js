import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import ProfileEdit from '@/views/ProfileEdit.vue'

const mockProfile = {
  first_name: 'Иван',
  last_name: 'Петров',
  patronymic: 'Петрович',
  country_code: 'RU',
  email: 'ivan@example.com',
  phone: '+79990001122',
  email_verified: true,
}

const mockSetAuth = vi.fn()
const mockSetUser = vi.fn()
const mockToast = vi.fn()
const mockUploadAvatar = vi.fn()

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn((url) => {
      if (url === '/auth/profile') {
        return Promise.resolve({ data: mockProfile })
      }
      return Promise.resolve({ data: {} })
    }),
    patch: vi.fn(() => Promise.resolve({ data: { ...mockProfile, first_name: 'Пётр' } })),
    post: vi.fn(() => Promise.resolve({ data: {} })),
  },
}))

vi.mock('@/api/users', () => ({
  uploadAvatar: (...args) => mockUploadAvatar(...args),
}))

vi.mock('@/composables/useAuth', () => ({
  useAuth: () => ({
    setAuth: mockSetAuth,
    setUser: mockSetUser,
    emailVerified: { value: true },
  }),
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({
    add: mockToast,
  }),
}))

function createFile(name = 'avatar.png', type = 'image/png') {
  return new File(['dummy'], name, { type })
}

function createWrapper() {
  const router = createRouter({
    history: createWebHistory(),
    routes: [{ path: '/profile/edit', component: ProfileEdit }],
  })
  return mount(ProfileEdit, {
    global: { plugins: [router] },
  })
}

describe('ProfileEdit.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUploadAvatar.mockReset()
    mockToast.mockReset()
    Object.defineProperty(window, 'localStorage', {
      value: {
        getItem: vi.fn(() => 'test-token'),
        setItem: vi.fn(),
        removeItem: vi.fn(),
      },
      writable: true,
    })
  })

  it('отображает заголовок страницы', async () => {
    const wrapper = createWrapper()
    await vi.waitFor(() => {
      expect(wrapper.text()).toContain('Редактирование профиля')
    })
  })

  it('загружает и отображает данные пользователя', async () => {
    const wrapper = createWrapper()

    await vi.waitFor(() => {
      expect(wrapper.find('[data-testid="edit-profile-first-name"]').element.value).toBe('Иван')
      expect(wrapper.find('[data-testid="edit-profile-last-name"]').element.value).toBe('Петров')
      expect(wrapper.find('[data-testid="edit-profile-patronymic"]').element.value).toBe('Петрович')
      expect(wrapper.find('[data-testid="edit-profile-country-code"]').element.value).toBe('RU')
      expect(wrapper.find('[data-testid="edit-profile-email"]').element.value).toBe('ivan@example.com')
      expect(wrapper.find('[data-testid="edit-profile-phone"]').element.value).toBe('+79990001122')
    })
  })

  it('содержит форму смены пароля', async () => {
    const wrapper = createWrapper()

    await vi.waitFor(() => {
      expect(wrapper.find('[data-testid="edit-profile-old-password"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="edit-profile-new-password"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="edit-profile-confirm-password"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="edit-profile-password-save"]').exists()).toBe(true)
    })
  })

  it('валидирует телефон в формате +7XXXXXXXXXX', async () => {
    const wrapper = createWrapper()
    await vi.waitFor(() => expect(wrapper.find('[data-testid="edit-profile-phone"]').exists()).toBe(true))

    await wrapper.find('[data-testid="edit-profile-phone"]').setValue('abc')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('[data-testid="edit-profile-phone-error"]').text()).toContain('+7')
  })

  it('валидирует имя и фамилию на недопустимые символы', async () => {
    const wrapper = createWrapper()
    await vi.waitFor(() => expect(wrapper.find('[data-testid="edit-profile-first-name"]').exists()).toBe(true))

    await wrapper.find('[data-testid="edit-profile-first-name"]').setValue('Иван123')
    await wrapper.find('[data-testid="edit-profile-last-name"]').setValue('')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('[data-testid="edit-profile-first-name-error"]').text()).toContain('недопустимые символы')
    expect(wrapper.find('[data-testid="edit-profile-last-name-error"]').text()).toContain('Введите фамилию')
  })

  it('нормализует телефон перед отправкой', async () => {
    const wrapper = createWrapper()
    await vi.waitFor(() => expect(wrapper.find('[data-testid="edit-profile-phone"]').exists()).toBe(true))

    await wrapper.find('[data-testid="edit-profile-phone"]').setValue('8 (999) 000-11-22')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('[data-testid="edit-profile-phone-error"]').exists()).toBe(false)
  })

  it('отображает статус подтверждения email', async () => {
    const wrapper = createWrapper()
    await vi.waitFor(() => expect(wrapper.find('[data-testid="edit-profile-email-status"]').exists()).toBe(true))

    expect(wrapper.find('[data-testid="edit-profile-email-status"]').text()).toContain('Подтверждён')
  })

  it('показывает предупреждение при смене email', async () => {
    const wrapper = createWrapper()
    await vi.waitFor(() => expect(wrapper.find('[data-testid="edit-profile-email"]').exists()).toBe(true))

    expect(wrapper.find('[data-testid="edit-profile-email-warning"]').exists()).toBe(false)

    await wrapper.find('[data-testid="edit-profile-email"]').setValue('new@example.com')
    await flushPromises()

    expect(wrapper.find('[data-testid="edit-profile-email-warning"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="edit-profile-email-warning"]').text()).toContain('повторное подтверждение')
  })

  it('успешно загружает аватар, обновляет превью и показывает toast', async () => {
    const wrapper = createWrapper()
    await vi.waitFor(() => expect(wrapper.find('[data-testid="edit-profile-first-name"]').exists()).toBe(true))

    const avatarUrl = 'https://example.com/avatars/1/original.png'
    mockUploadAvatar.mockResolvedValue({
      data: {
        avatar_url: avatarUrl,
        original: avatarUrl,
        small: 'https://example.com/avatars/1/small.webp',
        medium: 'https://example.com/avatars/1/medium.webp',
        large: 'https://example.com/avatars/1/large.webp',
      },
    })

    const input = wrapper.find('input[type="file"]')
    const file = createFile()
    await input.setValue('')
    Object.defineProperty(input.element, 'files', {
      value: [file],
      writable: false,
    })
    await input.trigger('change')
    await flushPromises()
    await vi.waitFor(() => expect(mockUploadAvatar).toHaveBeenCalled())

    expect(mockUploadAvatar).toHaveBeenCalledTimes(1)
    expect(wrapper.find('.avatar-preview__img').exists()).toBe(true)
    expect(wrapper.find('.avatar-preview__img').attributes('src')).toBe(avatarUrl)
    expect(mockToast).toHaveBeenCalledWith('Фото профиля обновлено', 'success')
    expect(mockSetAuth).toHaveBeenCalledWith('test-token', expect.objectContaining({ avatar_url: avatarUrl }))
  })

  it('при ошибке загрузки аватара показывает toast и не использует passwordError', async () => {
    const wrapper = createWrapper()
    await vi.waitFor(() => expect(wrapper.find('[data-testid="edit-profile-first-name"]').exists()).toBe(true))

    mockUploadAvatar.mockRejectedValue({
      response: { data: { detail: 'Недопустимый формат файла' } },
    })

    const input = wrapper.find('input[type="file"]')
    const file = createFile()
    Object.defineProperty(input.element, 'files', {
      value: [file],
      writable: false,
    })
    await input.trigger('change')
    await flushPromises()
    await vi.waitFor(() => expect(mockUploadAvatar).toHaveBeenCalled())

    expect(wrapper.find('[data-testid="avatar-upload-error"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="avatar-upload-error"]').text()).toContain('Недопустимый формат файла')
    expect(mockToast).toHaveBeenCalledWith('Недопустимый формат файла', 'error')
    expect(wrapper.find('.edit-card--avatar .error-msg').exists()).toBe(true)
  })
})
