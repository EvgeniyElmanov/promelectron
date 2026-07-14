import { test, expect } from '@playwright/test';
import {
  goToCart,
  completeYooKassaFailedPaymentIfNeeded,
  expectYooKassaPageOrSkip,
} from './helpers.js';
import { FAILED_CARDS } from './yookassa-test-cards.js';

function uniqueEmail() {
  return `test_${Date.now()}_w${test.info().workerIndex}@example.com`;
}

async function fillAddress(page, prefix) {
  await page.fill(`[data-testid="${prefix}region"]`, 'Московская область');
  await page.fill(`[data-testid="${prefix}district"]`, 'Тестовый район');
  await page.fill(`[data-testid="${prefix}city"]`, 'Москва');
  await page.fill(`[data-testid="${prefix}street"]`, 'Тестовая');
  await page.fill(`[data-testid="${prefix}house"]`, '1');
  await page.fill(`[data-testid="${prefix}apartment"]`, '42');
}

async function mockCdekWidget(page) {
  await page.addInitScript(() => {
    window.CDEKWidget = class MockCDEKWidget {
      constructor(options) {
        this.options = options;
        setTimeout(() => {
          options.onChoose('PVZ', {
            tariff_code: 136,
            tariff_name: 'Экспресс-экспедиция',
            delivery_sum: 350,
            period_min: 1,
            period_max: 3,
          }, {
            code: 'TEST_PVZ_1',
            location: { city_code: 44, city: 'Москва', address: 'ул. Тестовая, 1' },
          });
        }, 50);
      }
      destroy() {}
    };
  });
}

async function selectCdekDelivery(page) {
  await page.click('[data-testid="cdek-open-selector"]');
  await page.waitForSelector('[data-testid="cdek-selected-delivery"]', { timeout: 5000 });
}

async function fillRecipientName(page, firstName = 'Иван', lastName = 'Иванов') {
  await page.fill('[data-testid="recipient-first-name"]', firstName);
  await page.fill('[data-testid="recipient-last-name"]', lastName);
}

async function fillRecipientPhone(page, phone = '+79990001122') {
  await page.fill('[data-testid="recipient-phone"]', phone);
}

async function addFirstProductToCart(page) {
  await page.goto('/');
  const firstProduct = page.locator('[data-testid="product-card"]').first();
  await expect(firstProduct).toBeVisible();
  await firstProduct.locator('[data-testid="add-to-cart-button"]').click();
  await expect(page.locator('.toast--success')).toBeVisible({ timeout: 5000 });
  await page.waitForTimeout(300);
}

async function registerUser(page, email, password) {
  await page.goto('/register');
  await page.fill('[data-testid="register-name"]', 'Test User');
  await page.fill('[data-testid="register-email"]', email);
  await page.fill('[data-testid="register-password"]', password);
  await page.fill('[data-testid="register-password-confirm"]', password);
  await page.click('[data-testid="register-submit"]');
  await expect(page).toHaveURL('/');
}

async function fillProfileForCdek(page) {
  await page.goto('/profile/edit');
  await page.fill('[data-testid="edit-profile-first-name"]', 'Профиль');
  await page.fill('[data-testid="edit-profile-last-name"]', 'Тестовый');
  await page.fill('[data-testid="edit-profile-phone"]', '+79990001122');
  await fillAddress(page, 'edit-profile-');
  await page.click('[data-testid="edit-profile-save"]');
  await page.waitForTimeout(1000);
}

async function placeOrder(page) {
  await addFirstProductToCart(page);
  await goToCart(page);
  await expect(page).toHaveURL('/cart');
  await page.waitForSelector('[data-testid="cart-item"]', { timeout: 5000 });

  await selectCdekDelivery(page);
  await fillRecipientName(page, 'Иван', 'Иванов');
  await fillRecipientPhone(page, '+79990001122');

  const createOrderResponse = page.waitForResponse(
    response => response.url().includes('/orders/create'),
    { timeout: 30000 }
  );
  await page.locator('[data-testid="checkout-button"]').click();
  const response = await createOrderResponse;
  expect(response.status()).toBe(200);
  await expect(page).toHaveURL(/\/checkout\/\d+/, { timeout: 30000 });
}

test.describe('Checkout failed card scenarios', () => {
  for (const card of FAILED_CARDS) {
    test(`shows payment failed page with reason: ${card.reason}`, async ({ page }) => {
      test.setTimeout(180000);

      const email = uniqueEmail();
      const password = 'TestPassword123!';

      await mockCdekWidget(page);
      await registerUser(page, email, password);
      await fillProfileForCdek(page);
      await placeOrder(page);

      // Click Pay button → creates payment and redirects to YooKassa
      const payResponsePromise = page.waitForResponse(
        response => response.url().includes('/payments/') && response.request().method() === 'POST',
        { timeout: 30000 }
      );
      await page.click('[data-testid="pay-button"]');
      await payResponsePromise;

      // In CI/CD test environments YooKassa credentials may be missing — handle gracefully
      const onYooKassa = await expectYooKassaPageOrSkip(page);
      if (!onYooKassa) {
        return;
      }

      // Fill the declined card and submit the form
      await completeYooKassaFailedPaymentIfNeeded(page, card);

      // Wait for redirect back to our failed page (PaymentSuccess may poll for a while)
      await page.waitForURL(/\/payment\/failed/, { timeout: 120000 });
      await expect(page.locator('[data-testid="payment-failed-page"]')).toBeVisible();

      // Verify the human-readable cancellation reason is shown
      const reasonLocator = page.locator('[data-testid="cancellation-reason"]');
      await expect(reasonLocator).toBeVisible();
      const reasonText = await reasonLocator.textContent();
      expect(reasonText).toContain(card.label);
    });
  }
});
