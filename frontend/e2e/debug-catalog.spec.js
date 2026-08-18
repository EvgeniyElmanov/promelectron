import { test, expect } from '@playwright/test';

function uniqueEmail() {
  return `test_${Date.now()}_w${test.info().workerIndex}@example.com`;
}

test('debug add to cart desktop', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  page.on('request', req => {
    if (req.url().includes('/cart')) console.log('REQUEST', req.method(), req.url());
  });
  page.on('console', msg => console.log('CONSOLE', msg.type(), msg.text()));
  page.on('pageerror', err => console.log('PAGEERROR', err.message));

  const email = uniqueEmail();
  const password = 'TestPassword123!';

  await page.goto('/register');
  await page.fill('[data-testid="register-name"]', 'Test User');
  await page.fill('[data-testid="register-email"]', email);
  await page.fill('[data-testid="register-password"]', password);
  await page.fill('[data-testid="register-password-confirm"]', password);
  await page.click('[data-testid="register-submit"]');
  await expect(page).toHaveURL('/');
  await page.waitForTimeout(3000);

  const btn = page.locator('[data-testid="add-to-cart-button"]').first();
  await btn.click();
  await page.waitForTimeout(3000);
  console.log('AFTER CLICK URL:', page.url());
});
