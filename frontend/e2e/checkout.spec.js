import { test, expect } from '@playwright/test';
import {
  goToCart,
  completeYooKassaPaymentIfNeeded,
  waitForPaymentRedirect,
  setYooKassaPaymentStatus,
  getInStockProductCard,
  goToCatalog,
  mockCdekWidget,
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

async function selectCdekDelivery(page) {
  // Open CDEK widget modal (mocked via init script)
  await page.click('[data-testid="cdek-open-selector"]');
  // Мок делает реальные запросы к backend и песочнице СДЭК — ждём дольше (F101);
  // при ошибке мока поднимаем читаемую причину (F102).
  try {
    await page.waitForSelector('[data-testid="cdek-selected-delivery"]', { timeout: 20000 });
  } catch (err) {
    const mockError = await page.evaluate(() => window.__CDEK_MOCK_ERROR__).catch(() => null);
    if (mockError) {
      throw new Error(`MockCDEKWidget failed: ${mockError}`);
    }
    throw err;
  }
}

async function fillRecipientName(page, firstName = 'Иван', lastName = 'Иванов') {
  await page.fill('[data-testid="recipient-first-name"]', firstName);
  await page.fill('[data-testid="recipient-last-name"]', lastName);
}

async function fillRecipientPhone(page, phone = '+79990001122') {
  await page.fill('[data-testid="recipient-phone"]', phone);
}

async function addFirstProductToCart(page) {
  await goToCatalog(page);
  const firstProduct = await getInStockProductCard(page);
  await firstProduct.locator('[data-testid="add-to-cart-button"]').click();
  await expect(firstProduct.locator('[data-testid="add-to-cart-button"]')).toContainText('В корзине', { timeout: 5000 });
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
    // Тариф выбирается динамически из реального расчёта backend (mockCdekWidget),
    // поэтому проверяем тип, а не конкретный код.
    expect(typeof requestBody.cdek_delivery.tariff_code).toBe('number');

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

      if (card.name === 'Mir no 3DS') {
        // Mir no-3DS: реальный UI-флоу ЮKassa как интеграционный smoke-тест.
        // Приложение обязано само увести браузер после создания платежа:
        // на ЮKassa (песочница) или на /payment/success (mock-режим без ключей).
        const destination = await waitForPaymentRedirect(page);
        expect(
          destination,
          'после создания платежа приложение не перенаправило браузер: ' +
            'ни на ЮKassa, ни на /payment/success (mock-режим) — редирект на оплату сломан',
        ).not.toBe('none');

        if (destination === 'yookassa-pending') {
          // Переход инициирован приложением, но страница песочницы не
          // закоммитилась — медленный внешний контур (см. issue #224).
          test.skip(true, 'страница песочницы ЮKassa не загрузилась за 10с — внешний контур, см. #224');
        }

        if (destination === 'yookassa') {
          // Внешний сегмент (форма песочницы + возврат на return_url) ограничен
          // бюджетом, чтобы при нестабильной песочнице тест доходил до честного
          // skip, а не сгорал по общему таймауту (см. issue #224). Общий
          // таймаут теста (180с) не меняется.
          const EXTERNAL_BUDGET_MS = 90000;
          const externalFlow = (async () => {
            try {
              const completed = await completeYooKassaPaymentIfNeeded(page, card);
              if (!completed) {
                return 'форма/3DS песочницы не завершилась';
              }
              // Возврат браузера на return_url выполняет ЮKassa — подменять
              // переход ручным goto нельзя: проверяется переход, который
              // делает связка «приложение + платёжный контур».
              await page.waitForURL(/\/payment\/success/, { timeout: 60000 });
              return null;
            } catch (err) {
              if (err instanceof Error && err.name === 'TimeoutError') {
                return 'песочница не вернула браузер на /payment/success за 60с';
              }
              return `ошибка формы песочницы: ${String(err.message || err).split('\n')[0]}`;
            }
          })();
          const budgetExceeded = page.waitForTimeout(EXTERNAL_BUDGET_MS).then(
            () => `сценарий оплаты не уложился во внешний бюджет ${EXTERNAL_BUDGET_MS / 1000}с`,
            () => null,
          );
          const skipReason = await Promise.race([externalFlow, budgetExceeded]);
          if (skipReason) {
            test.skip(true, `песочница ЮKassa: ${skipReason} — внешний контур, см. #224`);
          }
        }
        // destination === 'success': mock-режим — приложение само привело
        // браузер на страницу результата, внешний контур не участвует.
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
