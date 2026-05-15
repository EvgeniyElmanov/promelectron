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

    // 4. Verify categories table is visible
    await expect(page.locator('.admin__table')).toBeVisible();
    await expect(page.locator('.admin__table td').filter({ hasText: 'Смартфоны' }).first()).toBeVisible();

    // 5. Verify "Add" button exists
    await expect(page.locator('.admin__btn--primary')).toBeVisible();
  });
});
