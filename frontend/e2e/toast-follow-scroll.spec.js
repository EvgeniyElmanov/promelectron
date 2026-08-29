import { test, expect } from '@playwright/test';

function uniqueEmail() {
  return `test_${Date.now()}_w${test.info().workerIndex}@example.com`;
}

function createAvatarPng() {
  // 1x1 transparent PNG
  return Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
    'base64'
  );
}

// Регрессия issue #194: toast-уведомления не следовали за скроллом, т.к.
// `overflow-x: hidden` на html/body ломал `position: sticky` хедера,
// к которому якорится .header__toast.
// Триггер тоста — загрузка аватара: success-тосты корзины удалены в #198 (PR #201).
async function scrollDeeply(page) {
  await page.evaluate(() => window.scrollTo(0, 1500));
  const scrollY = await page.evaluate(() => window.scrollY);
  expect(scrollY, 'страница должна реально проскроллиться').toBeGreaterThan(0);
}

async function expectHeaderStickyAfterScroll(page) {
  await page.goto('/');
  await expect(page.locator('[data-testid="product-card"]').first()).toBeVisible();
  await scrollDeeply(page);
  const headerTop = await page.locator('header.header').evaluate((el) => el.getBoundingClientRect().top);
  expect(headerTop).toBeCloseTo(0, 0);
}

async function expectToastVisibleInViewportAfterScroll(page) {
  // Register (загрузка аватара требует авторизации)
  await page.goto('/register');
  await page.fill('[data-testid="register-name"]', 'Test User');
  await page.fill('[data-testid="register-email"]', uniqueEmail());
  await page.fill('[data-testid="register-password"]', 'TestPassword123!');
  await page.fill('[data-testid="register-password-confirm"]', 'TestPassword123!');
  await page.click('[data-testid="register-submit"]');
  await expect(page).toHaveURL('/');

  // Скроллим вниз и загружаем аватар: success-тост должен появиться в viewport,
  // несмотря на проскролленную страницу (тост якорится к sticky-хедеру).
  await page.goto('/profile/edit');
  await expect(page.locator('.edit-card--avatar input[type="file"]')).toBeAttached();
  await scrollDeeply(page);
  await page.locator('.edit-card--avatar input[type="file"]').setInputFiles({
    name: 'avatar.png',
    mimeType: 'image/png',
    buffer: createAvatarPng(),
  });

  const toast = page.locator('.toast--success');
  await expect(toast).toBeVisible({ timeout: 10000 });
  await expect(toast).toContainText('Фото профиля обновлено');
  // Убеждаемся, что проверка выполняется при реально проскролленной странице
  expect(await page.evaluate(() => window.scrollY)).toBeGreaterThan(0);
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
