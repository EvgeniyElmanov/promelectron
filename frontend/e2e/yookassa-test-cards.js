/**
 * YooKassa test-card numbers and helpers.
 *
 * These values must NEVER be imported into production source code
 * (src/**). They live only in E2E specs and helpers.
 *
 * Source: https://yookassa.ru/developers/payment-acceptance/testing-and-going-live/testing
 */

export const SUCCESSFUL_CARDS = [
  {
    name: 'Mastercard 3DS',
    number: '5555555555554477',
    has3ds: true,
  },
  {
    name: 'Mastercard no 3DS',
    number: '5555555555554444',
    has3ds: false,
  },
  {
    name: 'Visa no 3DS',
    number: '4111111111111111',
    has3ds: false,
  },
  {
    name: 'Mir 3DS',
    number: '2200000000000004',
    has3ds: true,
  },
];

export const FAILED_CARDS = [
  {
    name: 'Insufficient funds',
    number: '5555555555554600',
    reason: 'insufficient_funds',
    label: 'Недостаточно средств на карте',
  },
  {
    name: 'Invalid CSC',
    number: '5555555555554626',
    reason: 'invalid_csc',
    label: 'Неверный код безопасности карты',
  },
  {
    name: 'Card expired',
    number: '5555555555554543',
    reason: 'card_expired',
    label: 'Истёк срок действия карты',
  },
  {
    name: 'Fraud suspected',
    number: '5555555555554576',
    reason: 'fraud_suspected',
    label: 'Платёж отклонён по соображениям безопасности',
  },
  {
    name: 'General decline',
    number: '5555555555554550',
    reason: 'general_decline',
    label: 'Платёж отклонён банком',
  },
];

export const DEFAULT_CARD_EXPIRY = {
  month: '12',
  year: '30',
  cvc: '000',
};
