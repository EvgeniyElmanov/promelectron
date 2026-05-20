/**
 * Visual Smoke Test — автоматизированная "ручная проверка через браузер".
 * После каждого шага делается скриншот в test-results/visual-smoke/.
 * Не проверяет функциональность (для этого есть обычные e2e), а делает скриншоты
 * всех ключевых страниц для визуальной проверки.
 */
import { test } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const screenshotDir = path.join(process.cwd(), 'test-results', 'visual-smoke');

function screenshot(page, name) {
  if (!fs.existsSync(screenshotDir)) {
    fs.mkdirSync(screenshotDir, { recursive: true });
  }
  return page.screenshot({
    path: path.join(screenshotDir, `${name}.png`),
    fullPage: true,
  });
}

test.describe('Visual Smoke — Key Pages', () => {
  test('01-homepage', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(1000);
    await screenshot(page, '01-homepage');
  });

  test('02-product-detail', async ({ page }) => {
    await page.goto('/product/1');
    await page.waitForTimeout(1000);
    await screenshot(page, '02-product-detail');
  });

  test('03-login', async ({ page }) => {
    await page.goto('/login');
    await page.waitForTimeout(600);
    await screenshot(page, '03-login');
  });

  test('04-register', async ({ page }) => {
    await page.goto('/register');
    await page.waitForTimeout(600);
    await screenshot(page, '04-register');
  });

  test('05-cart-unauthorized', async ({ page }) => {
    await page.goto('/cart');
    await page.waitForTimeout(600);
    await screenshot(page, '05-cart-unauthorized');
  });

  test('06-profile', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[data-testid="login-email"]', 'seed-admin@example.com');
    await page.fill('[data-testid="login-password"]', 'seedpassword123');
    await page.click('[data-testid="login-submit"]');
    await page.waitForTimeout(2000);

    await page.goto('/profile');
    await page.waitForTimeout(1000);
    await screenshot(page, '06-profile');
  });

  test('07-profile-edit', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[data-testid="login-email"]', 'seed-admin@example.com');
    await page.fill('[data-testid="login-password"]', 'seedpassword123');
    await page.click('[data-testid="login-submit"]');
    await page.waitForTimeout(2000);

    await page.goto('/profile/edit');
    await page.waitForTimeout(1000);
    await screenshot(page, '07-profile-edit');
  });

  test('08-admin-panel', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[data-testid="login-email"]', 'seed-admin@example.com');
    await page.fill('[data-testid="login-password"]', 'seedpassword123');
    await page.click('[data-testid="login-submit"]');
    await page.waitForTimeout(2000);

    await page.goto('/admin');
    await page.waitForTimeout(1000);
    await screenshot(page, '08-admin-panel');
  });

  test('09-supplier-my-products', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[data-testid="login-email"]', 'seed-supplier@example.com');
    await page.fill('[data-testid="login-password"]', 'seedpassword123');
    await page.click('[data-testid="login-submit"]');
    await page.waitForTimeout(2000);

    await page.goto('/my-products');
    await page.waitForTimeout(1000);
    await screenshot(page, '09-supplier-my-products');
  });

  test('10-orders', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[data-testid="login-email"]', 'seed-admin@example.com');
    await page.fill('[data-testid="login-password"]', 'seedpassword123');
    await page.click('[data-testid="login-submit"]');
    await page.waitForTimeout(2000);

    await page.goto('/orders');
    await page.waitForTimeout(1000);
    await screenshot(page, '10-orders');
  });

  test('11-favorites', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[data-testid="login-email"]', 'seed-admin@example.com');
    await page.fill('[data-testid="login-password"]', 'seedpassword123');
    await page.click('[data-testid="login-submit"]');
    await page.waitForTimeout(2000);

    await page.goto('/favorites');
    await page.waitForTimeout(1000);
    await screenshot(page, '11-favorites');
  });
});
