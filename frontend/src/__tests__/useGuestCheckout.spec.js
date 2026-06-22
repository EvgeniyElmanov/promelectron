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
      phone: 'abc',
    });
    expect(errors.phone).toContain('+7');
  });
});
