import { test, expect } from '@playwright/test';
import { goToCart } from './helpers.js';

function uniqueEmail() {
  return `test_${Date.now()}_w${test.info().workerIndex}@example.com`;
}

async function addFirstProductToCart(page) {
  await page.goto('/');
  const firstProduct = page.locator('[data-testid="product-card"]').first();
  await expect(firstProduct).toBeVisible();
  await firstProduct.locator('[data-testid="add-to-cart-button"]').click();
  await expect(page.locator('.toast--success')).toBeVisible({ timeout: 5000 });
  await page.waitForTimeout(300);
}

test.describe('CDEK Widget on Cart Page', () => {
  test('authenticated user sees CDEK widget and graceful error when Yandex Maps key is missing', async ({ page }) => {
    const email = uniqueEmail();
    const password = 'TestPassword123!';

    // Register an authenticated user
    await page.goto('/register');
    await page.fill('[data-testid="register-name"]', 'Test User');
    await page.fill('[data-testid="register-email"]', email);
    await page.fill('[data-testid="register-password"]', password);
    await page.fill('[data-testid="register-password-confirm"]', password);
    await page.click('[data-testid="register-submit"]');
    await expect(page).toHaveURL('/');

    // Add product to cart
    await addFirstProductToCart(page);

    // Navigate to cart
    await goToCart(page);
    await expect(page).toHaveURL('/cart');
    await expect(page.locator('[data-testid="cart-item"]')).toBeVisible({ timeout: 5000 });

    // Verify CDEK widget section is rendered on the cart page
    const widget = page.locator('[data-testid="cdek-delivery-widget"]');
    await expect(widget).toBeVisible();

    // Verify the selector button is present and clickable
    const openButton = page.locator('[data-testid="cdek-open-selector"]');
    await expect(openButton).toBeVisible();
    await expect(openButton).toContainText('Выбрать доставку СДЭК');

    // Clicking the button without a configured VITE_YANDEX_MAPS_API_KEY should
    // trigger a graceful load error instead of crashing the page.
    await openButton.click();

    // Wait for the loading spinner to finish (button returns from "Загрузка...")
    await expect(openButton).not.toContainText('Загрузка', { timeout: 10000 });

    const error = page.locator('[data-testid="cdek-widget-error"]');
    await expect(error).toBeVisible({ timeout: 10000 });
    await expect(error).toContainText('Не удалось загрузить виджет СДЭК');
  });

  test('CDEK widget container is present in the document for widget initialization', async ({ page }) => {
    const email = uniqueEmail();
    const password = 'TestPassword123!';

    // Register and add product so the authenticated cart renders the widget
    await page.goto('/register');
    await page.fill('[data-testid="register-name"]', 'Test User');
    await page.fill('[data-testid="register-email"]', email);
    await page.fill('[data-testid="register-password"]', password);
    await page.fill('[data-testid="register-password-confirm"]', password);
    await page.click('[data-testid="register-submit"]');
    await expect(page).toHaveURL('/');

    await addFirstProductToCart(page);
    await goToCart(page);
    await expect(page).toHaveURL('/cart');

    // The hidden container must exist for the official widget to mount
    const container = page.locator('[data-testid="cdek-widget-container"]');
    await expect(container).toBeAttached();
  });
});
