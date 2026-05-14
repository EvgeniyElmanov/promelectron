import { test, expect } from '@playwright/test';

function uniqueEmail() {
  return `test_${Date.now()}@example.com`;
}

test.describe('Product Detail Page', () => {
  test('can navigate to product detail from catalog', async ({ page }) => {
    await page.goto('/');
    const firstCard = page.locator('[data-testid="product-card"]').first();
    await expect(firstCard).toBeVisible();
    await firstCard.click();
    await expect(page.locator('[data-testid="pdp-title"]')).toBeVisible();
    await expect(page.locator('[data-testid="pdp-price"]')).toBeVisible();
    await expect(page.locator('[data-testid="pdp-add-to-cart"]')).toBeVisible();
  });

  test('can add product to cart from PDP', async ({ page }) => {
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

    // Go to PDP
    const firstCard = page.locator('[data-testid="product-card"]').first();
    await firstCard.click();
    await expect(page.locator('[data-testid="pdp-title"]')).toBeVisible();

    // Add to cart
    await page.click('[data-testid="pdp-add-to-cart"]');

    // Verify cart
    await page.click('[data-testid="cart-link"]');
    await expect(page).toHaveURL('/cart');
    await page.waitForSelector('[data-testid="cart-item"]', { timeout: 5000 });
  });

  test('shows reviews section on PDP', async ({ page }) => {
    await page.goto('/');
    const firstCard = page.locator('[data-testid="product-card"]').first();
    await firstCard.click();
    await expect(page.locator('[data-testid="pdp-reviews-section"]')).toBeVisible();
  });
});
