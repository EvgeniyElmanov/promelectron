import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useRecipients } from '@/composables/useRecipients';

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPatch = vi.fn();
const mockDelete = vi.fn();

vi.mock('@/services/api', () => ({
  default: {
    get: (...args) => mockGet(...args),
    post: (...args) => mockPost(...args),
    patch: (...args) => mockPatch(...args),
    delete: (...args) => mockDelete(...args),
  },
}));

const mockRecipient = {
  id: 1,
  first_name: 'Иван',
  last_name: 'Иванов',
  patronymic: 'Иванович',
  phone: '+79990001122',
  country_code: 'RU',
  is_default: false,
};

describe('useRecipients', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('loads recipients', async () => {
    mockGet.mockResolvedValue({ data: [mockRecipient] });
    const { recipients, loadRecipients } = useRecipients();

    await loadRecipients();

    expect(mockGet).toHaveBeenCalledWith('/me/recipients/');
    expect(recipients.value).toEqual([mockRecipient]);
  });

  it('creates a recipient', async () => {
    mockPost.mockResolvedValue({ data: { ...mockRecipient, id: 2 } });
    const { recipients, addRecipient } = useRecipients();

    const result = await addRecipient(mockRecipient);

    expect(mockPost).toHaveBeenCalledWith('/me/recipients/', mockRecipient);
    expect(recipients.value).toContainEqual(expect.objectContaining({ id: 2 }));
    expect(result.id).toBe(2);
  });

  it('creating a default recipient resets is_default on others', async () => {
    mockPost.mockResolvedValue({ data: { ...mockRecipient, id: 3, is_default: true } });
    const { recipients, addRecipient } = useRecipients();
    recipients.value = [
      { ...mockRecipient, id: 1, is_default: true },
      { ...mockRecipient, id: 2, is_default: false },
    ];

    await addRecipient({ ...mockRecipient, is_default: true });

    expect(recipients.value.find((r) => r.id === 1).is_default).toBe(false);
    expect(recipients.value.find((r) => r.id === 2).is_default).toBe(false);
    expect(recipients.value.find((r) => r.id === 3).is_default).toBe(true);
  });

  it('updates a recipient', async () => {
    mockPatch.mockResolvedValue({ data: { ...mockRecipient, first_name: 'Пётр' } });
    const { recipients, editRecipient } = useRecipients();
    recipients.value = [{ ...mockRecipient }];

    await editRecipient(1, { first_name: 'Пётр' });

    expect(mockPatch).toHaveBeenCalledWith('/me/recipients/1/', { first_name: 'Пётр' });
    expect(recipients.value[0].first_name).toBe('Пётр');
  });

  it('editing a recipient to default resets is_default on others', async () => {
    mockPatch.mockResolvedValue({ data: { ...mockRecipient, id: 2, is_default: true } });
    const { recipients, editRecipient } = useRecipients();
    recipients.value = [
      { ...mockRecipient, id: 1, is_default: true },
      { ...mockRecipient, id: 2, is_default: false },
    ];

    await editRecipient(2, { is_default: true });

    expect(recipients.value.find((r) => r.id === 1).is_default).toBe(false);
    expect(recipients.value.find((r) => r.id === 2).is_default).toBe(true);
  });

  it('deletes a recipient', async () => {
    mockDelete.mockResolvedValue({ data: {} });
    const { recipients, removeRecipient } = useRecipients();
    recipients.value = [{ ...mockRecipient }];

    await removeRecipient(1);

    expect(mockDelete).toHaveBeenCalledWith('/me/recipients/1/');
    expect(recipients.value).toHaveLength(0);
  });

  it('sets default recipient', async () => {
    mockPost.mockResolvedValue({ data: { ...mockRecipient, is_default: true } });
    const { recipients, makeDefaultRecipient } = useRecipients();
    recipients.value = [
      { ...mockRecipient, id: 1, is_default: false },
      { ...mockRecipient, id: 2, is_default: true },
    ];

    await makeDefaultRecipient(1);

    expect(mockPost).toHaveBeenCalledWith('/me/recipients/1/set-default/');
    expect(recipients.value.find((r) => r.id === 1).is_default).toBe(true);
    expect(recipients.value.find((r) => r.id === 2).is_default).toBe(false);
  });

  it('exposes defaultRecipient computed', async () => {
    mockGet.mockResolvedValue({ data: [{ ...mockRecipient, is_default: true }] });
    const { defaultRecipient, loadRecipients } = useRecipients();

    await loadRecipients();

    expect(defaultRecipient.value).toEqual(expect.objectContaining({ is_default: true }));
  });
});
