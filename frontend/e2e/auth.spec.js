import { test, expect, request } from '@playwright/test';
import { goToProfile } from './helpers.js';

function uniqueEmail() {
  return `test_${Date.now()}_w${test.info().workerIndex}@example.com`;
}

async function getApiBaseUrl() {
  return process.env.API_URL || 'http://localhost:8000';
}

async function fetchProduct(productId = 1) {
  const apiContext = await request.newContext({
    baseURL: await getApiBaseUrl(),
  });
  try {
    const res = await apiContext.get(`/api/v1/products/${productId}/`);
    if (!res.ok()) {
      throw new Error(`Failed to fetch product ${productId}: ${res.status()}`);
    }
    return await res.json();
  } finally {
    await apiContext.dispose();
  }
}

test.beforeEach(async ({ page, context }) => {
  await context.clearCookies();
  // Перейти на приложение перед доступом к localStorage, чтобы origin был корректным.
  await page.goto('/');
  await page.evaluate(() => localStorage.clear());
});

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

    await page.waitForURL('/', { timeout: 20000 });

    // Logout
    await goToProfile(page);
    await page.click('[data-testid="logout-button"]');
    await page.waitForURL('/login', { timeout: 10000 });
    await expect(page).toHaveURL('/login');

    // Login
    await page.fill('[data-testid="login-email"]', email);
    await page.fill('[data-testid="login-password"]', password);
    await page.click('[data-testid="login-submit"]');

    await page.waitForURL('/', { timeout: 20000 });
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

    // Use the real product from the database so the assertion matches the UI.
    const product = await fetchProduct(1);

    // Register a user that will be used for login
    await page.goto('/register');
    await page.fill('[data-testid="register-name"]', 'Test User');
    await page.fill('[data-testid="register-email"]', email);
    await page.fill('[data-testid="register-password"]', password);
    await page.fill('[data-testid="register-password-confirm"]', password);
    await page.click('[data-testid="register-submit"]', { noWaitAfter: true });
    await page.waitForURL('/', { timeout: 10000 });

    // Logout
    await goToProfile(page);
    await page.click('[data-testid="logout-button"]');
    await page.waitForURL('/login', { timeout: 10000 });

    // Pre-populate guest cart and open cart page
    await page.goto('/');
    await page.evaluate((cartProduct) => {
      localStorage.setItem('guest_cart', JSON.stringify([
        {
          product_id: cartProduct.id,
          quantity: 2,
          name: cartProduct.name,
          price: cartProduct.price,
          stock: cartProduct.stock,
          images: cartProduct.images || [],
        },
      ]));
    }, product);
    await page.goto('/cart');
    await expect(page.locator('[data-testid="cart-page"]')).toBeVisible();

    // Checkout button redirects guest to login with return URL
    const checkoutBtn = page.locator('[data-testid="checkout-button"]');
    await expect(checkoutBtn).toBeVisible();
    await checkoutBtn.click();
    await page.waitForURL('/login?redirect=/cart', { timeout: 10000 });

    // Login and expect cart merge + redirect back to cart
    await page.fill('[data-testid="login-email"]', email);
    await page.fill('[data-testid="login-password"]', password);
    await page.click('[data-testid="login-submit"]');

    await page.waitForURL('/cart', { timeout: 20000 });
    await expect(page.locator('[data-testid="cart-item"]')).toHaveCount(1, { timeout: 20000 });
    await expect(page.locator('[data-testid="cart-page"]')).toContainText(product.name);
  });
});
