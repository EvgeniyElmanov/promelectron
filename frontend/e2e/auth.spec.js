import { test, expect, request } from '@playwright/test';
import { goToProfile } from './helpers.js';

function uniqueEmail() {
  return `test_${Date.now()}_w${test.info().workerIndex}@example.com`;
}

async function getApiBaseUrl() {
  return process.env.API_URL || 'http://localhost:8000';
}

// Первый товар в наличии из каталога — без хардкода конкретного id:
// в локальных БД product id=1 может отсутствовать (404), а сценарию нужен
// любой реальный товар, чтобы assert совпал с UI.
// minStock = 2: тест кладёт в гостевую корзину quantity: 2, иначе merge
// ответит 400 «Not enough stock» и waitForResponse(200) зависнет (F001).
async function fetchFirstInStockProduct(minStock = 2) {
  const apiContext = await request.newContext({
    baseURL: await getApiBaseUrl(),
  });
  try {
    // limit=100: не зависим от первой страницы пагинации (дефолт 20) (F002).
    const res = await apiContext.get('/api/v1/products/?limit=100');
    if (!res.ok()) {
      throw new Error(`Failed to fetch products: ${res.status()}`);
    }
    const data = await res.json();
    const product = (data.items || []).find((p) => (p.stock || 0) >= minStock);
    if (!product) {
      throw new Error(`No product with stock >= ${minStock} found in catalog`);
    }
    return product;
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

    // Use a real in-stock product from the database so the assertion matches the UI.
    const product = await fetchFirstInStockProduct();

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

    // Login and expect cart merge + redirect back to cart.
    // Merge запускается фоном (Login.vue, без await), а Cart.vue читает корзину
    // один раз при монтировании: ждём ответ merge и перезагружаем страницу,
    // чтобы fetchCart выполнился после коммита merge (гонка, gh-186).
    const mergeResponse = page.waitForResponse(
      (response) => response.url().includes('/cart/merge') && response.status() === 200,
    );
    await page.fill('[data-testid="login-email"]', email);
    await page.fill('[data-testid="login-password"]', password);
    await page.click('[data-testid="login-submit"]');

    await page.waitForURL('/cart', { timeout: 20000 });
    await mergeResponse;
    await page.reload();
    await expect(page.locator('[data-testid="cart-item"]')).toHaveCount(1, { timeout: 20000 });
    await expect(page.locator('[data-testid="cart-page"]')).toContainText(product.name);
  });
});
