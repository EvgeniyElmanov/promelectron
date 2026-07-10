import { expect } from '@playwright/test';
import {
  DEFAULT_CARD_EXPIRY,
  SUCCESSFUL_CARDS,
} from './yookassa-test-cards.js';

export async function goToCart(page) {
  const headerLink = page.locator('[data-testid="cart-link"]');
  const bottomNavItem = page.locator('[data-testid="nav-Корзина"]');
  if (await headerLink.isVisible().catch(() => false)) {
    await headerLink.click();
  } else {
    await bottomNavItem.click();
  }
}

export async function goToProfile(page) {
  const headerLink = page.locator('[data-testid="profile-link"]');
  const bottomNavItem = page.locator('[data-testid="nav-Профиль"]');
  if (await headerLink.isVisible().catch(() => false)) {
    await headerLink.click();
  } else {
    await bottomNavItem.click();
  }
}

export function isYooKassaPage(page) {
  const url = page.url();
  return url.includes('yoomoney.ru') || url.includes('yookassa.ru');
}

export async function expectYooKassaPageOrSkip(page) {
  try {
    await page.waitForURL(/yoomoney\.ru|yookassa\.ru/, { timeout: 10000 });
  } catch {
    // YooKassa is not configured or redirect is blocked in this environment.
    // Skip the rest of the test gracefully.
    return false;
  }
  return true;
}

const YOO_KASSA_SELECTORS = {
  newCardOption: 'text=New card',
  cardNumberInput:
    'input[name="cardNumber"], input[autocomplete="cc-number"], input[placeholder*="0000"], input[inputmode="numeric"]',
  monthInput: 'input[placeholder="MM"], input[name="expiryMonth"]',
  yearInput: 'input[name="expiryYear"], input[placeholder="YY"], input[placeholder="ГГ"]',
  expiryInput: 'input[placeholder="MM/YY"], input[placeholder="ММ/ГГ"], input[name="expiry"], input[autocomplete="cc-exp"]',
  cvcInput: 'input[placeholder="CVC"], input[autocomplete="cc-csc"]',
  submitButton:
    'button[type="submit"], button:has-text("Оплатить"), button:has-text("Pay"), input[type="submit"]',
  backButton:
    'button:has-text("Back to the website"), a:has-text("Back to the website"), a:has-text("Exit the payment process"), button:has-text("Exit the payment process")',
};

async function selectNewCardIfNeeded(page) {
  await page.waitForTimeout(2000);
  const newCardOption = page.locator(YOO_KASSA_SELECTORS.newCardOption).first();
  if (await newCardOption.isVisible().catch(() => false)) {
    await newCardOption.click();
  }
  await page.waitForTimeout(1000);
}

async function fillYooKassaCardForm(page, card) {
  await selectNewCardIfNeeded(page);

  const cardNumberInput = page.locator(YOO_KASSA_SELECTORS.cardNumberInput).first();
  await expect(cardNumberInput).toBeVisible({ timeout: 10000 });
  await cardNumberInput.fill(card.number);

  const combinedExpiryInput = page.locator(YOO_KASSA_SELECTORS.expiryInput).first();
  if (await combinedExpiryInput.isVisible().catch(() => false)) {
    await expect(combinedExpiryInput).toBeVisible({ timeout: 5000 });
    await combinedExpiryInput.fill(`${DEFAULT_CARD_EXPIRY.month}/${DEFAULT_CARD_EXPIRY.year}`);
  } else {
    const monthInput = page.locator(YOO_KASSA_SELECTORS.monthInput).first();
    await expect(monthInput).toBeVisible({ timeout: 5000 });
    await monthInput.fill(DEFAULT_CARD_EXPIRY.month);

    // Fallback: if a dedicated year input is present, fill it; otherwise the
    // combined expiry input already received the full value above.
    const yearInput = page.locator(YOO_KASSA_SELECTORS.yearInput).first();
    if (await yearInput.isVisible().catch(() => false)) {
      await yearInput.fill(DEFAULT_CARD_EXPIRY.year);
    }
  }

  const cvcInput = page.locator(YOO_KASSA_SELECTORS.cvcInput).first();
  await expect(cvcInput).toBeVisible({ timeout: 5000 });
  await cvcInput.fill(DEFAULT_CARD_EXPIRY.cvc);
}

async function submitYooKassaForm(page) {
  const submitButton = page.locator(YOO_KASSA_SELECTORS.submitButton).first();
  await expect(submitButton).toBeVisible({ timeout: 5000 });
  await submitButton.click();
}

async function exitYooKassaPage(page) {
  const backButton = page.locator(YOO_KASSA_SELECTORS.backButton).first();
  await expect(backButton).toBeVisible({ timeout: 15000 });
  await backButton.click();
}

/**
 * Complete YooKassa test-card payment if the browser was redirected to YooKassa.
 * Does nothing when the app is using mock payments (local dev).
 *
 * @param {import('@playwright/test').Page} page
 * @param {Object} [card] - Card from SUCCESSFUL_CARDS. Defaults to the no-3DS
 *   Mastercard test card to preserve backward compatibility.
 */
export async function completeYooKassaPaymentIfNeeded(
  page,
  card = SUCCESSFUL_CARDS[1],
) {
  await page.waitForLoadState('networkidle');

  if (!isYooKassaPage(page)) {
    return;
  }

  await fillYooKassaCardForm(page, card);
  await submitYooKassaForm(page);

  // 3-D Secure test flow is best-effort in automated environments.
  if (card.has3ds) {
    const has3dsFrame = await page
      .locator('iframe, .three-d-secure, text=Подтвердите, text=Confirm')
      .first()
      .isVisible()
      .catch(() => false);
    if (has3dsFrame) {
      // Automated completion is not reliable for 3-D Secure; caller should
      // treat this as skipped.
      return false;
    }
  }

  await exitYooKassaPage(page);
  return true;
}

/**
 * Complete a YooKassa failed-card payment scenario.
 *
 * @param {import('@playwright/test').Page} page
 * @param {Object} card - Card from FAILED_CARDS.
 */
export async function completeYooKassaFailedPaymentIfNeeded(page, card) {
  await page.waitForLoadState('networkidle');

  if (!isYooKassaPage(page)) {
    return false;
  }

  await fillYooKassaCardForm(page, card);
  await submitYooKassaForm(page);

  // Most declined cards redirect back automatically, but the YooKassa UI may
  // require clicking the back button. Wait briefly, then fall back to it.
  try {
    await page.waitForURL(/\/payment\/failed/, { timeout: 15000 });
  } catch {
    await exitYooKassaPage(page);
  }

  return true;
}
