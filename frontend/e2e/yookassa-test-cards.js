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
    name: 'Mir 3DS',
    number: '2200000000000004',
    has3ds: true,
  },
  {
    name: 'Mir no 3DS',
    number: '2202474301322987',
    has3ds: false,
  },
];

export const FAILED_CARDS = [
  {
    name: 'Insufficient funds',
    number: '2200000000000053',
    reason: 'insufficient_funds',
    label: 'Недостаточно средств на карте',
  },
  {
    name: 'Invalid CSC',
    number: '2200770212727079',
    reason: 'invalid_csc',
    label: 'Неверный код безопасности карты',
  },
  {
    name: 'Card expired',
    number: '2200000000000038',
    reason: 'card_expired',
    label: 'Истёк срок действия карты',
  },
  {
    name: 'Fraud suspected',
    number: '2200000000000046',
    reason: 'fraud_suspected',
    label: 'Платёж отклонён по соображениям безопасности',
  },
  {
    name: 'General decline',
    number: '2202202212312379',
    reason: 'general_decline',
    label: 'Платёж отклонён банком',
  },
];

export const DEFAULT_CARD_EXPIRY = {
  month: '12',
  year: '30',
  cvc: '000',
};
