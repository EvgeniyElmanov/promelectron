import { test, expect } from '@playwright/test';

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
    await page.click('[data-testid="profile-link"]');
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

  test('guest user can view cart and login on checkout', async ({ page }) => {
    // Navigate first to set origin, then pre-populate guest cart
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('guest_cart', JSON.stringify([
        { product_id: 1, quantity: 2, name: 'Test Product', price: 1000, stock: 5, images: [] }
      ]));
    });
    await page.goto('/cart');
    // Guest sees cart page, not redirected to login
    await expect(page.locator('[data-testid="cart-page"]')).toBeVisible();
    await expect(page.locator('[data-testid="cart-title"]')).toContainText('Корзина');

    // Checkout button redirects to login for guest
    const checkoutBtn = page.locator('[data-testid="checkout-button"]');
    await expect(checkoutBtn).toBeVisible();
    await checkoutBtn.click();
    await expect(page).toHaveURL('/login');
  });
});
