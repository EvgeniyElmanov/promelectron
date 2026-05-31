import { test, expect } from '@playwright/test';

async function fillAddress(page, prefix) {
  await page.fill(`[data-testid="${prefix}region"]`, 'Московская область');
  await page.fill(`[data-testid="${prefix}district"]`, 'Тестовый район');
  await page.fill(`[data-testid="${prefix}city"]`, 'Москва');
  await page.fill(`[data-testid="${prefix}street"]`, 'Тестовая');
  await page.fill(`[data-testid="${prefix}house"]`, '1');
  await page.fill(`[data-testid="${prefix}apartment"]`, '42');
}

test.describe('Guest Checkout Flow', () => {
  test('guest can place an order without registration', async ({ page }) => {
    // Add product to cart as guest
    await page.goto('/');
    const firstProduct = page.locator('[data-testid="product-card"]').first();
    await expect(firstProduct).toBeVisible();
    await firstProduct.locator('[data-testid="add-to-cart-button"]').click();
    await expect(page.locator('.toast--success')).toBeVisible({ timeout: 5000 });
    await page.waitForTimeout(300);

    // Go to cart
    await page.click('[data-testid="cart-link"]');
    await expect(page).toHaveURL('/cart');
    await page.waitForSelector('[data-testid="cart-item"]', { timeout: 5000 });

    // Click checkout → redirect to guest checkout
    await page.locator('[data-testid="checkout-button"]').click();
    await expect(page).toHaveURL('/guest-checkout');
    await expect(page.locator('[data-testid="guest-checkout-page"]')).toBeVisible();

    // Fill contact info
    await page.fill('[data-testid="guest-email"]', 'guest_test@example.com');
    await page.fill('[data-testid="guest-name"]', 'Гость Тестовый');
    await page.fill('[data-testid="guest-phone"]', '+79990001122');

    // Fill address
    await fillAddress(page, 'guest-');

    // Submit order
    const createOrderResponse = page.waitForResponse(
      response => response.url().includes('/orders/create-guest'),
      { timeout: 30000 }
    );
    await page.locator('[data-testid="guest-checkout-submit"]').click();
    const response = await createOrderResponse;
    expect(response.status()).toBe(200);

    // Redirect to success page
    await expect(page).toHaveURL(/\/guest-order-success\/\d+/, { timeout: 15000 });
    await expect(page.locator('[data-testid="guest-order-success-page"]')).toBeVisible();

    // Verify order details shown
    const orderId = await page.locator('[data-testid="success-order-id"]').textContent();
    expect(orderId).toMatch(/№\d+/);
    await expect(page.locator('[data-testid="success-email"]')).toContainText('guest_test@example.com');
  });

  test('guest checkout shows empty state for empty cart', async ({ page }) => {
    await page.goto('/guest-checkout');
    await expect(page.locator('[data-testid="guest-checkout-page"]')).toBeVisible();
    // Empty cart should show link to catalog
    await expect(page.locator('.guest-checkout__empty')).toContainText('В каталог');
  });
});
