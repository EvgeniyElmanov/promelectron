import { expect } from '@playwright/test';

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

/**
 * Complete YooKassa test-card payment if the browser was redirected to YooKassa.
 * Does nothing when the app is using mock payments (local dev).
 */
export async function completeYooKassaPaymentIfNeeded(page) {
  // Wait for any navigation after clicking the pay button
  await page.waitForLoadState('networkidle');

  const url = page.url();
  if (!url.includes('yoomoney.ru') && !url.includes('yookassa.ru')) {
    // Mock payment flow — already on /payment/success
    return;
  }

  // Real YooKassa test flow
  await page.waitForTimeout(2000);
  const newCardOption = page.locator('text=New card').first();
  if (await newCardOption.isVisible().catch(() => false)) {
    await newCardOption.click();
  }

  await page.waitForTimeout(1000);

  const cardNumberInput = page.locator('input[name="cardNumber"], input[autocomplete="cc-number"], input[placeholder*="0000"], input[inputmode="numeric"]').first();
  await expect(cardNumberInput).toBeVisible({ timeout: 10000 });
  await cardNumberInput.fill('5555555555554444');

  const monthInput = page.locator('input[placeholder="MM"], input[name="expiryMonth"]').first();
  await expect(monthInput).toBeVisible({ timeout: 5000 });
  await monthInput.fill('12');

  const yearInput = page.locator('input').nth(2);
  await expect(yearInput).toBeVisible({ timeout: 5000 });
  await yearInput.fill('30');

  const cvcInput = page.locator('input[placeholder="CVC"]').first();
  await expect(cvcInput).toBeVisible({ timeout: 5000 });
  await cvcInput.fill('000');

  const submitButton = page.locator('button[type="submit"], button:has-text("Оплатить"), button:has-text("Pay"), input[type="submit"]').first();
  await expect(submitButton).toBeVisible({ timeout: 5000 });
  await submitButton.click();

  const backButton = page.locator(
    'button:has-text("Back to the website"), a:has-text("Back to the website"), a:has-text("Exit the payment process"), button:has-text("Exit the payment process")'
  ).first();
  await expect(backButton).toBeVisible({ timeout: 15000 });
  await backButton.click();
}
