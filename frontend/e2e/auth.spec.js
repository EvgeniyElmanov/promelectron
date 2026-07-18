import { test, expect } from '@playwright/test';
import { goToProfile } from './helpers.js';

function uniqueEmail() {
  return `test_${Date.now()}_w${test.info().workerIndex}@example.com`;
}

test.describe('Authentication', () => {
  test('user can register and login', async ({ page }) => {
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

    // Logout
    await goToProfile(page);
    await page.click('[data-testid="logout-button"]');
    await expect(page).toHaveURL('/login');

    // Login
    await page.fill('[data-testid="login-email"]', email);
    await page.fill('[data-testid="login-password"]', password);
    await page.click('[data-testid="login-submit"]');

    await expect(page).toHaveURL('/');
  });

  test('login with wrong password shows error', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[data-testid="login-email"]', 'nonexistent@example.com');
    await page.fill('[data-testid="login-password"]', 'wrongpassword');
    await page.click('[data-testid="login-submit"]');

    await expect(page.locator('[data-testid="login-error"]')).toBeVisible();
  });

  test('guest cart is merged after login from checkout redirect', async ({ page }) => {
    const email = uniqueEmail();
    const password = 'TestPassword123!';

    // Register a user that will be used for login
    await page.goto('/register');
    await page.fill('[data-testid="register-name"]', 'Test User');
    await page.fill('[data-testid="register-email"]', email);
    await page.fill('[data-testid="register-password"]', password);
    await page.fill('[data-testid="register-password-confirm"]', password);
    await page.click('[data-testid="register-submit"]');
    await expect(page).toHaveURL('/');

    // Logout
    await goToProfile(page);
    await page.click('[data-testid="logout-button"]');
    await expect(page).toHaveURL('/login');

    // Pre-populate guest cart and open cart page
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('guest_cart', JSON.stringify([
        { product_id: 1, quantity: 2, name: 'Test Product', price: 1000, stock: 5, images: [] }
      ]));
    });
    await page.goto('/cart');
    await expect(page.locator('[data-testid="cart-page"]')).toBeVisible();

    // Checkout button redirects guest to login with return URL
    const checkoutBtn = page.locator('[data-testid="checkout-button"]');
    await expect(checkoutBtn).toBeVisible();
    await checkoutBtn.click();
    await expect(page).toHaveURL('/login?redirect=/cart');

    // Login and expect cart merge + redirect back to cart
    await page.fill('[data-testid="login-email"]', email);
    await page.fill('[data-testid="login-password"]', password);
    await page.click('[data-testid="login-submit"]');

    await expect(page).toHaveURL('/cart');
    await expect(page.locator('[data-testid="cart-item"]')).toHaveCount(1);
    await expect(page.locator('[data-testid="cart-page"]')).toContainText('Test Product');
  });
});
