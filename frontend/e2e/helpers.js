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
  overlay: '[data-qa="overlay"], [class*="overlay"], [class*="spinner"], [class*="loading"]',
  threeDSFrame: 'iframe, .three-d-secure, text=Подтвердите, text=Confirm, text=Card authentication',
  errorMessage: 'text=/payment declined|отклонён|declined|ошибка|error/i',
};

async function waitForOverlayToDisappear(page, timeout = 5000) {
  const overlay = page.locator(YOO_KASSA_SELECTORS.overlay).first();
  try {
    await overlay.waitFor({ state: 'hidden', timeout });
  } catch {
    // Overlay may still be present; callers should use force/JS click as fallback.
  }
}

async function clickElementRobustly(locator, options = {}) {
  const { timeout = 5000, forceTimeout = 2000, jsFallback = true } = options;
  await expect(locator).toBeVisible({ timeout });

  try {
    await locator.click({ timeout: forceTimeout });
    return;
  } catch {
    // Normal click failed (e.g. intercepted by overlay); try force click.
  }

  try {
    await locator.click({ force: true, timeout: forceTimeout });
    return;
  } catch {
    // Force click also failed; fall back to JS click if allowed.
  }

  if (jsFallback) {
    await locator.evaluate((el) => el.click());
  } else {
    throw new Error('Could not click element robustly');
  }
}

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
  await clickElementRobustly(submitButton, { timeout: 5000, forceTimeout: 3000 });
}

async function exitYooKassaPage(page) {
  const backButton = page.locator(YOO_KASSA_SELECTORS.backButton).first();
  await expect(backButton).toBeVisible({ timeout: 15000 });

  // YooKassa may show a loading/3-D Secure overlay after form submission.
  // Wait briefly for it to disappear before attempting a normal click.
  await waitForOverlayToDisappear(page, 3000);

  await clickElementRobustly(backButton, {
    timeout: 5000,
    forceTimeout: 3000,
    jsFallback: true,
  });
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
    return true;
  }

  await fillYooKassaCardForm(page, card);
  await submitYooKassaForm(page);

  // After submission YooKassa may:
  //   1. redirect straight back to the merchant success page,
  //   2. show a 3-D Secure challenge,
  //   3. show a loading overlay and then the "back to website" link.
  // Wait for any of these outcomes.
  const successPromise = page.waitForURL(/\/payment\/success/, { timeout: 20000 }).then(() => 'success');
  const threeDSPromise = page
    .locator(YOO_KASSA_SELECTORS.threeDSFrame)
    .first()
    .waitFor({ state: 'visible', timeout: 20000 })
    .then(() => '3ds');
  const backButtonPromise = page
    .locator(YOO_KASSA_SELECTORS.backButton)
    .first()
    .waitFor({ state: 'visible', timeout: 20000 })
    .then(() => 'back');

  const outcome = await Promise.race([successPromise, threeDSPromise, backButtonPromise]).catch(
    () => 'timeout'
  );

  if (outcome === 'success') {
    return true;
  }

  if (outcome === '3ds') {
    // 3-D Secure cannot be reliably completed in automated environments.
    return false;
  }

  // Loading overlay may still be visible; wait a bit more before clicking back.
  await waitForOverlayToDisappear(page, 3000);

  if (outcome === 'back') {
    await exitYooKassaPage(page);
    return true;
  }

  // Fallback: try to exit the YooKassa page anyway.
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

  // Declined cards usually show an error and stay on YooKassa, but some test
  // flows redirect back automatically. Wait for either outcome.
  try {
    await page.waitForURL(/\/payment\/failed/, { timeout: 15000 });
    return true;
  } catch {
    // Stayed on YooKassa: click the back link to return to the merchant site.
    // The PaymentSuccess page will sync the payment status and redirect to
    // /payment/failed because cancellation_reason is populated.
    await exitYooKassaPage(page);
    return true;
  }
}
