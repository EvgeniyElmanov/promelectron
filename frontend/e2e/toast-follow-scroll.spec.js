import { test, expect } from '@playwright/test';
import { getInStockProductCard } from './helpers.js';

function uniqueEmail() {
  return `test_${Date.now()}_w${test.info().workerIndex}@example.com`;
}

// Регрессия issue #194: toast-уведомления не следовали за скроллом, т.к.
// `overflow-x: hidden` на html/body ломал `position: sticky` хедера,
// к которому якорится .header__toast.
async function expectHeaderStickyAfterScroll(page) {
  await page.goto('/');
  await expect(page.locator('[data-testid="product-card"]').first()).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 1500));
  const headerTop = await page.locator('header.header').evaluate((el) => el.getBoundingClientRect().top);
  expect(headerTop).toBe(0);
}

async function expectToastVisibleInViewportAfterScroll(page) {
  // Register (add-to-cart требует авторизации, как в catalog.spec.js)
  await page.goto('/register');
  await page.fill('[data-testid="register-name"]', 'Test User');
  await page.fill('[data-testid="register-email"]', uniqueEmail());
  await page.fill('[data-testid="register-password"]', 'TestPassword123!');
  await page.fill('[data-testid="register-password-confirm"]', 'TestPassword123!');
  await page.click('[data-testid="register-submit"]');
  await expect(page).toHaveURL('/');

  // Скроллим вниз и добавляем товар из глубины страницы
  await page.evaluate(() => window.scrollTo(0, 1500));
  const product = await getInStockProductCard(page);
  await product.locator('[data-testid="add-to-cart-button"]').click();

  const toast = page.locator('.toast--success');
  await expect(toast).toBeVisible({ timeout: 5000 });
  const box = await toast.boundingBox();
  const viewport = page.viewportSize();
  expect(box).not.toBeNull();
  expect(box.y).toBeGreaterThanOrEqual(0);
  expect(box.y + box.height).toBeLessThanOrEqual(viewport.height);
}

test.describe('Toast follow scroll (mobile viewport)', () => {
  test('header stays sticky after scrolling down', async ({ page }) => {
    await expectHeaderStickyAfterScroll(page);
  });

  test('success toast is visible in viewport after scrolling down', async ({ page }) => {
    await expectToastVisibleInViewportAfterScroll(page);
  });
});

test.describe('Toast follow scroll (desktop viewport)', () => {
  test.use({ viewport: { width: 1280, height: 900 } });

  test('header stays sticky after scrolling down', async ({ page }) => {
    await expectHeaderStickyAfterScroll(page);
  });

  test('success toast is visible in viewport after scrolling down', async ({ page }) => {
    await expectToastVisibleInViewportAfterScroll(page);
  });
});
