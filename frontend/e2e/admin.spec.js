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

    // 3. Switch to Categories tab on mobile
    const categoriesTab = page.locator('.admin__tab:has-text("Категории")');
    if (await categoriesTab.isVisible().catch(() => false)) {
      await categoriesTab.click();
    }

    // 4. Create a test category
    await page.click('[data-testid="add-category-btn"]');
    await page.fill('[data-testid="category-name-input"]', 'E2E Test Category');
    await page.fill('[data-testid="category-description-input"]', 'Test description');
    await page.click('[data-testid="category-submit-btn"]');

    // 5. Wait for modal to close, then verify category appears in table
    await expect(page.locator('.modal-overlay')).not.toBeVisible({ timeout: 10000 });
    const categoryRow = page.locator('.admin__table tr').filter({ hasText: 'E2E Test Category' }).first();
    await expect(categoryRow).toBeVisible({ timeout: 10000 });

    // 6. Verify "Add" button exists
    await expect(page.locator('[data-testid="add-category-btn"]')).toBeVisible();

    // 7. Cleanup: delete the test category
    page.once('dialog', (dialog) => dialog.accept());
    await categoryRow.locator('.admin__icon-btn--delete').click();
    await expect(categoryRow).not.toBeVisible({ timeout: 10000 });
  });
});
