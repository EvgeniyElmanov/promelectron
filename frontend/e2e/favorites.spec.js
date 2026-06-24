import { test, expect } from '@playwright/test';

function uniqueEmail() {
  return `test_${Date.now()}_w${test.info().workerIndex}@example.com`;
}

test.describe('Favorites', () => {
  test('can add product to favorites from catalog', async ({ page }) => {
    const email = uniqueEmail();
    const password = 'TestPassword123!';

    // Register
    await page.goto('/register');
    await page.fill('[data-testid="register-name"]', 'Test User');
    await page.fill('[data-testid="register-email"]', email);
    await page.fill('[data-testid="register-password"]', password);
    await page.fill('[data-testid="register-password-confirm"]', password);
    await page.click('[data-testid="register-submit"]');
    await expect(page).toHaveURL('/');

    // Add first product to favorites
    const firstCard = page.locator('[data-testid="product-card"]').first();
    const favButton = firstCard.locator('[data-testid="favorite-button"]');
    await favButton.click();
    await expect(favButton).toHaveClass(/product-card__heart--active/);

    // Go to favorites
    await page.click('[data-testid="nav-Избранное"]');
    await expect(page).toHaveURL('/favorites');
    await expect(page.locator('[data-testid="favorite-item"]').first()).toBeVisible({ timeout: 5000 });
  });

  test('unauthorized user redirected to login when accessing favorites', async ({ page }) => {
    await page.goto('/favorites');
    await expect(page).toHaveURL('/login');
  });
});
