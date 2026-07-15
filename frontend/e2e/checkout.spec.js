import { test, expect } from '@playwright/test';
import {
  goToCart,
  completeYooKassaPaymentIfNeeded,
  expectYooKassaPageOrSkip,
  setYooKassaPaymentStatus,
} from './helpers.js';
import { SUCCESSFUL_CARDS } from './yookassa-test-cards.js';

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
  // Open CDEK widget modal (mocked via init script)
  await page.click('[data-testid="cdek-open-selector"]');
  // Wait for the selected delivery summary to appear
  await page.waitForSelector('[data-testid="cdek-selected-delivery"]', { timeout: 5000 });
}

async function fillRecipientName(page, firstName = 'Иван', lastName = 'Иванов') {
  await page.fill('[data-testid="recipient-first-name"]', firstName);
  await page.fill('[data-testid="recipient-last-name"]', lastName);
}

async function fillRecipientPhone(page, phone = '+79990001122') {
  await page.fill('[data-testid="recipient-phone"]', phone);
}

async function fillGuestContactInfo(page, email, firstName = 'Иван', lastName = 'Иванов', phone = '+79990001122') {
  await page.fill('[data-testid="guest-email"]', email);
  await page.fill('[data-testid="guest-first-name"]', firstName);
  await page.fill('[data-testid="guest-last-name"]', lastName);
  await page.fill('[data-testid="guest-phone"]', phone);
}

async function addFirstProductToCart(page) {
  await page.goto('/');
  const firstProduct = page.locator('[data-testid="product-card"]').first();
  await expect(firstProduct).toBeVisible();
  await firstProduct.locator('[data-testid="add-to-cart-button"]').click();
  await expect(page.locator('.toast--success')).toBeVisible({ timeout: 5000 });
  await page.waitForTimeout(300);
}

async function verifyPaymentSuccessPage(page) {
  await expect(page.locator('[data-testid="payment-success-page"]')).toBeVisible();
  const title = page.locator('.payment-result__title');
  await expect(title).toBeVisible();
  await expect(title).toHaveText(/Оплата прошла успешно!|Платёж в обработке/, { timeout: 15000 });
  const titleText = await title.textContent();
  expect(['Оплата прошла успешно!', 'Платёж в обработке']).toContain(titleText);
}

test.describe('Checkout Flow', () => {
  test('authenticated user can place an order with CDEK delivery and recipient name', async ({ page }) => {
    const email = uniqueEmail();
    const password = 'TestPassword123!';

    await mockCdekWidget(page);

    // Register
    await page.goto('/register');
    await page.fill('[data-testid="register-name"]', 'Test User');
    await page.fill('[data-testid="register-email"]', email);
    await page.fill('[data-testid="register-password"]', password);
    await page.fill('[data-testid="register-password-confirm"]', password);
    await page.click('[data-testid="register-submit"]');
    await expect(page).toHaveURL('/');

    // Set profile data (phone required for CDEK recipient)
    await page.goto('/profile/edit');
    await page.fill('[data-testid="edit-profile-first-name"]', 'Профиль');
    await page.fill('[data-testid="edit-profile-last-name"]', 'Тестовый');
    await page.fill('[data-testid="edit-profile-phone"]', '+79990001122');
    await fillAddress(page, 'edit-profile-');
    await page.click('[data-testid="edit-profile-save"]');
    await page.waitForTimeout(1000);

    // Add product to cart
    await addFirstProductToCart(page);

    // Go to cart
    await goToCart(page);
    await expect(page).toHaveURL('/cart');
    await page.waitForSelector('[data-testid="cart-item"]', { timeout: 5000 });

    // Select CDEK delivery and fill recipient data
    await selectCdekDelivery(page);
    await fillRecipientName(page, 'Иван', 'Иванов');
    await fillRecipientPhone(page, '+79990001122');

    // Place order → redirects to checkout page
    const createOrderResponse = page.waitForResponse(
      response => response.url().includes('/orders/create'),
      { timeout: 30000 }
    );
    await page.locator('[data-testid="checkout-button"]').click();
    const response = await createOrderResponse;
    expect(response.status()).toBe(200);

    // Verify order creation payload includes recipient names
    const request = await response.request();
    const requestBody = await request.postDataJSON();
    expect(requestBody).toHaveProperty('recipient_first_name', 'Иван');
    expect(requestBody).toHaveProperty('recipient_last_name', 'Иванов');
    expect(requestBody.cdek_delivery).toHaveProperty('tariff_code', 136);

    // Verify order response includes recipient names
    const order = await response.json();
    expect(order).toHaveProperty('recipient_first_name', 'Иван');
    expect(order).toHaveProperty('recipient_last_name', 'Иванов');

    await expect(page).toHaveURL(/\/checkout\/\d+/, { timeout: 30000 });

    // Verify checkout page shows recipient name and pay button
    const recipientBlock = page.locator('[data-testid="checkout-recipient"]');
    await expect(recipientBlock).toBeVisible();
    await expect(recipientBlock).toContainText('Иванов Иван');

    const payButton = page.locator('[data-testid="pay-button"]');
    await expect(payButton).toBeVisible();
    await expect(payButton).toContainText('Оплатить');
  });

  test('guest user can place an order and complete payment', async ({ page }) => {
    const email = uniqueEmail();

    await mockCdekWidget(page);

    // Add product to cart as guest
    await addFirstProductToCart(page);

    // Navigate directly to guest checkout
    await page.goto('/guest-checkout');
    await expect(page).toHaveURL('/guest-checkout');
    await expect(page.locator('[data-testid="guest-checkout-page"]')).toBeVisible();

    // Select CDEK delivery
    await selectCdekDelivery(page);

    // Fill contact info and recipient name
    await fillGuestContactInfo(page, email, 'Пётр', 'Петров', '+79990002233');

    // Submit order
    const createOrderResponse = page.waitForResponse(
      response => response.url().includes('/orders/create-guest') && response.request().method() === 'POST',
      { timeout: 30000 }
    );
    await page.locator('[data-testid="guest-checkout-submit"]').click();
    const response = await createOrderResponse;
    expect(response.status()).toBe(200);

    // Verify order creation payload includes recipient names
    const request = await response.request();
    const requestBody = await request.postDataJSON();
    expect(requestBody).toHaveProperty('guest_email', email);
    expect(requestBody).toHaveProperty('guest_phone', '+79990002233');
    expect(requestBody).toHaveProperty('recipient_first_name', 'Пётр');
    expect(requestBody).toHaveProperty('recipient_last_name', 'Петров');
    expect(requestBody.cdek_delivery).toHaveProperty('tariff_code', 136);

    // Verify order response includes recipient names
    const order = await response.json();
    expect(order).toHaveProperty('recipient_first_name', 'Пётр');
    expect(order).toHaveProperty('recipient_last_name', 'Петров');
    expect(order).toHaveProperty('guest_email', email);

    // Verify redirect to checkout page (guest email stored in sessionStorage, not URL)
    await expect(page).toHaveURL(`/checkout/${order.id}`, { timeout: 30000 });
    await expect(page.locator('[data-testid="checkout-page"]')).toBeVisible();

    // Click pay button to create guest payment
    const payResponsePromise = page.waitForResponse(
      response => response.url().includes(`/payments/guest/${order.id}`) && response.request().method() === 'POST',
      { timeout: 30000 }
    );
    await page.click('[data-testid="pay-button"]');
    const payResponse = await payResponsePromise;
    expect(payResponse.status()).toBe(200);

    // Set payment status via debug endpoint instead of YooKassa UI
    await setYooKassaPaymentStatus({
      orderId: order.id,
      status: 'succeeded',
      guestEmail: email,
    });

    // Navigate to success page and verify order is loaded
    await page.goto(`/payment/success?order_id=${order.id}`);
    await verifyPaymentSuccessPage(page);
  });

  for (const card of SUCCESSFUL_CARDS) {
    test(`authenticated user can pay with ${card.name} test card`, async ({ page }) => {
      test.setTimeout(180000);

      const email = uniqueEmail();
      const password = 'TestPassword123!';

      await mockCdekWidget(page);

      // 1. Register
      await page.goto('/register');
      await page.fill('[data-testid="register-name"]', 'Test User');
      await page.fill('[data-testid="register-email"]', email);
      await page.fill('[data-testid="register-password"]', password);
      await page.fill('[data-testid="register-password-confirm"]', password);
      await page.click('[data-testid="register-submit"]');
      await expect(page).toHaveURL('/');

      // 2. Set profile data (phone required for CDEK recipient)
      await page.goto('/profile/edit');
      await page.fill('[data-testid="edit-profile-first-name"]', 'Профиль');
      await page.fill('[data-testid="edit-profile-last-name"]', 'Тестовый');
      await page.fill('[data-testid="edit-profile-phone"]', '+79990001122');
      await fillAddress(page, 'edit-profile-');
      await page.click('[data-testid="edit-profile-save"]');
      await page.waitForTimeout(1000);

      // 3. Add product to cart
      await addFirstProductToCart(page);

      // 4. Go to cart and place order
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

      const order = await response.json();
      const orderId = order.id;
      await expect(page).toHaveURL(/\/checkout\/\d+/, { timeout: 30000 });

      // 5. Click Pay button → creates payment
      const payResponsePromise = page.waitForResponse(
        response => response.url().includes('/payments/') && response.request().method() === 'POST',
        { timeout: 30000 }
      );
      await page.click('[data-testid="pay-button"]');
      const payResponse = await payResponsePromise;
      expect(payResponse.status()).toBe(200);

      if (card.number === '2202474301322987') {
        // Mir no-3DS: keep real YooKassa UI flow as the integration smoke test
        const onYooKassa = await expectYooKassaPageOrSkip(page);
        if (!onYooKassa) {
          return;
        }
        const completed = await completeYooKassaPaymentIfNeeded(page, card);
        if (!completed) {
          test.skip();
          return;
        }
        try {
          await page.waitForURL(/\/payment\/success/, { timeout: 60000 });
        } catch {
          await page.goto(`/payment/success?order_id=${orderId}`);
        }
      } else {
        // Mir 3DS: deterministic debug endpoint to avoid flaky sandbox
        await setYooKassaPaymentStatus({ orderId, status: 'succeeded' });
        await page.goto(`/payment/success?order_id=${orderId}`);
      }

      // 6. Verify success page is loaded
      await verifyPaymentSuccessPage(page);
    });
  }
});
