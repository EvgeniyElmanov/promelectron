import { test, expect, request } from '@playwright/test';

// E2E для фичи «выбор товаров к оформлению в корзине» (#177):
// - guest: выбор в localStorage → login → merge сохраняет флаги selected
// - auth: снятие выбора пересчитывает итоги, пустой выбор блокирует оформление
//   (API отдаёт 400), заказ создаётся только из выбранных, невыбранные остаются.

function uniqueEmail() {
  return `test_${Date.now()}_w${test.info().workerIndex}@example.com`;
}

// Локальная копия formatPrice из src/utils/price.js для сверки итогов.
function formatPrice(value) {
  return Number(value).toLocaleString('ru-RU', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
}

async function getApiBaseUrl() {
  return process.env.API_URL || 'http://localhost:8000';
}

async function fetchInStockProducts(count = 2) {
  const apiContext = await request.newContext({
    baseURL: await getApiBaseUrl(),
  });
  try {
    const res = await apiContext.get('/api/v1/products/');
    if (!res.ok()) {
      throw new Error(`Failed to fetch products: ${res.status()}`);
    }
    const data = await res.json();
    const items = (data.items || []).filter((p) => (p.stock || 0) > 0);
    if (items.length < count) {
      throw new Error('Not enough in-stock products in catalog');
    }
    return items.slice(0, count);
  } finally {
    await apiContext.dispose();
  }
}

async function registerUser(page, email, password) {
  await page.goto('/register');
  await page.fill('[data-testid="register-name"]', 'Test User');
  await page.fill('[data-testid="register-email"]', email);
  await page.fill('[data-testid="register-password"]', password);
  await page.fill('[data-testid="register-password-confirm"]', password);
  await page.click('[data-testid="register-submit"]');
  await page.waitForURL('/', { timeout: 20000 });
}

async function loginUser(page, email, password) {
  await page.fill('[data-testid="login-email"]', email);
  await page.fill('[data-testid="login-password"]', password);
  await page.click('[data-testid="login-submit"]');
}

async function logoutUser(page) {
  await page.goto('/profile');
  await page.click('[data-testid="logout-button"]');
  await page.waitForURL('/login', { timeout: 10000 });
}

function cartItemByName(page, name) {
  return page
    .locator('[data-testid="cart-item"]')
    .filter({ has: page.locator('.cart-item__name', { hasText: name }) });
}

function itemCheckbox(page, name) {
  return cartItemByName(page, name).locator(
    '[data-testid="cart-item-select"] input[type="checkbox"]',
  );
}

async function mockCdekWidget(page) {
  await page.addInitScript(() => {
    window.__CDEK_MOCK_MODE__ = true;
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
  await page.click('[data-testid="cdek-open-selector"]');
  await page.waitForSelector('[data-testid="cdek-selected-delivery"]', { timeout: 5000 });
}

test.beforeEach(async ({ page, context }) => {
  await context.clearCookies();
  // Перейти на приложение перед доступом к localStorage, чтобы origin был корректным.
  await page.goto('/');
  await page.evaluate(() => localStorage.clear());
});

test.describe('Cart item selection (#177)', () => {
  test('guest selection survives login and cart merge', async ({ page }) => {
    const email = uniqueEmail();
    const password = 'TestPassword123!';
    const [productA, productB] = await fetchInStockProducts(2);

    // Register a user that will be used for login, then logout.
    await registerUser(page, email, password);
    await logoutUser(page);

    // Pre-populate guest cart with two products (both selected by default).
    await page.goto('/');
    await page.evaluate((items) => {
      localStorage.setItem('guest_cart', JSON.stringify(
        items.map((p) => ({
          product_id: p.id,
          quantity: 1,
          name: p.name,
          price: p.price,
          stock: p.stock,
          images: p.images || [],
        })),
      ));
    }, [productA, productB]);

    await page.goto('/cart');
    await expect(page.locator('[data-testid="cart-page"]')).toBeVisible();
    await expect(page.locator('[data-testid="cart-item"]')).toHaveCount(2);

    // Deselect product B — totals should drop to the price of product A only.
    await itemCheckbox(page, productB.name).uncheck();
    await expect(page.locator('.cart__checkout-price')).toHaveText(
      `${formatPrice(productA.price)} ₽`,
    );

    // Checkout as guest redirects to login; merge happens after login.
    await page.locator('[data-testid="checkout-button"]').click();
    await page.waitForURL('/login?redirect=/cart', { timeout: 10000 });
    await loginUser(page, email, password);
    await page.waitForURL('/cart', { timeout: 20000 });

    // After merge: both items present, selection flags preserved.
    await expect(page.locator('[data-testid="cart-item"]')).toHaveCount(2, { timeout: 20000 });
    await expect(itemCheckbox(page, productA.name)).toBeChecked();
    await expect(itemCheckbox(page, productB.name)).not.toBeChecked();
    await expect(page.locator('.cart__checkout-price')).toHaveText(
      `${formatPrice(productA.price)} ₽`,
    );
  });

  test('auth user: totals follow selection, order contains only selected items', async ({ page }) => {
    const email = uniqueEmail();
    const password = 'TestPassword123!';
    const [productA, productB] = await fetchInStockProducts(2);

    await mockCdekWidget(page);
    await registerUser(page, email, password);

    // Add both products to the server-side cart via API (auth token in localStorage).
    await page.evaluate(async (ids) => {
      const token = localStorage.getItem('access_token');
      for (const id of ids) {
        const res = await fetch('/api/v1/cart/add', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ product_id: id, quantity: 1 }),
        });
        if (!res.ok) {
          throw new Error(`cart/add failed for product ${id}: ${res.status}`);
        }
      }
    }, [productA.id, productB.id]);

    await page.goto('/cart');
    await expect(page.locator('[data-testid="cart-item"]')).toHaveCount(2, { timeout: 10000 });
    await expect(page.locator('.cart__checkout-price')).toHaveText(
      `${formatPrice(Number(productA.price) + Number(productB.price))} ₽`,
    );

    // Deselect B → totals recalculated for A only, select-all becomes indeterminate.
    await itemCheckbox(page, productB.name).uncheck();
    await expect(page.locator('.cart__checkout-price')).toHaveText(
      `${formatPrice(productA.price)} ₽`,
    );
    const selectAllInput = page.locator('[data-testid="cart-select-all"] input[type="checkbox"]');
    await expect(selectAllInput).not.toBeChecked();
    expect(await selectAllInput.evaluate((el) => el.indeterminate)).toBe(true);

    // Клик по indeterminate-чекбоксу сначала выбирает все (стандартное поведение браузера),
    // повторный клик снимает выбор со всех.
    await selectAllInput.click();
    await expect(itemCheckbox(page, productB.name)).toBeChecked();

    // Deselect all → checkout button disabled, API rejects order creation with 400.
    await selectAllInput.click();
    await expect(itemCheckbox(page, productA.name)).not.toBeChecked();
    await expect(itemCheckbox(page, productB.name)).not.toBeChecked();
    await expect(page.locator('[data-testid="checkout-button"]')).toBeDisabled();

    const apiStatus = await page.evaluate(async () => {
      const token = localStorage.getItem('access_token');
      const res = await fetch('/api/v1/orders/create/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          cdek_delivery: {
            tariff_code: 136,
            tariff_name: 'Экспресс-экспедиция',
            delivery_mode: 'PVZ',
            delivery_point: 'TEST_PVZ_1',
            price: 350,
          },
          recipient_first_name: 'Иван',
          recipient_last_name: 'Иванов',
          recipient_phone: '+79990001122',
          recipient_country_code: 'RU',
        }),
      });
      return res.status;
    });
    expect(apiStatus).toBe(400);

    // Re-select only product A, choose delivery and recipient, place the order.
    await itemCheckbox(page, productA.name).check();
    await selectCdekDelivery(page);
    await page.fill('[data-testid="recipient-first-name"]', 'Иван');
    await page.fill('[data-testid="recipient-last-name"]', 'Иванов');
    await page.fill('[data-testid="recipient-phone"]', '+79990001122');

    const createOrderResponse = page.waitForResponse(
      (response) => response.url().includes('/orders/create'),
      { timeout: 30000 },
    );
    await page.locator('[data-testid="checkout-button"]').click();
    const response = await createOrderResponse;
    expect(response.status()).toBe(200);

    // Order contains only the selected product.
    const order = await response.json();
    expect(order.items).toHaveLength(1);
    expect(order.items[0].product_id).toBe(productA.id);

    await expect(page).toHaveURL(/\/checkout\/\d+/, { timeout: 30000 });

    // The deselected product stays in the cart, still deselected.
    await page.goto('/cart');
    await expect(page.locator('[data-testid="cart-item"]')).toHaveCount(1, { timeout: 10000 });
    await expect(cartItemByName(page, productB.name)).toBeVisible();
    await expect(itemCheckbox(page, productB.name)).not.toBeChecked();
  });
});
