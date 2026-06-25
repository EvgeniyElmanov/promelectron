import { describe, it, expect } from 'vitest';
import { normalizePhone, useGuestCheckout } from '@/composables/useGuestCheckout';

describe('normalizePhone', () => {
  it('returns empty string for empty input', () => {
    expect(normalizePhone('')).toBe('');
    expect(normalizePhone(null)).toBe('');
    expect(normalizePhone(undefined)).toBe('');
  });

  it('keeps +7XXXXXXXXXX as is', () => {
    expect(normalizePhone('+79990001122')).toBe('+79990001122');
  });

  it('normalizes 10-digit number to +7', () => {
    expect(normalizePhone('9990001122')).toBe('+79990001122');
  });

  it('normalizes 11-digit number starting with 7 to +7', () => {
    expect(normalizePhone('79990001122')).toBe('+79990001122');
  });

  it('normalizes 11-digit number starting with 8 to +7', () => {
    expect(normalizePhone('8-999-000-11-22')).toBe('+79990001122');
    expect(normalizePhone('89990001122')).toBe('+79990001122');
  });

  it('strips formatting characters', () => {
    expect(normalizePhone('+7 (999) 000-11-22')).toBe('+79990001122');
  });

  it('returns original trimmed value for unsupported formats', () => {
    expect(normalizePhone('abc')).toBe('abc');
    expect(normalizePhone('+12345678901')).toBe('+12345678901');
    expect(normalizePhone('799900011222')).toBe('799900011222');
  });
});

describe('useGuestCheckout', () => {
  it('validateGuestForm accepts phone starting with 8', () => {
    const { validateGuestForm } = useGuestCheckout();
    const errors = validateGuestForm({
      email: 'test@example.com',
      firstName: 'Иван',
      lastName: 'Иванов',
      patronymic: 'Иванович',
      phone: '8-999-000-11-22',
    });
    expect(errors).toEqual({});
  });

  it('validateGuestForm rejects unsupported phone formats', () => {
    const { validateGuestForm } = useGuestCheckout();
    const errors = validateGuestForm({
      email: 'test@example.com',
      firstName: 'Иван',
      lastName: 'Иванов',
      patronymic: 'Иванович',
      phone: 'abc',
    });
    expect(errors.phone).toContain('+7');
  });

  it('validateGuestForm requires patronymic for RU', () => {
    const { validateGuestForm } = useGuestCheckout();
    const errors = validateGuestForm({
      email: 'test@example.com',
      firstName: 'Иван',
      lastName: 'Иванов',
      patronymic: '',
      phone: '+79990001122',
      countryCode: 'RU',
    });
    expect(errors.patronymic).toContain('Укажите отчество');
  });

  it('validateGuestForm skips patronymic for non-RU', () => {
    const { validateGuestForm } = useGuestCheckout();
    const errors = validateGuestForm({
      email: 'test@example.com',
      firstName: 'Иван',
      lastName: 'Иванов',
      patronymic: '',
      phone: '+79990001122',
      countryCode: 'KZ',
    });
    expect(errors).toEqual({});
  });

  it('buildGuestOrderPayload includes recipient fields', () => {
    const { buildGuestOrderPayload } = useGuestCheckout();
    const payload = buildGuestOrderPayload({
      items: [{ product_id: 1, quantity: 1 }],
      selectedDelivery: { tariff_code: 136 },
      email: 'Test@Example.com',
      firstName: 'Иван',
      lastName: 'Иванов',
      patronymic: 'Иванович',
      phone: '+79990001122',
      countryCode: 'RU',
      saveAddress: false,
    });
    expect(payload).toMatchObject({
      guest_email: 'test@example.com',
      guest_phone: '+79990001122',
      recipient_first_name: 'Иван',
      recipient_last_name: 'Иванов',
      recipient_patronymic: 'Иванович',
      recipient_phone: '+79990001122',
      recipient_country_code: 'RU',
    });
  });

  it('buildGuestOrderPayload omits patronymic for non-RU', () => {
    const { buildGuestOrderPayload } = useGuestCheckout();
    const payload = buildGuestOrderPayload({
      items: [{ product_id: 1, quantity: 1 }],
      selectedDelivery: { tariff_code: 136 },
      email: 'test@example.com',
      firstName: 'Иван',
      lastName: 'Иванов',
      patronymic: '',
      phone: '+79990001122',
      countryCode: 'KZ',
      saveAddress: false,
    });
    expect(payload.recipient_patronymic).toBeUndefined();
    expect(payload.recipient_country_code).toBe('KZ');
  });
});
