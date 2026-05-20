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

    // 4. Switch to Categories tab on mobile
    const categoriesTab = page.locator('.admin__tab:has-text("Категории")');
    if (await categoriesTab.isVisible().catch(() => false)) {
      await categoriesTab.click();
    }

    // 5. Create a test category using data-testid selectors
    await page.click('[data-testid="add-category-btn"]');
    await page.fill('[data-testid="category-name-input"]', 'E2E Test Category');
    await page.fill('[data-testid="category-description-input"]', 'Test description');
    await page.click('[data-testid="category-submit-btn"]');

    // 6. Wait for modal to close, then verify category appears in table
    await expect(page.locator('.modal-overlay')).not.toBeVisible({ timeout: 10000 });
    await expect(
      page.locator('.admin__table td').filter({ hasText: 'E2E Test Category' }).first()
    ).toBeVisible({ timeout: 10000 });

    // 7. Verify "Add" button exists
    await expect(page.locator('[data-testid="add-category-btn"]')).toBeVisible();
  });
});
