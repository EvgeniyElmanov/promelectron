import { test, expect } from '@playwright/test';

test.describe('Admin Panel', () => {
  test('admin can view admin page and categories table', async ({ page }) => {
    // 1. Login as admin
    await page.goto('/login');
    await page.fill('[data-testid="login-email"]', 'seed-admin@example.com');
    await page.fill('[data-testid="login-password"]', 'seedpassword123');
    await page.click('[data-testid="login-submit"]');
    await expect(page).toHaveURL('/');

    // 2. Navigate to admin page via profile
    await page.goto('/profile');
    await expect(page.locator('[data-testid="profile-page"]')).toBeVisible();
    await page.click('[data-testid="profile-admin-link"]');
    await expect(page).toHaveURL('/admin');
    await expect(page.locator('[data-testid="admin-page"]')).toBeVisible();

    // 4. Switch to Categories tab (mobile) or scroll to categories section (desktop)
    const categoriesTab = page.locator('.admin__tab:has-text("Категории")');
    if (await categoriesTab.isVisible().catch(() => false)) {
      await categoriesTab.click();
    }

    // 5. Create a test category
    await page.click('.admin__btn--primary');
    await page.fill('.field__input[placeholder*="Например"]', 'E2E Test Category');
    await page.fill('.field__input--textarea', 'Test description');
    await page.click('.modal__submit');

    // 6. Verify category appears in table
    await expect(page.locator('.admin__table td').filter({ hasText: 'E2E Test Category' }).first()).toBeVisible();

    // 7. Verify "Add" button exists
    await expect(page.locator('.admin__btn--primary')).toBeVisible();
  });
});
