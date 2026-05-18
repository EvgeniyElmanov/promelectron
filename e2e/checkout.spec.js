import { test, expect } from '@playwright/test';

function uniqueEmail() {
  return `test_${Date.now()}@example.com`;
}

async function fillAddress(page, prefix) {
  await page.fill(`[data-testid="${prefix}region"]`, 'Московская область');
  await page.fill(`[data-testid="${prefix}district"]`, 'Тестовый район');
  await page.fill(`[data-testid="${prefix}city"]`, 'Москва');
  await page.fill(`[data-testid="${prefix}street"]`, 'Тестовая');
  await page.fill(`[data-testid="${prefix}house"]`, '1');
  await page.fill(`[data-testid="${prefix}apartment"]`, '42');
}

test.describe('Checkout Flow', () => {
  test('user can place an order', async ({ page }) => {
    const email = uniqueEmail();
    const password = 'TestPassword123!';

    // Register
    await page.goto('/register');
    await page.fill('[data-testid="register-name"]', 'Test User');
    await page.fill('[data-testid="register-email"]', email);
    await page.fill('[data-testid="register-password"]', password);
    await page.fill('[data-testid="register-password-confirm"]', password);
    await page.click('[data-testid="register-submit"]');
    await expect(page).toHaveURL('/');

    // Set shipping address in profile
    await page.goto('/profile/edit');
    await fillAddress(page, 'edit-profile-');
    await page.click('[data-testid="edit-profile-save"]');
    await page.waitForTimeout(1000);

    // Add product to cart
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

    // Verify shipping address auto-filled from profile
    await expect(page.locator('[data-testid="cart-city"]')).toHaveValue('Москва');
    await expect(page.locator('[data-testid="cart-street"]')).toHaveValue('Тестовая');

    // Place order → redirects to checkout page
    await page.click('[data-testid="checkout-button"]');
    await page.waitForURL(/\/checkout\/\d+/, { timeout: 10000 });

    // Complete mock payment
    await page.fill('[data-testid="card-holder"]', 'Test User');
    await page.fill('[data-testid="card-number"]', '4242 4242 4242 4242');
    await page.fill('[data-testid="card-expiry"]', '12/30');
    await page.fill('[data-testid="card-cvv"]', '123');
    await page.click('[data-testid="pay-button"]');

    // After successful payment → redirect to order detail
    await page.waitForURL(/\/orders\/\d+/, { timeout: 15000 });

    // Verify order detail page is shown with shipping address
    await expect(page.locator('[data-testid="order-detail-page"]')).toBeVisible();
    await expect(page.locator('.order-detail')).toContainText('Москва');
  });
});
