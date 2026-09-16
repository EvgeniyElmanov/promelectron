import { test, expect } from '@playwright/test';
import { goToCart, getInStockProductCard, goToCatalog } from './helpers.js';

function uniqueEmail() {
  return `test_${Date.now()}_w${test.info().workerIndex}@example.com`;
}

async function addFirstProductToCart(page) {
  await goToCatalog(page);
  const firstProduct = await getInStockProductCard(page);
  await firstProduct.locator('[data-testid="add-to-cart-button"]').click();
  await expect(firstProduct.locator('[data-testid="add-to-cart-button"]')).toContainText('В корзине', { timeout: 5000 });
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

async function mockSupplierCityCode(page, cityCode = 44) {
  await page.route('/api/v1/cdek/supplier-city-code/**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ city_code: cityCode }),
    });
  });
}

async function mockCdekWidget(page) {
  await page.addInitScript(() => {
    window.__CDEK_MOCK_MODE__ = true;
    window.CDEKWidget = class MockCDEKWidget {
      constructor(options) {
        this.options = options;
        window.__lastCdekWidgetOptions = options;
        setTimeout(() => {
          options.onChoose('PVZ', {
            tariff_code: 136,
            tariff_name: 'Экспресс-экспедиция',
            delivery_sum: 350,
            period_min: 1,
            period_max: 3,
          }, {
            code: 'TEST_PVZ_1',
            city_code: 44,
            city: 'Москва',
            address: 'ул. Тестовая, 1',
          });
        }, 50);
      }

      destroy() {}

      open() {}
    };
  });
}

test.describe('CDEK Widget on Cart Page', () => {
  test('authenticated user can open CDEK widget from cart without page crash', async ({ page }) => {
    await registerAndGoToCart(page);

    const widget = page.locator('[data-testid="cdek-delivery-widget"]');
    await expect(widget).toBeVisible();

    const openButton = page.locator('[data-testid="cdek-open-selector"]');
    await expect(openButton).toBeVisible();
    await expect(openButton).toContainText('Выбрать доставку СДЭК');

    await openButton.click();

    await expect(openButton).not.toContainText('Загрузка', { timeout: 10000 });

    const error = page.locator('[data-testid="cdek-widget-error"]');
    const hasError = await error.isVisible().catch(() => false);

    if (hasError) {
      await expect(error).toContainText('Не удалось загрузить виджет СДЭК');
    } else {
      await expect(page.locator('[data-testid="cdek-widget-container"]')).toBeAttached();
    }
  });

  test('CDEK widget container is present in the document for widget initialization', async ({ page }) => {
    await registerAndGoToCart(page);

    const container = page.locator('[data-testid="cdek-widget-container"]');
    await expect(container).toBeAttached();
  });

  test('selecting a PVZ displays tariff price and delivery period', async ({ page }) => {
    await mockCdekWidget(page);
    await mockSupplierCityCode(page, 44);
    await registerAndGoToCart(page);

    const widget = page.locator('[data-testid="cdek-delivery-widget"]');
    await expect(widget).toBeVisible();

    await page.locator('[data-testid="cdek-open-selector"]').click();
    const selected = page.locator('[data-testid="cdek-selected-delivery"]');
    await expect(selected).toBeVisible({ timeout: 5000 });

    await expect(selected).toContainText('Пункт выдачи');
    await expect(selected).toContainText('Экспресс-экспедиция');
    await expect(selected).toContainText('350 ₽');
    await expect(selected).toContainText('Срок: 1-3 дн.');
  });

  test('uses supplier city code as sender location', async ({ page }) => {
    await mockCdekWidget(page);
    await mockSupplierCityCode(page, 280);
    await registerAndGoToCart(page);

    await page.locator('[data-testid="cdek-open-selector"]').click();
    await page.waitForTimeout(200);

    const options = await page.evaluate(() => window.__lastCdekWidgetOptions);
    expect(options).toBeDefined();
    expect(options.from).toEqual({ code: 280 });
  });

  test('shows fallback hint when supplier city code is not resolved', async ({ page }) => {
    await mockCdekWidget(page);
    await mockSupplierCityCode(page, null);
    await registerAndGoToCart(page);

    const hint = page.locator('[data-testid="cdek-widget-fallback-hint"]');
    await expect(hint).toBeVisible();
    await expect(hint).toContainText('Город отправления поставщика не настроён');

    await page.locator('[data-testid="cdek-open-selector"]').click();
    const selected = page.locator('[data-testid="cdek-selected-delivery"]');
    await expect(selected).toBeVisible({ timeout: 5000 });
  });
});


