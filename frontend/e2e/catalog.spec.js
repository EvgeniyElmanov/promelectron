import { test, expect } from '@playwright/test';
import { goToCart, getInStockProductCard } from './helpers.js';

function uniqueEmail() {
  return `test_${Date.now()}_w${test.info().workerIndex}@example.com`;
}

test.describe('Catalog & Cart', () => {
  test('homepage shows products and categories', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('[data-testid="search-bar"]')).toBeVisible();
    await expect(page.locator('[data-testid="category-chips"]')).toBeVisible();
    await expect(page.locator('[data-testid="product-card"]').first()).toBeVisible();
  });

  test('product can be added to cart', async ({ page }) => {
    const email = uniqueEmail();
    const password = 'TestPassword123!';

    // Register first
    await page.goto('/register');
    await page.fill('[data-testid="register-name"]', 'Test User');
    await page.fill('[data-testid="register-email"]', email);
    await page.fill('[data-testid="register-password"]', password);
    await page.fill('[data-testid="register-password-confirm"]', password);
    await page.click('[data-testid="register-submit"]');
    await expect(page).toHaveURL('/');

    // Add product to cart
    const firstProduct = await getInStockProductCard(page);
    await firstProduct.locator('[data-testid="add-to-cart-button"]').click();
    // Wait for success toast (not error)
    await expect(page.locator('.toast--success')).toBeVisible({ timeout: 5000 });
    await page.waitForTimeout(300);

    // Go to cart
    await goToCart(page);
    await expect(page).toHaveURL('/cart');
    await page.waitForSelector('[data-testid="cart-item"]', { timeout: 5000 });
  });
});
