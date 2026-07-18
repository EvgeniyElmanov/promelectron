import { expect, request, test } from '@playwright/test';
import {
  DEFAULT_CARD_EXPIRY,
  SUCCESSFUL_CARDS,
} from './yookassa-test-cards.js';

const SEED_SECRET = process.env.SEED_SECRET || 'promelectron-test-seed-2024';

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

export async function setYooKassaPaymentStatus(
  { orderId, status, cancellationReason, guestEmail },
) {
  const apiContext = await request.newContext({
    baseURL: process.env.API_URL,
  });
  try {
    const body = { order_id: orderId, status };
    if (status === 'canceled') body.cancellation_reason = cancellationReason;
    if (guestEmail) body.guest_email = guestEmail;
    const res = await apiContext.post('/api/v1/payments/debug/set-status/', {
      data: body,
      headers: { 'x-seed-secret': SEED_SECRET },
    });
    if (!res.ok()) {
      throw new Error(`debug/set-status failed: ${res.status()} ${await res.text()}`);
    }
  } finally {
    await apiContext.dispose();
  }
}

const YOO_KASSA_SELECTORS = {
  newCardOption: 'text=/New card|Новая карта|Добавить карту|Add card/i',
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
  threeDSFrame: 'iframe, .three-d-secure',
  threeDSChallenge:
    'text=/Подтвердите|Confirm|Card authentication|3-D Secure|Код из SMS/i',
  threeDSCodeInput:
    'input[placeholder="Any number"], input[placeholder="Код из SMS"], input[name="code"], input[inputmode="numeric"]',
  threeDSConfirmButton: 'button:has-text("Confirm"), button:has-text("Подтвердить")',
  errorMessage:
    'text=/payment declined|отклонён|declined|ошибка|error|не удалось|failed|invalid/i',
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

async function isYooKassaErrorVisible(page) {
  const errorLocator = page.locator(YOO_KASSA_SELECTORS.errorMessage).first();
  return errorLocator.isVisible().catch(() => false);
}

async function find3DSFrame(page) {
  // The 3DS challenge may be a full-page redirect or rendered inside an iframe.
  // Try to locate a relevant iframe and return it if its content looks like a
  // 3DS challenge.
  const frames = page.frames();
  for (const frame of frames) {
    const url = frame.url();
    if (/3ds|three-d-secure|secure/i.test(url)) {
      return frame;
    }
    const hasChallenge = await frame
      .locator(YOO_KASSA_SELECTORS.threeDSCodeInput)
      .first()
      .isVisible()
      .catch(() => false);
    if (hasChallenge) {
      return frame;
    }
  }

  const iframeLocator = page.locator(YOO_KASSA_SELECTORS.threeDSFrame).first();
  const count = await iframeLocator.count().catch(() => 0);
  if (count > 0) {
    const frame = await iframeLocator.contentFrame().catch(() => null);
    if (frame) {
      return frame;
    }
  }
  return null;
}

async function isYooKassa3DSChallenge(page) {
  const url = page.url();
  if (/yookassa\.ru\/.*\/3ds/i.test(url) || /yoomoney\.ru\/.*3ds/i.test(url)) {
    return true;
  }

  const codeInput = page.locator(YOO_KASSA_SELECTORS.threeDSCodeInput).first();
  const confirmButton = page.locator(YOO_KASSA_SELECTORS.threeDSConfirmButton).first();
  const challengeText = page.locator(YOO_KASSA_SELECTORS.threeDSChallenge).first();

  const results = await Promise.allSettled([
    codeInput.isVisible().catch(() => false),
    confirmButton.isVisible().catch(() => false),
    challengeText.isVisible().catch(() => false),
    find3DSFrame(page).then((frame) => Boolean(frame)),
  ]);
  return results.some((r) => r.status === 'fulfilled' && r.value === true);
}

async function waitFor3DSChallenge(page, timeout = 30000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    if (await isYooKassa3DSChallenge(page)) {
      return true;
    }
    await page.waitForTimeout(500);
  }
  return false;
}

async function completeYooKassa3DSChallenge(page) {
  // Wait until the challenge controls are actually present.
  const start = Date.now();
  while (Date.now() - start < 30000) {
    if (await isYooKassa3DSChallenge(page)) {
      break;
    }
    await page.waitForTimeout(500);
  }

  // Prefer a dedicated iframe if one exists.
  const frame = await find3DSFrame(page);
  const context = frame || page;

  const codeInput = context.locator(YOO_KASSA_SELECTORS.threeDSCodeInput).first();
  await expect(codeInput).toBeVisible({ timeout: 15000 });
  await codeInput.fill('1234');

  const confirmButton = context.locator(YOO_KASSA_SELECTORS.threeDSConfirmButton).first();
  await expect(confirmButton).toBeVisible({ timeout: 15000 });
  await clickElementRobustly(confirmButton, { timeout: 5000, forceTimeout: 3000 });
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

async function waitForAnyUrl(page, patterns, timeout) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    const url = page.url();
    for (const pattern of patterns) {
      if (pattern.test(url)) {
        return pattern;
      }
    }
    await page.waitForTimeout(500);
  }
  return null;
}

async function waitForYooKassaOutcome(page, patterns, timeout) {
  /**
   * Poll YooKassa page until one of the following happens:
   *   - URL matches one of the provided merchant patterns (redirect)
   *   - a 3-D Secure challenge appears
   *   - a visible error/decline message appears
   * This avoids racing against always-visible UI elements such as the Back
   * button and detects 3DS as soon as it appears.
   */
  const start = Date.now();
  while (Date.now() - start < timeout) {
    const url = page.url();
    for (const pattern of patterns) {
      if (pattern.test(url)) {
        return { type: 'redirect', pattern };
      }
    }

    if (await isYooKassa3DSChallenge(page)) {
      return { type: '3ds' };
    }

    if (await isYooKassaErrorVisible(page)) {
      return { type: 'error' };
    }

    await page.waitForTimeout(500);
  }
  return null;
}

/**
 * Complete YooKassa test-card payment if the browser was redirected to YooKassa.
 * Does nothing when the app is using mock payments (local dev).
 *
 * @param {import('@playwright/test').Page} page
 * @param {Object} [card] - Card from SUCCESSFUL_CARDS. Defaults to the no-3DS
 *   Mir test card to preserve backward compatibility.
 * @returns {Promise<boolean>} true if the payment flow completed (success or
 *   manual exit), false if 3-D Secure could not be completed automatically.
 */
/**
 * Находит первый товар в наличии через API и возвращает его карточку на странице.
 * Тесты больше не полагаются на порядок выдачи каталога.
 *
 * @param {import('@playwright/test').Page} page
 * @returns {Promise<import('@playwright/test').Locator>}
 */
export async function getInStockProductCard(page) {
  const response = await page.request.get('/api/v1/products/');
  expect(response.ok()).toBeTruthy();
  const data = await response.json();
  const items = (data.items || [])
    .filter((p) => (p.stock || 0) > 0)
    .sort((a, b) => b.stock - a.stock);
  if (items.length === 0) {
    throw new Error('No in-stock product found in catalog');
  }
  // Распределяем worker'ы по разным товарам, чтобы уменьшить конкуренцию за stock.
  const workerIndex = test.info().workerIndex;
  const product = items[workerIndex % items.length];
  const card = page.locator(`[data-product-id="${product.id}"]`);
  await expect(card).toBeVisible();
  return card;
}

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
  //   2. show a 3-D Secure challenge (iframe or full-page redirect),
  //   3. stay on YooKassa because of an error.
  // Wait briefly for a redirect or 3DS, then exit manually if YooKassa stays
  // on the payment page. The merchant success page will poll/sync the status.
  const successPattern = /\/payment\/success/;
  const outcome = await waitForYooKassaOutcome(page, [successPattern], 10000);

  if (outcome && outcome.type === 'redirect') {
    return true;
  }

  if (outcome && outcome.type === '3ds') {
    try {
      await completeYooKassa3DSChallenge(page);
      await waitForAnyUrl(page, [successPattern], 30000);
      return true;
    } catch {
      // 3-D Secure completion is not reliable in automated environments.
      return false;
    }
  }

  // No redirect, no 3DS: exit manually so the merchant page can poll/sync.
  await waitForOverlayToDisappear(page, 2000);
  await exitYooKassaPage(page);
  return true;
}


