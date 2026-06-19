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

async function registerAndGoToCart(page) {
  const email = uniqueEmail();
  const password = 'TestPassword123!';

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
  await expect(page.locator('[data-testid="cart-item"]')).toBeVisible({ timeout: 5000 });
}

test.describe('CDEK Widget on Cart Page', () => {
  test('authenticated user can open CDEK widget from cart without page crash', async ({ page }) => {
    await registerAndGoToCart(page);

    // Verify CDEK widget section is rendered on the cart page
    const widget = page.locator('[data-testid="cdek-delivery-widget"]');
    await expect(widget).toBeVisible();

    // Verify the selector button is present and clickable
    const openButton = page.locator('[data-testid="cdek-open-selector"]');
    await expect(openButton).toBeVisible();
    await expect(openButton).toContainText('Выбрать доставку СДЭК');

    // Clicking the button should either open the widget (if Yandex Maps key is configured)
    // or show a graceful load error (if it is missing). The page must not crash either way.
    await openButton.click();

    // Wait for the loading spinner to finish (button returns from "Загрузка...")
    await expect(openButton).not.toContainText('Загрузка', { timeout: 10000 });

    const error = page.locator('[data-testid="cdek-widget-error"]');
    const hasError = await error.isVisible().catch(() => false);

    if (hasError) {
      await expect(error).toContainText('Не удалось загрузить виджет СДЭК');
    } else {
      // Widget opened successfully; the hidden mount point must exist and the page must stay healthy.
      await expect(page.locator('[data-testid="cdek-widget-container"]')).toBeAttached();
    }
  });

  test('CDEK widget container is present in the document for widget initialization', async ({ page }) => {
    await registerAndGoToCart(page);

    // The hidden container must exist for the official widget to mount
    const container = page.locator('[data-testid="cdek-widget-container"]');
    await expect(container).toBeAttached();
  });
});
